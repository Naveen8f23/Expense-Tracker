# Architecture

Status: **populated (v1.2) — Epics A-F (Foundation through Dashboard: Review & Correction) built
and verified; Epics B and C additionally against the owner's real Gmail account, Epic F by
directly driving the running dashboard.** Automatic background sync added (2026-07-19, ADR-0019):
a `SyncScheduler` polls Gmail every 5 seconds with no manual trigger, and the dashboard shows new
transactions live via polling + browser notifications. **The Ubuntu VM is now the owner's real,
permanent, day-to-day instance (2026-07-19, ADR-0020)** — previously only ADR-0017's cross-platform
*test* target, it now runs a persistent `systemd --user` service with its own independent Gmail
connection/history (a deliberate fresh start, not a migration of the Mac's data); the local Mac
instance has been stopped. Technology stack confirmed (ADR-0013); encryption approach revised for
cross-platform reliability (ADR-0015: application-level field encryption, not SQLCipher). Google's
official client libraries added for Gmail OAuth/API access (ADR-0018). **Epic G (Search &
Analytics) done, verified, and confirmed by the owner (2026-07-19)** — a new Analytics module
(monthly summary, category breakdown, payee history, ADR-0021) plus dashboard polish, demoed live
on the production VM per the epic-checkpoint policy (ADR-0014). Same-day follow-ups requested by
the owner: transaction time now shown (real or approximated) everywhere a transaction is listed,
and same-day sort order now actually follows that time
(`app/domain/transaction_time.py`) instead of database insertion order. **Epic H (Cross-cutting
polish) done (2026-07-19)** — H1 (encryption verification) was already satisfied by an Epic A2
test; H2 (manual "add a transaction" escape hatch, ADR-0022) required making
`transactions.email_message_id` nullable, the first schema change to that table's core shape
since Epic A. **M7 (Ledger, the iOS app) started (2026-07-19)** — a visual design concept was
reviewed and confirmed; Swift + SwiftUI chosen (ADR-0023); new-transaction notifications will be
in-app/foreground-only, not Apple Push and not a third-party relay (ADR-0024). No backend changes
are implied — Ledger is a second Presentation-layer client of the existing API (§3). Detailed
build backlog tracked in [BACKLOG.md](BACKLOG.md) (Epics I–M for Ledger).

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

A mobile app — **Ledger**, iOS, ROADMAP.md M7, in progress — connects to the same API Layer as
an additional client. It does not get its own copy of the sync pipeline, its own Gmail connection,
or its own analytics logic; it is presentation only, exactly like the Web Dashboard box above,
just a second box beside it reading and writing through the same API Layer.

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

**Noted deviation (Epic C, 2026-07-19):** the vocabulary enums (`TransactionType`,
`PaymentMethod`, `DebitOrCredit`, `EmailMessageStatus`, `ReviewStatus`) live in
`app/infrastructure/models.py` (Epic A's choice, so SQLAlchemy's `Enum` column type can reference
them directly) rather than in Domain. `app/domain/classification.py` and
`app/domain/extraction.py` import `PaymentMethod`/`DebitOrCredit` from there, which technically
makes Domain depend on Infrastructure — these are plain, framework-free `str, enum.Enum` classes
with no SQLAlchemy/Gmail/FastAPI coupling of their own, so nothing about the *actual* forbidden
dependencies (Gmail API, the database engine, the web framework) is pulled in, but the import
still crosses the layer boundary as drawn. Flagged here rather than silently introduced; not
fixed now since duplicating the same four enums into a new `app/domain` module would violate
"one source of truth per fact" (Constitution principle 26) for no behavior change. Revisit (move
the enums to Domain and have `models.py` import them back) if this pairing starts to feel like a
real problem rather than a naming wrinkle.

Modules, matching [REQUIREMENTS.md](REQUIREMENTS.md) §3:

- **Ingestion** (`GmailClient` + `SyncScheduler`) — ING-1 through ING-8. **Epic B complete
  (2026-07-18), all verified against the real connected account:**
  - **B1:** OAuth connect — `app/infrastructure/gmail_oauth.py` (Google's official client
    libraries, ADR-0018) + `app/application/connect_gmail_account.py` +
    `app/presentation/gmail_router.py`.
  - **B3:** one-time backfill — `app/infrastructure/gmail_client.py` +
    `app/application/run_initial_backfill.py`, chained automatically at the end of the OAuth
    callback; caches each match as an unprocessed `EmailMessage` (content = decoded `text/html`
    MIME part, falling back to `text/plain`).
  - **B4:** incremental sync — `app/application/run_incremental_sync.py`, using Gmail's History
    API with a bounded-re-scan fallback if the checkpoint expires. Shares its message-storing
    step with B3 via `app/application/ingest_gmail_messages.py`.
  - **B5:** sync health — the shared message-storing step now catches a per-message
    `GmailIngestionError` and counts it as failed rather than aborting the whole run; `sync_state`
    carries start time and scanned/matched/skipped/failed counts (migration `96b145d41d66`).
  - **`SyncScheduler` built (2026-07-19, ADR-0019):** `app/infrastructure/sync_scheduler.py` — a
    plain `threading.Thread` polling every 5 seconds by default
    (`SYNC_POLL_INTERVAL_SECONDS`), running `run_incremental_sync` then
    `run_classify_and_extract` each cycle; started/stopped from FastAPI's lifespan hook
    (`app/presentation/main.py`). No manual "sync now" trigger exists or is needed — this was
    deferred through Epics B–F (per Constitution principle 2, no concrete reason yet existed to
    run sync unattended) until the owner explicitly asked for automatic updates while live-testing
    Epic F's dashboard.
- **Classification** (`SenderRule` matching — see Appendix A in REQUIREMENTS.md) — ING-3a. **Epic
  C complete (2026-07-19):** `app/domain/classification.py` — pure content-pattern matchers
  (`is_upi_debit`, `is_upi_credit`, `is_credit_card_debit`) plus `classify()`, which picks the one
  matching `content_pattern_id` out of the candidates a caller passes in (sender-then-content,
  ADR-0010). No database or Gmail dependency — a true Domain-layer module.
- **Extraction** (`Extractor`, per-type fixed parsers + `AIFallbackClient`) — EXT-1 through EXT-7.
  **Epic C complete:** `app/domain/extraction.py` (`extract_upi_debit`, `extract_upi_credit`,
  `extract_credit_card_debit`, each returning an `ExtractedTransaction` or raising
  `ExtractionError`) and `app/domain/ai_fallback.py` (`AIFallbackClient` protocol +
  `StubAIFallbackClient`, always "unable to extract" — C8). Orchestrated by
  `app/application/run_classify_and_extract.py` (`run_classify_and_extract`), which processes
  every `UNPROCESSED` `EmailMessage`: classify → extract → create a `Transaction` (auto-accepted
  on a clean fixed-rule match; flagged `NEEDS_REVIEW` if only the AI fallback produced it) →
  mark the email `MATCHED`, or mark it `NEEDS_REVIEW` if nothing could extract it at all (EXT-6).
  Now called automatically every cycle by the `SyncScheduler` above (ADR-0019), not just
  on-demand.
- **Deduplication** — DUP-1, DUP-2. **Epic D complete (2026-07-19), no new code:** both
  guarantees already existed by construction from earlier epics — `email_messages.message_id` and
  `transactions.email_message_id` are both `unique` (A2), and `run_classify_and_extract` only
  ever processes `UNPROCESSED` emails (C7), so an already-handled message can't be reprocessed.
  There is no content-based (amount/payee/day) matching step anywhere, by design (ADR-0009), so
  two genuinely separate transactions that happen to share those fields are never at risk of
  being merged — there's nothing that would ever compare them in the first place. No dedicated
  `Deduplicator` component was added: it would have had no logic to hold, and Constitution
  principle 2 (avoid unnecessary abstraction) argues against building one anyway. Confirmed by
  `backend/tests/test_deduplication.py`, not by new production code.
- **Storage** (`TransactionRepository` and friends) — the single source of truth on disk.
- **Review Queue** — a query/view over Storage for needs-review items, not a separate store.
  **Epic C complete:** `run_classify_and_extract.get_needs_review_emails` — a dedicated read
  helper (unlike B5's `sync_state`, which reused plain ORM queries directly) since Epic E's E5
  endpoint will want exactly this query shape.
- **Categorization** — mostly a thin module: remembers the last category a user assigned per
  Payee (COR-2); no AI/inference in MVP (EXT-2). **Epic E complete (2026-07-19):** realized as
  `payees.default_category_id` (migration `dcdef4f896b2`), set by `correct_transaction` (E3) and
  read back by `run_classify_and_extract` (Epic C) when creating a *new* transaction from that
  payee.
- **Correction** (`CorrectTransaction` use case) — COR-1 through COR-5. **Epic E complete:**
  `app/application/correct_transaction.py` (E3) and `app/application/dismiss_transaction.py`
  (E4, COR-4). **H2 complete (2026-07-19):** `app/application/add_manual_transaction.py`
  (`add_manual_transaction`) — COR-5's "add a transaction with no email" escape hatch. Payee
  matched case-insensitively by name (no VPA to key on for a typed-in name, ADR-0022); COR-2's
  remembered-category behavior applies the same way it does for corrections and auto-ingestion.
- **Analytics** (`app/application/analytics.py`) — ANL-1 through ANL-4. **Epic G complete
  (2026-07-19):** `get_monthly_summary`, `get_category_breakdown`, `get_payee_history` — plain
  aggregation queries (`func.sum`/`group_by`) over `Transaction`, the first in this codebase.
  Money-semantics conventions (sign convention, debit-only category spend, shared month cursor,
  exact-name payee matching) recorded in ADR-0021 since BACKLOG.md's G2-G4 stories didn't spell
  them out. Exposed via `app/presentation/analytics_router.py`
  (`GET /analytics/monthly`, `GET /analytics/by-category`, `GET /analytics/by-payee/{payee}`).
- **API Layer** — the only door into the system for any UI, current or future. **Epic E complete:**
  `app/presentation/transactions_router.py` (E1-E4, plus `GET /transactions/recent?since_id=`
  added 2026-07-19 for the dashboard to poll for newly-arrived transactions, ADR-0019),
  `needs_review_router.py` (E5, plus the F4 addendum `POST /needs-review/emails/{id}/ignore`),
  `categories_router.py` (E6), `sync_router.py` (E7), `analytics_router.py` (Epic G, above) —
  all registered in `main.py`. Every endpoint reads/writes through an Application-layer use case;
  no router queries the ORM directly beyond simple single-row lookups (`session.get`), keeping
  with the layering in ARCHITECTURE.md §3.
- **Web Dashboard** — a separate front-end application; talks to the API Layer only. **Epic F
  complete (2026-07-19):** `frontend/src/components/TransactionsView.tsx` (F1),
  `TransactionDetailPanel.tsx` (F2/F3/F5 combined — correction form, source email viewer, inline
  category creation), `NeedsReviewView.tsx` (F4). `frontend/src/api/client.ts` extended with
  typed functions for every Epic E/F endpoint — still the only place in the frontend that calls
  `fetch`. **Automatic live updates added same day (ADR-0019):**
  `frontend/src/hooks/useNewTransactionNotifications.ts` polls `GET /transactions/recent` every
  5 seconds; when new transactions appear, it triggers a table refresh (via a `refreshSignal`
  prop threaded into `TransactionsView`) and fires a browser `Notification` per new transaction
  (permission requested via a one-time button click in `App.tsx` — browsers require an explicit
  user gesture, it can't be granted programmatically) whose `onclick` opens that transaction's
  detail panel directly. No routing library was added (React Router, etc.) — simple `useState`-driven view
  switching in `App.tsx` was judged sufficient for the two current top-level views
  (Constitution principle 3: don't add a dependency without a concrete need); revisit once Epic G
  adds more views if this stops being simple enough. `.claude/launch.json` added so the frontend
  dev server can be previewed via the Browser tool.
  **Epic G additions (2026-07-19):** a third "Analytics" tab
  (`frontend/src/components/AnalyticsView.tsx`, G2/G3 — month navigation, summary cards, category
  table) and `frontend/src/components/PayeeHistoryPanel.tsx` (G4 — a `.panel`-shaped overlay,
  opened by clicking a payee name in `TransactionsView`'s table, matching `TransactionDetailPanel`'s
  existing shape rather than becoming its own tab). The two-way ternary in `App.tsx` became a
  three-way conditional chain, confirming the "revisit once Epic G adds more views" note above —
  still no routing library needed for three views. `TransactionsView.tsx` also gained G1's
  polish: debounced free-text/payee inputs (a `searchDraft` state separate from the
  fetch-triggering `filters` state), a "Clear all filters" button, and removable active-filter
  chips.
  **H2 addition (2026-07-19):** `frontend/src/components/AddTransactionPanel.tsx` — a
  create-only panel (not a retrofit of the fetch-and-edit-shaped `TransactionDetailPanel`) opened
  by a new "+ Add transaction" button in `TransactionsView`; a persistent banner frames it as the
  exception, not the norm (COR-5). Rows with no source email (`email_message_id === null`) get a
  "Manual" badge in the table and a substituted note in `TransactionDetailPanel` where "View
  source email" would otherwise be.
- **Mobile Client — Ledger (iOS)** — a second Presentation-layer client, alongside the Web
  Dashboard, talking to the same API Layer only (REQUIREMENTS.md §15, ADR-0023). **M7 in progress
  (2026-07-19): Epic I (foundation) and Epic J (transaction list & correction, J1-J7) both done.**
  Native Swift + SwiftUI, project defined via a checked-in XcodeGen `project.yml` rather than a
  hand-edited `.xcodeproj` (`ios/Ledger/`). Module shape mirrors the frontend's own discipline — a
  single `Networking/APIClient.swift` wraps every backend call (no view talks to `URLSession`
  directly, the same rule `frontend/src/api/client.ts` follows), `ViewState/` holds
  `ObservableObject` stores (the only layer allowed to call `Networking`), `Views/` holds SwiftUI
  screens. Built so far: the 3-tab shell (Ledger/Analytics/Review), the connection-settings screen
  (I3), the transaction list with full filtering/search/chips (J1-J2), a transaction detail sheet
  for correcting fields or dismissing a transaction (J3), the source email viewer (J4), swipe
  actions for quick edit/dismiss (J5), a "Manage categories" screen plus inline "+ New category…"
  in J3's picker (J6), and a nav-bar sync-health dot (J7). New-transaction notifications will be
  local (`UNNotificationRequest`), driven by the same `GET /transactions/recent` polling pattern as
  the web dashboard's `useNewTransactionNotifications` hook — no APNs, no third-party push relay
  (ADR-0024) — once Epic M is reached. Detailed stories in [BACKLOG.md](BACKLOG.md) Epics I–M.

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
  **cached content (encrypted column, ADR-0012/ADR-0015)**, the `content_pattern_id`
  classification matched (if any — nullable; added Epic C, migration `e5aa5f25c7b3`, so a
  needs-review item that classified but then failed extraction keeps that context), and a
  pointer to the transaction it produced (if any).
- `sync_state` — per-connection checkpoint (last `historyId`, last sync started/completed time,
  last error) plus, since B5, the last run's scanned/matched/skipped/failed message counts
  (ING-8) — exposed via `GET /sync/status` (Epic E's E7, done).
- `transactions` — amount, currency, date, time (nullable), payee, instrument last-4, category,
  payment method, type, reference number (nullable), confidence score, review status, link to
  its `email_messages` row — **nullable since H2 (ADR-0022, migration `8bcc9bb76003`)**: a
  manually-added transaction (COR-5) has no source email at all, and `NULL` here is the marker for
  that, not a separate flag. Not encrypted at the column level (see above).
- `payees` — payee/merchant identity as it appears in the source email, plus (added Epic E,
  migration `dcdef4f896b2`) `default_category_id`: the category last assigned to a transaction
  from this payee (COR-2), applied to that payee's *future* transactions by
  `run_classify_and_extract`.
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
  - **Gap found during Epic F (2026-07-19):** `_STOP_REMOTE_SERVERS`'s pkill patterns
    (`vm_dev.py`) don't match an orphaned `multiprocessing` worker left over from an earlier
    `--reload`-mode uvicorn session — its command line never contains the literal
    `uvicorn app.presentation.main` the pattern looks for. Such a leftover process silently keeps
    answering health checks on the same port while a fresh `dev.py` invocation fails to bind and
    exits, making it look (from a bare health check) like the new code is running when it isn't.
    Not yet fixed in the tooling; killed by hand this session
    (`ssh $VM_HOST "kill -9 <pid>"`, found via `ss -tlnp`). Also: in the tool environment used for
    this session specifically, a backgrounded `ssh -L` tunnel process didn't reliably persist
    across separate tool invocations, so Epic F's dashboard could not be verified live against
    the VM specifically in this session — `scripts/dev.py` was confirmed to start both servers
    correctly there directly (its own log showed a clean Vite startup), just not tunneled back to
    a browser this time. Since the dashboard is plain client-side React/Vite with no OS-specific
    code, this is a lower-risk gap than the backend/interpreter divergence ADR-0016 covers.
  - **`scripts/vm_dev.py` is for interactive dev/test only — it now conflicts with the real
    deployment (ADR-0020).** The VM's persistent `systemd --user expense-tracker` service already
    occupies port 8000. Running `vm_dev.py start` (ephemeral `--reload` dev servers) at the same
    time will fail to bind that port. Stop the persistent service first
    (`ssh $VM_HOST systemctl --user stop expense-tracker`) if `vm_dev.py`-style interactive
    testing against the VM is genuinely needed, and restart it afterward (or just run
    `scripts/deploy_vm.py`, which restarts it as part of a normal deploy).
- **Deployment (ADR-0020):** `scripts/deploy_vm.py` is the one command for pushing a code change
  to the VM's real, persistent instance — sync, backend deps, `alembic upgrade head`, frontend
  rebuild, `systemctl --user restart`, then a health check. See `deploy/README.md` for the
  one-time setup (`systemd --user` service install + `sudo loginctl enable-linger`, run by the
  owner directly — the only step that ever needs their password, and it's never asked for or
  handled through an agent).

## 8. Known Limitations / Technical Debt

- Epics A-H (Foundation through Cross-cutting polish) built and verified (BACKLOG.md) — this
  completes REQUIREMENTS.md §13's MVP definition, modulo the still-pending 4th email template
  (credit card credit, REQUIREMENTS.md §8). Automatic background sync (ADR-0019) and real VM
  production deployment (ADR-0020) added on top of F, same day.
- **Ledger (iOS, M7) will not notify the owner of a new transaction while the app is fully closed
  or backgrounded beyond a short window (ADR-0024)** — a deliberate, accepted scope, not a bug.
  Both a real push path (direct APNs, $99/year) and a free push path (a third-party relay like
  ntfy.sh, at the cost of transaction text transiting a third party) were presented and declined.
  The concept design's lock-screen notification mockup is aspirational for a possible future
  upgrade, not what M7's initial build delivers — see ADR-0024 for the full reasoning and what
  would need to change to revisit it.
- **TRC-1 ("every transaction retains a reference back to the original email") has an explicit,
  intentional exception: manually-added transactions (H2, COR-5, ADR-0022).**
  `transactions.email_message_id` is nullable specifically for this case — `NULL` means "added
  manually," not a data-quality gap. Any future reporting/auditing feature that assumes every
  transaction has a source email should filter or branch on this rather than assuming TRC-1 holds
  universally.
- **Browser notifications only work while a dashboard tab is open** and the user has granted
  permission — there is no notification path for a closed tab or when no browser is running,
  since that would require Gmail's real push API and a public endpoint, explicitly not adopted
  (ADR-0019). New transactions still appear in the table on the next poll either way; only the
  *notification* depends on the tab being open.
- **Two writer threads now touch the same SQLite file** (the `SyncScheduler`'s background thread
  and the FastAPI request-handling thread(s)) — relies on `check_same_thread=False` (already set,
  ADR-0015) plus sqlite3's default 5-second busy-timeout to absorb rare write overlaps, rather
  than an explicit retry/backoff layer. Acceptable at single-user, low-write-volume scale; revisit
  if "database is locked" errors ever actually surface in practice.
- **Bug found and fixed via live verification (2026-07-19):** the dashboard's new-transaction
  polling hook tracked "have I established a baseline yet" as `lastSeenId === null`, which broke
  when zero transactions existed at page load — the first genuinely new transaction afterward was
  silently absorbed into the (still-null) baseline instead of triggering a refresh/notification.
  Fixed with an explicit `hasBaseline` flag, independent of what `lastSeenId` happens to be.
  Caught by literally inserting a transaction into an empty throwaway database and watching the
  dashboard fail to react — exactly the class of bug a written unit test (this project's frontend
  has none, per its browser-automation-driven testing strategy) might have also caught, but this
  is the mechanism actually in place.
- **Classification doesn't yet narrow candidates by the specific sender an email came from** —
  `run_classify_and_extract` tries every configured `SenderRule.content_pattern_id` against every
  processed email, since `EmailMessage` doesn't record which sender address produced it. Correct
  today (exactly one sender address, `alerts@hdfcbank.bank.in`, hosts all three confirmed
  patterns), but will need revisiting if a second bank/sender is added (REQUIREMENTS.md §9).
- No `Category` is ever assigned automatically from email content (EXT-2, by design) — a new
  `Transaction` only gets a non-null `category_id` if its payee already has a remembered default
  (COR-2, Epic E); a first-ever transaction from a brand-new payee is still uncategorized until a
  user assigns one, now possible via the dashboard (Epic F).
- **E3's "correct the payee" only renames the shared `Payee` row**, it doesn't reassign a
  transaction to a different `Payee` entity — see BACKLOG.md E3's design note. Revisit if this
  turns out to be the wrong call now that the correction UI (Epic F) is actually in use.
- **The dashboard's transaction time display is a real value for some rows and an approximation
  for others** (2026-07-19) — HDFC's UPI templates never included a time to begin with
  (REQUIREMENTS.md Appendix A), so `TransactionDateTime`
  (`frontend/src/utils/transactionTime.tsx`) falls back to the source email's received time for
  those rows, marked with a `~` prefix and a tooltip. This is deliberately visible rather than
  silently fabricated (Constitution principle 21), but it does mean the "time" column isn't a
  single consistent kind of fact across all rows. **The list/payee-history sort now accounts for
  this** (`app/domain/transaction_time.py`'s `effective_sort_datetime`, same day as the display
  itself shipped) — same-day transactions order correctly by whichever time is actually shown, real
  or approximate, rather than by database insertion order. Any *new* place that lists transactions
  should reuse this function rather than sorting by `txn_date`/`id` alone.
- **Epic F's automated live-browser pass wasn't completed against the Ubuntu VM specifically**
  (tunnel persistence issue in this session's tool environment, see §7) — superseded later the
  same day: the VM became the real production instance (ADR-0020) and was verified live and
  directly by the owner themselves (real OAuth connect, real backfill, real ongoing sync), a
  stronger check than an agent-driven browser pass would have been anyway.
- **The Mac's local database and the VM's database are now two independent, diverging histories**
  (ADR-0020) — the owner chose a fresh start on the VM over migrating the Mac's existing data.
  Nothing reconciles them; the Mac instance is stopped, not deleted, in case its history matters
  later.
- **No dashboard routing library** (e.g. React Router) — Epic F's two views (transactions,
  needs-review) are switched with plain `useState` in `App.tsx`. Fine for two views; revisit if
  Epic G's analytics views make this feel cramped.
- No manual "add a transaction with no email" escape hatch yet (COR-5, H2) — an unmatched email a
  user can't otherwise resolve just sits ignorable in the needs-review queue (F4's new "Ignore"
  action), with no way to manually record the real transaction it might represent.
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
- **Updated (B1, 2026-07-18):** the FastAPI app now touches the database directly — the
  `/gmail/connect`/`/gmail/callback` endpoints (`app/presentation/gmail_router.py`) read/write
  `GmailConnection` rows per request via `Depends(get_db)`, calling `ensure_default_user`
  lazily rather than at startup (no lifespan hook was added — not needed yet, per Constitution
  principle 2). Migrations still only run via `alembic upgrade head` (through
  `scripts/setup.py`), never automatically at app startup.

---
_Every non-trivial entry above should trace back to an ADR in [DECISIONS.md](DECISIONS.md)._
