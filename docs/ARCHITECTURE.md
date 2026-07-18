# Architecture

Status: **populated (v0.4) — initial system design laid out and Epic A (Foundation) built and
verified.** Technology stack confirmed (ADR-0013); encryption approach revised for
cross-platform reliability (ADR-0015: application-level field encryption, not SQLCipher).
Detailed build backlog tracked in [BACKLOG.md](BACKLOG.md).

This document describes the current state of the system's architecture. It should always
reflect what *is*, not what's planned (that belongs in [ROADMAP.md](ROADMAP.md)) or why a
choice was made (that belongs in [DECISIONS.md](DECISIONS.md), linked from here).

Per [CONSTITUTION.md](CONSTITUTION.md), this file must be updated in the same change that alters
the architecture — never left to drift.

## 1. System Overview

A single local application, run entirely on one machine (per [DECISIONS.md](DECISIONS.md)
ADR-0002), with two halves that share one local database:

1. A background **sync pipeline** that periodically reads matching Gmail messages and turns
   them into structured transactions.
2. A **web dashboard** the user opens in a browser to search, review, correct, and summarize
   their transaction history.

```
                    ┌────────────────────────────────────────────┐
                    │              Sync Scheduler                 │
                    │        (wakes up periodically)               │
                    └───────────────────┬──────────────────────────┘
                                        │ triggers
                                        ▼
   Gmail  ───────►  Gmail Connector ──► Classifier ──► Extractor ──► Deduplicator
 (OAuth,                (ING-1..8)     (ING-3a,        (EXT-1..7)      (DUP-1, DUP-2)
  History API)                          Appendix A)                        │
                                                                            ▼
                                                                  ┌──────────────────┐
                                                                  │     Storage       │
                                                                  │  (Transaction,    │
                                                                  │  EmailMessage,    │
                                                                  │  SenderRule,      │
                                                                  │  Category, ...)   │
                                                                  └─────────┬────────┘
                                                                            │
                                                          ┌─────────────────┴─────────────────┐
                                                          ▼                                   ▼
                                                  Review Queue                          Categorizer
                                                 (needs-review items,                  (user-assigned,
                                                  EXT-5/EXT-6)                          remembered per payee)
                                                          │                                   │
                                                          └─────────────────┬─────────────────┘
                                                                            ▼
                                                                       API Layer
                                                                 (REST/JSON, ADR-0003)
                                                                            │
                                                                            ▼
                                                                     Web Dashboard
                                                              (search, correct, analytics)
```

A future mobile app (ROADMAP.md M7) connects to the same API Layer as an additional client —
it does not get its own copy of the sync pipeline.

## 2. Guiding Architectural Style

Layered, with a strict separation between the **domain** (what a Transaction is, what counts as
a duplicate, how correction works) and **infrastructure** (Gmail's specific API, the specific
database engine, the specific web framework). Each functional area from
[REQUIREMENTS.md](REQUIREMENTS.md) §3 is a separate module behind a defined interface — no
monolith, per the original design directive to stay plug-and-play.

- Reference: [DECISIONS.md](DECISIONS.md) → ADR-0009 (ingestion scope), ADR-0010 (classification
  approach), ADR-0013 (proposed tech stack).

## 3. Layers & Module Boundaries

| Layer | Responsibility | Depends on | Must not depend on |
|---|---|---|---|
| Domain | Core rules: what a Transaction/Payee/Category is, dedup logic (DUP-1/DUP-2), correction rules (COR-1..5) | Nothing (pure) | Gmail API, the database engine, the web framework |
| Application (use cases) | Orchestration: `SyncGmailAccount`, `ClassifyAndExtractEmail`, `CorrectTransaction`, `BuildMonthlySummary` | Domain | UI, infrastructure internals |
| Infrastructure | `GmailClient` (Gmail OAuth + History API), `TransactionRepository` (database), `AIFallbackClient` (rare-case AI extraction) — each a concrete implementation of a Domain/Application-defined interface | Application, Domain (via interfaces) | — |
| Presentation | API Layer (REST/JSON endpoints) and the Web Dashboard (consumes the API only, never talks to Infrastructure directly) | Application | Infrastructure internals |

Modules, matching [REQUIREMENTS.md](REQUIREMENTS.md) §3:

- **Ingestion** (`GmailClient` + `SyncScheduler`) — ING-1 through ING-8.
- **Classification** (`SenderRule` matching — see Appendix A in REQUIREMENTS.md) — ING-3a.
- **Extraction** (`Extractor`, per-type fixed parsers + `AIFallbackClient`) — EXT-1 through EXT-7.
- **Deduplication** (`Deduplicator`) — DUP-1, DUP-2.
- **Storage** (`TransactionRepository` and friends) — the single source of truth on disk.
- **Review Queue** — a query/view over Storage for needs-review items, not a separate store.
- **Categorization** — mostly a thin module: remembers the last category a user assigned per
  Payee (COR-2); no AI/inference in MVP (EXT-2).
- **Correction** (`CorrectTransaction` use case) — COR-1 through COR-5.
- **Analytics** (`BuildMonthlySummary` and similar use cases) — ANL-1 through ANL-4.
- **API Layer** — the only door into the system for any UI, current or future.
- **Web Dashboard** — a separate front-end application; talks to the API Layer only.

Each of these is swappable independently: e.g. the `GmailClient` could later be joined by a
second bank's client without touching Extraction, Storage, or the Dashboard; the
`AIFallbackClient` could switch providers without touching anything else (Constitution
principle 10).

## 4. Data Storage

**Accepted (ADR-0013, revised by ADR-0015):** SQLite via Python's standard library `sqlite3`
(through SQLAlchemy), as a single local file — no separate database server to install or run,
and no native/compiled dependency, matching both the local-first deployment model (ADR-0002)
and the platform-independence requirement (macOS dev machine, Ubuntu VM deployment target,
ADR-0015).

**Encryption approach (ADR-0015):** whole-database encryption (SQLCipher) was attempted and
rejected — it failed to install even on the development machine, confirming it as an
unreliable cross-platform dependency. Instead, the `gmail_connections.tokens` and
`email_messages.content` columns are encrypted at the application level using the
`cryptography` package (Fernet/AES) before being written, and decrypted after being read.
Other columns (transaction amount, date, payee, category, etc.) are stored in plain SQLite —
their at-rest protection depends on file permissions and the host OS's own disk encryption,
not a guarantee this application makes.

Tables map directly to [REQUIREMENTS.md](REQUIREMENTS.md) §5 Data Model:

- `users` — single row for now, but present from day one (multi-user readiness, §9).
- `gmail_connections` — OAuth tokens (**encrypted column**, ADR-0015), one per connected mailbox.
- `sender_rules` — sender address + content-matching pattern → transaction type (ADR-0010).
- `email_messages` — Gmail message ID, thread ID, received timestamp, processing status,
  **cached content (encrypted column, ADR-0012/ADR-0015)**, and a pointer to the transaction it
  produced (if any).
- `sync_state` — per-connection checkpoint (last `historyId`, last sync time, last error).
- `transactions` — amount, currency, date, time (nullable), payee, instrument last-4, category,
  payment method, type, reference number (nullable), confidence score, review status, link to
  its `email_messages` row. Not encrypted at the column level (see above).
- `payees` — payee/merchant identity as it appears in the source email.
- `categories` — fully user-defined for MVP; no fixed seed list.
- `correction_log` — original vs. corrected field values (COR-3).

Migration tooling: Alembic (standard companion to SQLAlchemy, pure Python, no native
dependency — consistent with the platform-independence requirement).

## 5. External Integrations

| Integration | Purpose | Isolation boundary |
|---|---|---|
| Gmail API (OAuth 2.0 + History API) | Read-only access to the connected mailbox; incremental sync | Behind a `GmailClient` interface (Infrastructure layer) — nothing above it knows it's specifically Gmail, only "an ingestion source" |
| AI provider (rare extraction fallback) | Best-effort field extraction when an email matches a known sender but not a known content pattern | Behind an `AIFallbackClient` interface (Constitution principle 10) — provider (cloud API vs. local model) is a swappable implementation detail, not yet chosen |

No other external integrations exist. Vendor-email tracking (Amazon, Flipkart, etc.) was
considered and explicitly dropped (ADR-0009) — not an integration in this system.

## 6. Cross-Cutting Concerns

- **Error handling:** fail loudly and visibly. Sync failures, classification failures, and
  extraction failures are surfaced (ING-8 sync health panel; EXT-5/EXT-6 needs-review queue) —
  never silently swallowed or guessed past.
- **Logging & observability:** a local log capturing sync runs (messages scanned/matched/
  skipped/failed) feeding the ING-8 sync health panel; no external log shipping (local-first).
- **Authentication & authorization:** no user login exists yet — single local user, single
  machine. Gmail OAuth is the only credential in the system. Multi-user (ROADMAP.md M8) will add
  a real auth layer at the API boundary without changing Transaction/Payee/Category shapes,
  which are already user-scoped (§9 of REQUIREMENTS.md).
- **Configuration management:** `SenderRule` entries (sender address + content pattern per
  type), database location, and API/dashboard ports are the main configuration surface for v1.
  The `scripts/vm_*.py` verification tooling (§7, ADR-0017) adds its own small surface —
  `VM_HOST`, `VM_REMOTE_DIR` — plus reuses `BACKEND_PORT`/`FRONTEND_PORT` from `scripts/dev.py`.
- **Process shutdown:** the dev-run script (`scripts/dev.py`) explicitly registers handlers for
  both SIGINT (Ctrl+C) and SIGTERM, rather than relying on Python's default Ctrl+C behavior.
  This was a deliberate fix during Epic A: a shell backgrounding a process sets SIGINT to be
  ignored by convention, which suppressed the default handler entirely during testing —
  explicit registration is also what a systemd-managed process on the Ubuntu deployment target
  needs, since systemd stops services with SIGTERM, not an interactive Ctrl+C.

## 7. Testing Strategy

- **Unit tests** for each per-type parser (UPI debit, UPI credit, credit card debit — credit
  card credit once its sample arrives) against the real sample emails in
  [REQUIREMENTS.md](REQUIREMENTS.md) Appendix A, plus the edge cases already identified there:
  missing reference number, missing parenthetical payee name, differing `Rs.` spacing,
  differing date/time formats.
- **Unit tests** for the Deduplicator: same message ID twice, same amount/payee/day with
  different reference numbers, missing-reference-number fallback via timestamp.
- **Integration tests** for the full pipeline: a raw sample email in → a correct `Transaction`
  row out (or a correctly-flagged needs-review item, never a silent drop).
- **UI verification by driving the running dashboard directly** (browser automation) for
  dashboard stories — actually clicking through search, correction, and review flows and
  observing the result, rather than relying on a written UI test suite or on code review alone.
- **What cannot be self-verified, and why:** the live Gmail OAuth consent step requires the
  account owner's own action (no credential entry on their behalf); and full confidence that
  extraction rules hold against the real inbox — beyond the confirmed samples — requires the
  user to spot-check a handful of real results after the first backfill. See
  [BACKLOG.md](BACKLOG.md) "Definition of Done" for how this fits into each story/epic.
- **Verification runs against the Ubuntu VM, not just macOS (ADR-0017):** macOS is fine for the
  fast local dev/edit loop, but a story or epic isn't considered verified until it's been run on
  the actual Ubuntu deployment target, since real divergence between the two has already
  surfaced once (ADR-0016). Four scripts under `scripts/` (stdlib-only, matching
  `setup.py`/`dev.py`) make this a single command instead of repeated manual steps:
  - `scripts/vm_test.py` — syncs the source tree to the VM and runs the backend automated test
    suite there. This is the real gate for Epics A–E's "automated tests exist and pass"
    Definition-of-Done criterion (BACKLOG.md) — a macOS-only pass is necessary but not
    sufficient.
  - `scripts/vm_dev.py` (`start`/`stop`) — syncs, (re)starts the backend + frontend dev servers
    on the VM, and opens the SSH tunnel (below) so the dashboard can be driven directly for
    Epics F–G's browser-automation verification, same as it would be against a local instance.
  - `scripts/vm_tunnel.py` (`start`/`stop`) — the SSH port-forward on its own, for when the
    servers are already running and only the tunnel needs to be (re)established.
  - `scripts/vm_sync.py` — the rsync step alone; the other three call it internally. Excludes
    are derived from `.gitignore` rather than a second hand-maintained list, so venvs,
    `node_modules`, and the local encryption key/database can't silently drift into being synced
    (or silently stop being synced) as `.gitignore` evolves.
  - **Why a tunnel, not direct access:** the VM sits on a Tailscale network whose ACLs appear to
    permit only SSH between nodes — direct connections to the app's own ports (5173/8000) time
    out even though `ping` and `ssh` both succeed and the VM's own firewall (`ufw`) is inactive.
    The tunnel rides over the already-permitted SSH connection instead. Configurable via
    `VM_HOST`/`VM_REMOTE_DIR`/`BACKEND_PORT`/`FRONTEND_PORT` env vars (see `scripts/_vm.py`).

## 8. Known Limitations / Technical Debt

- Epic A (Foundation) built and verified (BACKLOG.md); Epics B onward not started.
- Encryption at rest is **field-level, not whole-database** (ADR-0015) — transaction data
  itself relies on OS-level disk encryption if the user wants that layer protected too; this is
  a real, accepted limitation, not an oversight (see REQUIREMENTS.md §4 NFR Security).
- Single bank (HDFC) only; `SenderRule` design must stay extensible per REQUIREMENTS.md §9, but
  no second bank is implemented.
- No OCR/attachment handling; not needed for the confirmed HDFC templates (plain-text body).
- Development happens on macOS (Apple Silicon); the actual deployment target is an Ubuntu VM
  (ADR-0015). **Verified 2026-07-18:** Epic A runs end-to-end on the Ubuntu 26.04 LTS deployment
  VM — `scripts/setup.py` (venv creation, pip install, Alembic migration, `npm install`) and
  `scripts/dev.py` (backend + frontend dev servers, CORS) both work, and all 5 backend tests pass
  (including the raw-file encryption check). This required bumping `sqlalchemy`/`alembic` to
  newer 2.0.x/1.x patch releases for Python 3.14 compatibility, since Ubuntu 26.04 ships only
  Python 3.14 with no older version available via its repos or a PPA (ADR-0016). Not yet
  exercised: systemd-managed service setup (still run via `scripts/dev.py` directly, as on
  macOS) and the live Gmail OAuth flow (Epic B).
- The FastAPI app does not yet touch the database at all (no lifespan hook creates tables or
  runs migrations automatically) — schema setup currently only happens via running
  `alembic upgrade head` directly (through `scripts/setup.py`). This is expected to remain the
  case until an epic that actually needs the database (Epic B onward) wires it in.

---
_Every non-trivial entry above should trace back to an ADR in [DECISIONS.md](DECISIONS.md)._
