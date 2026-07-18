# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once
versioned releases begin.

## [Unreleased]

### Added (code)
- **Epic B, B1 (Gmail OAuth connect flow) complete** — `GET /gmail/connect`/`GET /gmail/callback`
  (`app/presentation/gmail_router.py`, `app/application/connect_gmail_account.py`,
  `app/infrastructure/gmail_oauth.py`), using Google's official client libraries (ADR-0018).
  Read-only scope only (ING-2); tokens stored encrypted (ADR-0015). Verified with mocked
  responses (23 backend tests, passing on both macOS and the Ubuntu VM per ADR-0017) and against
  the owner's real Gmail account per ADR-0014. Fixed a real bug caught during that live
  verification: the token exchange initially failed with `invalid_grant: Missing code verifier`
  because the PKCE `code_verifier` Google's client library auto-generates wasn't carried over
  from the authorization step to the exchange step (two separate `Flow` objects) — now passed
  through explicitly, with a regression test.
- **Epic B, B2 (SenderRule seed data) complete** — `ensure_hdfc_sender_rules`
  (`app/infrastructure/bootstrap.py`) seeds the three confirmed HDFC templates (Appendix A);
  called from a new FastAPI lifespan hook alongside `ensure_default_user`, so baseline config
  data exists whenever the app runs rather than only lazily on first use. Verified against the
  real local database (exactly 3 rows, correct values, B1's existing connection untouched) and
  with 4 new tests (27/27 backend tests passing on macOS and the Ubuntu VM).
- **Epic B, B3 (one-time backfill sync) complete** — `run_initial_backfill`
  (`app/application/run_initial_backfill.py`, `app/infrastructure/gmail_client.py`), chained
  automatically at the end of `/gmail/callback`. Fetches every message from the configured
  `SenderRule` senders dated from the 1st of the connection's setup month (ADR-0011) onward,
  caches each as an encrypted, unprocessed `email_messages` row (dedup'd by Gmail message ID,
  ING-6/DUP-1), and creates no `Transaction` rows (that's Epic C). Uses
  google-api-python-client's built-in retry/backoff (ING-7). Verified with mocked tests
  (14 new, 41/41 total passing on macOS and the Ubuntu VM) and against the real connected
  account: 6 real HDFC emails backfilled on first run, correctly deduplicated (0 new) on a
  second run.
- **Epic B, B4 (incremental sync via Gmail History API) complete** — `run_incremental_sync`
  (`app/application/run_incremental_sync.py`) fetches only what's changed since the stored
  `historyId` checkpoint (ING-4/ING-5), rather than re-scanning the whole backfill window;
  falls back to a bounded re-scan from the last successful sync time if the checkpoint has
  aged out of Gmail's History API retention window. Shares its message-storing step with B3 via
  a new `app/application/ingest_gmail_messages.py`. Verified with mocked tests (7 new, 48/48
  total passing on macOS and the Ubuntu VM) and against the real connected account (correctly
  idempotent: 0 scanned/stored on a real repeat sync). Scheduling this automatically is
  explicitly deferred until Epic C exists (decision recorded in BACKLOG.md B4).
- **Epic B, B5 (sync health logging & status) complete — Epic B (Gmail Ingestion) now fully
  done** — `sync_state` gained `last_sync_started_at`, `last_scanned`, `last_matched`,
  `last_skipped`, `last_failed` (migration `96b145d41d66`), populated by both B3 and B4.
  `store_new_messages` (`app/application/ingest_gmail_messages.py`) now catches a per-message
  `GmailIngestionError` and counts it as failed rather than aborting the whole sync run — one
  oddly formatted email no longer blocks every other message in the same batch. A failed OAuth
  token refresh already surfaced via `sync_state.last_error` from B3/B4's existing error
  handling; added a test tying this specifically to B5's stated criterion. Verified with mocked
  tests (5 new, 53/53 total passing on macOS and the Ubuntu VM) and against the real connected
  account after applying the migration there too.
- **`scripts/vm_sync.py`, `scripts/vm_test.py`, `scripts/vm_tunnel.py`, `scripts/vm_dev.py`**
  (plus shared helper `scripts/_vm.py`): stdlib-only tooling to sync to, test on, and view the
  app running on the Ubuntu verification VM in one command each, replacing the repeated manual
  `rsync`/`ssh`/tunnel commands used to verify Epic A there. See
  [DECISIONS.md](DECISIONS.md) ADR-0017 for why (a manual sync once ran from the wrong directory
  and scattered files into the VM's project root; a manually-typed `pkill` pattern intermittently
  killed its own invoking shell) and for the Tailscale-ACL reason a tunnel is used instead of
  reaching the VM's ports directly.

### Changed
- **Verification policy:** the Ubuntu deployment VM, not macOS, is now the authoritative
  environment for a story/epic's "Definition of Done" (`docs/BACKLOG.md`) — run via the new
  `scripts/vm_test.py`/`scripts/vm_dev.py`. macOS remains the normal environment for day-to-day
  development. See [DECISIONS.md](DECISIONS.md) ADR-0017.

### Fixed
- **Epic A verified on the Ubuntu deployment target (2026-07-18):** running the project on the
  actual Ubuntu 26.04 LTS VM (rather than just macOS) surfaced a real cross-platform bug —
  Ubuntu 26.04 ships only Python 3.14 (no 3.10/3.11/3.12 available via apt or a PPA), and the
  previously pinned `sqlalchemy==2.0.36`/`alembic==1.14.0` crash under Python 3.14 due to a
  `typing` internals incompatibility. Fixed by bumping to `sqlalchemy==2.0.51` and
  `alembic==1.18.5` (same 2.0.x/1.x line already approved in ADR-0013) — verified with no
  regression on macOS and with the full setup/test/dev-server flow passing on the Ubuntu VM. See
  [DECISIONS.md](DECISIONS.md) ADR-0016.

### Added (code)
- **Epic A (Foundation) complete** — first real application code, per `docs/BACKLOG.md`:
  - `backend/`: FastAPI app in a layered structure (domain/application/infrastructure/
    presentation), `GET /health` endpoint, CORS enabled for the dashboard's origin.
  - Database: SQLAlchemy models for all 9 core tables, Alembic migration applied; `tokens` and
    `content` columns encrypted at the application level (`cryptography`/Fernet, ADR-0015);
    verified by reading the raw SQLite file directly and confirming those two fields are not
    human-readable while ordinary columns are.
  - `frontend/`: React + Vite + TypeScript dashboard scaffold with a thin `api/client.ts`
    module as the only place that calls the backend.
  - `scripts/setup.py` and `scripts/dev.py`: one-time environment setup and a single command
    to run backend + frontend together, using only cross-platform Python (no shell-specific
    scripting) per the macOS-dev/Ubuntu-deploy requirement (ADR-0015).
  - All automated tests pass (5/5); the health check and dashboard were verified live via
    browser automation, not just tests. Custom ports and `DATABASE_PATH` verified configurable.
    `python3 scripts/setup.py` then `python3 scripts/dev.py` is the full local run path.
- Git repository initialized (no commits made yet — left for the user to commit when ready);
  `.gitignore` added so `backend/data/` (the encryption key and local database) is never
  committed.

### Added
- Engineering foundation established under `/docs`: `CONSTITUTION.md`, `REQUIREMENTS.md`,
  `ARCHITECTURE.md`, `ROADMAP.md`, `DECISIONS.md`, and this `CHANGELOG.md`. See
  [DECISIONS.md](DECISIONS.md) ADR-0001.
- Product specification for the Gmail-driven expense tracker: `REQUIREMENTS.md` populated with
  functional/non-functional requirements, data model, assumptions, edge cases, deferred
  features, and an MVP definition. `ROADMAP.md` populated with milestones M1–M8. Three
  foundational product decisions recorded: local-first deployment, web-dashboard-first with a
  later mobile client, and INR-only MVP currency scope. See [DECISIONS.md](DECISIONS.md)
  ADR-0002, ADR-0003, ADR-0004.

### Changed
- Narrowed email-ingestion scope: for known e-commerce/food-delivery vendors, only the
  order-confirmation email is ingested (payment/delivery emails from those vendors excluded);
  bank/card/UPI alerts remain the source for other spend. See ADR-0005.
- Deferred phishing/prompt-injection hardening of the extraction pipeline to a later phase;
  accepted as a v1 risk. See ADR-0006.
- All 8 working assumptions in `REQUIREMENTS.md` §7 confirmed by the user; `REQUIREMENTS.md`
  §11 (Suggested Improvements) marked deferred, not adopted for MVP.
- Both blocking open questions resolved: extraction is deterministic-first with AI only as a
  rare fallback (ADR-0007); bank/card alerts matching an already-covered known vendor are
  excluded at ingestion to prevent double-counting against the vendor's order-confirmation
  email (ADR-0008).
- **Major scope simplification:** ingestion narrowed to exactly four fixed bank/UPI
  transaction-notification email types (UPI debit, UPI credit, credit card debit, credit card
  credit); all third-party vendor-email tracking (Amazon, Flipkart, Swiggy, Zomato, etc.)
  dropped entirely. Supersedes ADR-0005 and ADR-0008. See [DECISIONS.md](DECISIONS.md)
  ADR-0009.
- Sync health visibility (ING-8) and the unrecognized/unparseable-email review queue (EXT-6)
  promoted from suggested improvements to confirmed core MVP requirements.
- Category assignment resolved as fully user-defined/manual for MVP; auto-suggesting a
  category from email content noted as a post-MVP roadmap idea (see `ROADMAP.md` M6).
- Cancelled/failed-transaction handling question resolved as not applicable — there is no
  "order" concept left to cancel now that only settled bank/UPI debits and credits are
  ingested.
- Spending-coverage question resolved: the four email types capture the large majority of the
  user's spending; small/occasional exceptions (e.g. cash) are an accepted minor gap, handled
  by the existing manual add-transaction escape hatch rather than a dedicated feature
  (`REQUIREMENTS.md` §7 Assumption 9).
- Three of the four email templates confirmed against real HDFC samples (UPI debit, UPI credit,
  credit card debit); recorded as `REQUIREMENTS.md` Appendix A. Discovered that all three share
  one sender address (`alerts@hdfcbank.bank.in`), so classification needs a content-pattern
  match in addition to the sender check — recorded as [DECISIONS.md](DECISIONS.md) ADR-0010,
  which refines `SenderRule` (§5 Data Model) and ING-3. Also discovered: HDFC's credit card
  debit template has no reference number (dedup falls back to timestamp, DUP-2) and uses a
  cryptic merchant descriptor (e.g. `ASSPL`) rather than a friendly name; date/time format
  differs between UPI and credit card templates. The fourth template (credit card credit) is
  still pending from the user.
- **All remaining open questions resolved except the pending 4th template:**
  - Initial backfill starts from the first day of the current calendar month at setup time, not
    a rolling historical window (see [DECISIONS.md](DECISIONS.md) ADR-0011).
  - Source email content is cached locally at ingestion time for robust traceability (ADR-0012).
  - No export/API needed near-term (dashboard is sufficient), but the backend/API boundary must
    still be designed so a future mobile app is a clean additional client (reaffirms ADR-0003).
  - HDFC confirmed as the user's sole bank/card issuer for now (`REQUIREMENTS.md` §7
    Assumption 10); the `SenderRule` design must stay extensible to a second bank later.
  - "Credit card credit" confirmed to primarily mean a merchant refund, not a bill-payment/
    repayment confirmation (`REQUIREMENTS.md` §7 Assumption 11).
- `ARCHITECTURE.md` populated (v0.1): system overview/diagram, module boundaries (Ingestion,
  Classification, Extraction, Deduplication, Storage, Review Queue, Categorization,
  Correction, Analytics, API Layer, Web Dashboard), data storage schema outline, external
  integration isolation boundaries, cross-cutting concerns, and testing strategy.
- Technology stack recorded and **confirmed by the user**: Python/FastAPI backend, encrypted
  SQLite, React/Vite dashboard, in-process scheduler, pluggable AI-fallback interface. See
  [DECISIONS.md](DECISIONS.md) ADR-0013 (status: Accepted).
- New doc `BACKLOG.md` added: the MVP build plan (ROADMAP.md M2–M5) broken into ~30 independent,
  SCRUM-style stories across 8 epics (Foundation, Gmail Ingestion, Classification & Extraction,
  Deduplication, API Layer, Dashboard Review/Correction, Search & Analytics, Cross-cutting
  polish), each with acceptance criteria and explicit dependencies. `ROADMAP.md` updated to
  point to it instead of describing implementation tasks itself.
- Verification policy defined and added to `BACKLOG.md` ("Definition of Done") and
  `ARCHITECTURE.md` §7: automated tests (run for real, against the confirmed sample emails) for
  backend/logic stories; direct browser-driven checks for dashboard stories; user-gated live
  testing for the Gmail OAuth consent step and the first real backfill; a demo + explicit
  go-ahead required at the end of each epic before the next begins. See
  [DECISIONS.md](DECISIONS.md) ADR-0014.

### Changed
- **Platform-independence requirement added:** the app must run identically on macOS
  (development) and Ubuntu (the actual deployment target, an Ubuntu VM). Discovered that
  SQLCipher (the presumed whole-database encryption approach) fails to install even on the
  development machine — a real cross-platform native-dependency risk, not just theoretical.
- **Encryption approach revised:** "encrypted at rest" is now implemented as application-level
  encryption (via the `cryptography` package) of only the genuinely sensitive fields — Gmail
  OAuth tokens and cached raw email content. Transaction fields (amount, date, payee, category)
  are stored unencrypted; their protection depends on the host OS's own disk encryption, not a
  guarantee the app makes. `REQUIREMENTS.md` §4, `ARCHITECTURE.md` §4/§8, and `BACKLOG.md`
  stories A2/H1 updated accordingly. See [DECISIONS.md](DECISIONS.md) ADR-0015.
- Migration tooling decided: Alembic (pairs with SQLAlchemy, pure Python, no native dependency).

<!--
When cutting a release, move entries from [Unreleased] into a new dated section, e.g.:

## [0.1.0] - YYYY-MM-DD
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
-->
