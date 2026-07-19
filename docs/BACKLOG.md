# Backlog

Status: **v1.0 (web MVP) done; v1.1 (Ledger, the iOS app) planning started 2026-07-19.** All
eight original epics (A-H) are done, verified, and merged to main (2026-07-19; PR #1-#8) — see
"Epic Overview" below and each epic's own status block for what was built and how it was
verified. Foundation through Dashboard (A-F), packaging (H3), and automatic sync (H4) merged
first (PR #1-#6); Search & Analytics (G) — which completes REQUIREMENTS.md §13's MVP definition —
merged next (PR #7), along with two same-day follow-ups (transaction time display, time-based
sort order); Epic H's remaining stories (H1, already satisfied by an Epic A test; H2, the manual
add-transaction escape hatch, ADR-0022) merged last (PR #8). The Ubuntu VM is the owner's actual,
permanent, day-to-day instance (ADR-0020) — a persistent `systemd --user` service with its own
independent Gmail history; the local Mac instance has been stopped. The only web-MVP requirement
not yet fully met is the still-pending 4th email template (credit card credit, REQUIREMENTS.md
§8), which was never tied to any specific epic.

**Epics I–M below are new (2026-07-19): the story breakdown for Ledger, ROADMAP.md M7's iOS app.**
A visual design concept was reviewed and confirmed by the owner first (not tracked as a story
here — it was a standalone design pass, not a build step); Swift + SwiftUI and an
in-app/foreground-only notification scope were then decided (ADR-0023, ADR-0024) before any of
the epics below were written, per Constitution principle 20 (tradeoffs presented and agreed
before implementation, not guessed).

This is the detailed, implementation-level breakdown of [ROADMAP.md](ROADMAP.md) milestones
M2–M5 and now M7, into units small enough to pick up and build one at a time. ROADMAP.md stays
milestones-only by design; this file is where day-to-day story tracking lives instead.

Each story is scoped to one module boundary from [ARCHITECTURE.md](ARCHITECTURE.md) §3, so it
can be built and tested largely on its own — dependencies on other stories are stated
explicitly rather than assumed. "Depends on" means *must be done first*, not "related to."

Stories reference the requirement IDs they satisfy (from [REQUIREMENTS.md](REQUIREMENTS.md))
so acceptance criteria trace back to something concrete, not vibes.

**Sizing:** S = under a day, M = 1–3 days, L = 3+ days (rough, for sequencing — not a
commitment).

## How to use this file

- Work top to bottom within an epic; epics themselves are ordered by dependency (A before B
  before C, etc.) — see the Epic Overview table.
- Check a story off when its acceptance criteria are all met, not before.
- If a story turns out to hide a bigger problem, split it into new stories rather than quietly
  expanding its scope — keep the "small, focused" property intact (Constitution principle 17).
- Update this file as stories are added, split, or completed. Move genuinely new/deferred ideas
  discovered mid-build into [REQUIREMENTS.md](REQUIREMENTS.md) §12 rather than letting them
  balloon this backlog silently.

## Definition of Done (confirmed 2026-07-18, ADR-0014; revised 2026-07-18, ADR-0017)

A story is not done just because code was written for it. It's done when:

1. **Its acceptance criteria are all met**, checked explicitly against the story text — not
   assumed from "the general approach works."
2. **Automated tests exist and pass**, run for real (not just written) — this applies fully to
   Epics A–E (backend/logic): schema, classifiers, extractors, dedup, API endpoints. These are
   deterministic and get tested directly against the real sample emails in REQUIREMENTS.md
   Appendix A plus the known edge cases. **Run via `python3 scripts/vm_test.py` against the
   Ubuntu deployment VM (ADR-0017)** — a macOS-only pass is necessary but not sufficient, since
   real macOS/Ubuntu divergence has already surfaced once (ADR-0016).
3. **For dashboard stories (Epics F–G):** the actual running UI is driven directly (browser
   automation) through the flow the story describes — click search, edit a transaction, view
   the source email, etc. — and the result is observed, not just asserted. **Run against the
   Ubuntu VM via `python3 scripts/vm_dev.py`**, which starts the app there and opens the SSH
   tunnel needed to reach it (ADR-0017), not just against a local macOS instance.
4. **For anything touching live Gmail OAuth (Epic B, starting with B1):** the mechanics
   (redirect, token exchange, error handling) are tested with mocked responses first. The
   **live one-time consent click against the user's real HDFC-linked Gmail account** happens
   with the user directly — this cannot be done on the user's behalf. The first real backfill
   (B3) is validated together: the user spot-checks a handful of the resulting transactions
   against their own memory/bank statement, since real inbox variety can exceed what the three
   confirmed samples cover.

### Epic checkpoints

At the end of each epic (A, B, C, ...), before starting the next one: a short demo — what was
built, tests passing, a walkthrough of the actual behavior — followed by the user's explicit
go-ahead to continue. Epics are not to be chained through silently; each is a checkpoint, not
just an internal milestone.

## Epic Overview

| Epic | Name | Maps to | Depends on |
|---|---|---|---|
| A | Foundation (scaffolding) | ARCHITECTURE.md Infrastructure layer | none |
| B | Gmail Ingestion | REQUIREMENTS.md §3.1, ROADMAP.md M2 | A |
| C | Classification & Extraction | REQUIREMENTS.md §3.2, ROADMAP.md M3 | A, B |
| D | Deduplication | REQUIREMENTS.md §3.3, ROADMAP.md M3 | C |
| E | API Layer | REQUIREMENTS.md §3.4–3.7 (surface), ROADMAP.md M4 | A, C, D |
| F | Dashboard — Review & Correction | REQUIREMENTS.md §3.4–3.5, ROADMAP.md M4 | E |
| G | Search & Analytics (MVP complete) | REQUIREMENTS.md §3.6–3.7, ROADMAP.md M5 | E, F |
| H | Cross-cutting polish | NFRs (REQUIREMENTS.md §4) | rolling, alongside others |
| I | Ledger — iOS Foundation | REQUIREMENTS.md §15, ROADMAP.md M7 | E (backend API only; no other web epic) |
| J | Ledger — Transaction List & Correction | REQUIREMENTS.md §15 (MOB-2), ROADMAP.md M7 | I |
| K | Ledger — Needs-Review Queue | REQUIREMENTS.md §15 (MOB-2), ROADMAP.md M7 | I, J |
| L | Ledger — Analytics | REQUIREMENTS.md §15 (MOB-2), ROADMAP.md M7 | I, J |
| M | Ledger — Manual Add & Notifications | REQUIREMENTS.md §15 (MOB-4, MOB-6), ROADMAP.md M7 | J |

---

## Epic A — Foundation (Project Scaffolding)

**Status: Done (2026-07-18).** All four stories complete and verified — see the epic checkpoint
summary in [CHANGELOG.md](CHANGELOG.md) for what was actually built and tested.

### A1. Backend project scaffold ✅
**As** the developer, **I want** a FastAPI project laid out in the layered structure from
ARCHITECTURE.md §3 (domain / application / infrastructure / presentation folders), **so that**
every later story has an obvious, consistent place to live.

**Acceptance criteria:**
- Project runs locally and serves a `GET /health` endpoint returning `200 OK`.
- Folder structure matches the four layers; a README note (or code comment) states what each
  layer may/may not depend on.
- No business logic yet — this is skeleton only.

**Depends on:** none. **Size:** S.

### A2. Database + core schema, with sensitive fields encrypted ✅
**As** the developer, **I want** a SQLite database (via SQLAlchemy + Alembic) with the core
tables from ARCHITECTURE.md §4, where OAuth tokens and cached email content are encrypted at
the application level, **so that** every later story has somewhere to persist data without a
fragile native encryption dependency (ADR-0015).

**Acceptance criteria:**
- Tables exist for: `users`, `gmail_connections`, `sender_rules`, `email_messages`,
  `sync_state`, `transactions`, `payees`, `categories`, `correction_log`.
- `gmail_connections.tokens` and `email_messages.content` are encrypted before being written
  (via the `cryptography` package) and transparently decrypted on read — verified by reading
  the raw SQLite file directly and confirming those two columns are not human-readable, while
  other columns (amount, date, payee, etc.) are plain, as intended.
- The encryption key is stored outside the database file (e.g. a separate file with restrictive
  permissions), not hardcoded and not stored alongside the encrypted data.
- Alembic is set up with a first migration checked in.
- A single `users` row exists for the one owner-operator (multi-user readiness, no login yet).
- Runs identically on macOS and Ubuntu — no native/compiled dependency (ADR-0015).

**Depends on:** A1. **Size:** M.

### A3. Frontend project scaffold ✅
**As** the developer, **I want** a React + Vite project that can call the backend's
`/health` endpoint and render the result, **so that** the dashboard has a working foundation
before any real feature is built.

**Acceptance criteria:**
- `npm run dev` serves a page showing "backend: healthy" (or an error state if not reachable).
- Project structure has an obvious place for API calls (a thin client module), separate from
  UI components — the dashboard must only ever talk to the backend via the API Layer (Epic E),
  never directly to the database.

**Depends on:** A1. **Size:** S.

### A4. Local dev/run tooling ✅
**As** the owner-operator, **I want** one command (or two, clearly documented) that starts the
backend and the dashboard together, **so that** running this day-to-day doesn't require
remembering multiple manual steps.

**Acceptance criteria:**
- A single documented command starts both the backend (serving the API) and the frontend dev
  server (or, later, the built static dashboard served by the backend).
- Ports and the database file location are configurable, not hardcoded.

**Depends on:** A1, A2, A3. **Size:** S.

---

## Epic B — Gmail Ingestion (ROADMAP.md M2)

### B1. Gmail OAuth connect flow ✅
**As** the owner-operator, **I want** to grant read-only Gmail access through Google's consent
screen from within the app, **so that** the system can start reading my transaction emails.

**Acceptance criteria:**
- A "Connect Gmail" action completes the OAuth flow and stores the resulting tokens encrypted
  in `gmail_connections` (ING-1, ING-2). ✅ `GET /gmail/connect` → `GET /gmail/callback`
  (`app/presentation/gmail_router.py`), using Google's official client libraries (ADR-0018).
  Verified with mocked responses (`backend/tests/test_gmail_oauth.py`,
  `test_gmail_routes.py`) and against the owner's real HDFC-linked Gmail account
  (`naveen8f23@gmail.com`) per ADR-0014 — encrypted `tokens` column confirmed unreadable in the
  raw SQLite file, decrypts correctly through the ORM.
- Only read-only scope is requested — no send/delete/modify permission. ✅ Verified against the
  real granted token: `scopes: ["https://www.googleapis.com/auth/gmail.readonly"]`, nothing else.
- Token refresh works without user intervention; if refresh fails (e.g. access revoked), this
  is surfaced, not silently swallowed (ties into B5). ✅ `gmail_oauth.get_valid_credentials`
  refreshes an expired token using the stored `refresh_token` (present and confirmed on the real
  connection) and raises `GmailAuthError` — never silently swallowed — if refresh fails; unit
  tested for both paths. Live long-running refresh will be exercised naturally once B3/B4 sync
  runs over time.

**Bug found and fixed during live verification:** the first live consent attempt failed with
`invalid_grant: Missing code verifier` — `exchange_code` built a fresh `Flow` object for the
token exchange, separate from the one `build_authorization_url` used, losing the PKCE
`code_verifier` Google's client library auto-generates. Fixed by carrying it over explicitly
between the two steps (module-level, paired with the CSRF `state` check), with a regression test
that fails without the fix.

**Depends on:** A2. **Size:** M.

### B2. SenderRule configuration + seed data ✅
**As** the developer, **I want** the three confirmed HDFC `SenderRule`s (UPI debit, UPI credit,
credit card debit — REQUIREMENTS.md Appendix A) loaded into the database, **so that**
ingestion and classification have something real to match against.

**Acceptance criteria:**
- `sender_rules` table has one row per confirmed template: sender address
  (`alerts@hdfcbank.bank.in`), a content-pattern identifier, and the resulting transaction
  type. ✅ `ensure_hdfc_sender_rules` (`app/infrastructure/bootstrap.py`), called from a new
  FastAPI lifespan hook alongside `ensure_default_user` so both exist whenever the app actually
  runs. Verified against the real local `app.db`: exactly the 3 confirmed rows, correct sender
  address/pattern id/type, and the pre-existing B1 `gmail_connections` row left untouched.
- Adding a fourth rule later (credit card credit, or a second bank) requires only a new row,
  not a code change (validates the extensibility goal in REQUIREMENTS.md §9). ✅ `HDFC_SENDER_RULES`
  is a plain list of tuples; a dedicated test appends a 4th tuple and confirms it's picked up
  with no other change.

Tests: `backend/tests/test_sender_rules.py` (27/27 backend tests passing on macOS and the
Ubuntu VM).

**Depends on:** A2. **Size:** S.

### B3. One-time backfill sync ✅
**As** the owner-operator, **I want** the first sync to pull matching emails from the start of
the current calendar month, **so that** my tracker has a clean starting point (ADR-0011).

**Acceptance criteria:**
- On first connect, the system fetches all Gmail messages from `sender_rules` senders dated
  from the 1st of the current month to now. ✅ `run_initial_backfill`
  (`app/application/run_initial_backfill.py`) + `app/infrastructure/gmail_client.py`, chained
  automatically at the end of `/gmail/callback` (B1). Date range starts from the 1st of the
  connection's setup month (`connection.created_at`, ADR-0011), not a rolling window.
- Each matched raw email is stored as an `email_messages` row with status `unprocessed`
  (classification/extraction happens in Epic C, not here). ✅ Content is the decoded
  `text/html` MIME part (falling back to `text/plain`), preserving original formatting for
  later source-email viewing (TRC-2/F3); encrypted at rest (ADR-0015).
- No transaction records are created yet — this story only proves ingestion, not extraction.
  ✅ No `Transaction` rows are created anywhere in this story's code.

**Verified against the real connected account (`naveen8f23@gmail.com`):** 6 real HDFC emails
scanned and stored on first run; re-running scanned the same 6 and skipped all as duplicates
(ING-6/DUP-1) — 0 newly stored. Raw SQLite file confirmed `content` is a BLOB (encrypted, not
human-readable); decrypts correctly through the ORM. Verified structurally only (length,
presence of generic banking terms) — actual transaction content was deliberately never printed
to keep financial data out of any transcript.

Tests: `backend/tests/test_gmail_client.py`, `test_run_initial_backfill.py`, plus additions to
`test_gmail_routes.py` (41/41 backend tests passing on macOS and the Ubuntu VM).

**Depends on:** B1, B2. **Size:** M.

### B4. Incremental sync via Gmail History API ✅
**As** the owner-operator, **I want** subsequent syncs to only fetch what's new since the last
check, **so that** the app stays fast and doesn't reprocess my whole inbox every time (ING-4,
ING-5, ING-6).

**Acceptance criteria:**
- `sync_state` stores the last processed `historyId` per connection. ✅ Planted at the end of
  B3's backfill (`_do_backfill`, `gmail_client.get_current_history_id`), advanced by
  `run_incremental_sync` (`app/application/run_incremental_sync.py`) after each run.
- A sync run only fetches changes since that checkpoint. ✅
  `gmail_client.list_message_ids_since_history` (Gmail History API,
  `historyTypes=['messageAdded']`); results filtered to configured senders after the fact since
  History API isn't sender-scoped like `messages.list`'s `q=` (`store_new_messages`'s new
  `keep_if` hook, shared with B3 rather than a second fetch).
- Re-running a sync with no new mail creates zero new `email_messages` rows (idempotent, ties
  to DUP-1 in Epic D). ✅ Verified with mocked tests and against the real connected account
  (0 scanned/stored on a real repeat run).
- If the checkpoint is too old for Gmail's History API retention window, the system detects
  this and falls back to a bounded re-scan rather than failing silently. ✅ Catches the 404
  Gmail returns for an expired `startHistoryId` (`HistoryCheckpointExpiredError`), re-scans from
  the last successful sync time (not ADR-0011's original backfill-month window), and re-plants
  a fresh checkpoint.

**Scope note (explicit decision at the time, since superseded by H4):** nothing automatically
called `run_incremental_sync` on a schedule yet as of this story — the sync mechanism itself was
correct and tested; an in-process scheduler (ADR-0013) was deferred until Epic C existed to give
newly-synced emails somewhere to go. **Resolved 2026-07-19:** H4's `SyncScheduler`
(`app/infrastructure/sync_scheduler.py`) now calls this automatically every 5 seconds (ADR-0019).

Tests: `backend/tests/test_run_incremental_sync.py` (48/48 backend tests passing on macOS and
the Ubuntu VM).

**Depends on:** B3. **Size:** M.

### B5. Sync health logging & status ✅
**As** the owner-operator, **I want** to see when the last sync ran and whether anything went
wrong, **so that** I never have to wonder if the system is silently broken (ING-8).

**Acceptance criteria:**
- Each sync run logs: start/end time, messages scanned, matched, skipped, failed. ✅
  `sync_state` gained `last_sync_started_at`, `last_scanned`, `last_matched`, `last_skipped`,
  `last_failed` (migration `96b145d41d66`), set by both `run_initial_backfill` (B3) and
  `run_incremental_sync` (B4). A message that fails to read (`GmailIngestionError`) is now
  counted as failed and the run continues — one oddly formatted email no longer blocks every
  other message in the same sync from being stored (refined `store_new_messages`,
  `app/application/ingest_gmail_messages.py`).
- A simple status is queryable (even just a log file or a DB row at this stage — a dedicated
  API endpoint for this is Epic E, story E7). ✅ The `sync_state` row itself, queryable via the
  ORM like any other row — no dedicated read helper added, since E7 will define its own
  query/serialization needs when the actual endpoint is built.
- A failed OAuth refresh (from B1) shows up here, not just in a stack trace. ✅ Already covered
  by B3/B4's existing outer error handling (any exception, including `GmailAuthError` from a
  failed token refresh, is caught and written to `sync_state.last_error` before re-raising);
  added a test tying this specifically to an OAuth refresh failure.

**Verified against the real connected account:** re-ran both the backfill and an incremental
sync after the migration — `sync_state` correctly recorded `scanned=6, matched=0, skipped=6,
failed=0` (all 6 already-ingested messages correctly recognized as duplicates) and
`scanned=0, matched=0, skipped=0, failed=0` respectively, with `last_sync_started_at`/
`last_sync_at` both populated.

Tests: `backend/tests/test_ingest_gmail_messages.py` (new), plus additions to
`test_run_initial_backfill.py` (53/53 backend tests passing on macOS and the Ubuntu VM).

**Depends on:** B1, B3, B4. **Size:** S.

---

## Epic B — Status: Done (2026-07-18)

All five stories (B1–B5) complete, tested (53/53 backend tests passing on macOS and the Ubuntu
VM per ADR-0017), and verified against the owner's real HDFC-linked Gmail account per ADR-0014:
OAuth connect, `SenderRule` seeding, one-time backfill, incremental History-API sync, and sync
health tracking. Per the epic-checkpoint policy (ADR-0014), this is the point for a demo and the
owner's explicit go-ahead before Epic C (Classification & Extraction) begins.

---

## Epic C — Classification & Extraction (ROADMAP.md M3)

### C1. Classifier: UPI Debit ✅
**As** the developer, **I want** a function that identifies an email as "UPI Debit" using the
confirmed content markers, **so that** downstream extraction knows which template to apply.

**Acceptance criteria:**
- Given the real UPI Debit sample (REQUIREMENTS.md Appendix A.1), correctly classifies as UPI
  Debit. ✅ `is_upi_debit` (`app/domain/classification.py`) matches on the confirmed
  ADR-0010 marker pair (`"is debited from your account ending"` + `"towards VPA"`).
- Given the UPI Credit or Credit Card Debit samples, does **not** misclassify as UPI Debit. ✅
- Given an unrelated email from the same sender, returns "no match" rather than a false
  positive. ✅ Verified against a synthetic unrelated HDFC email (account-statement notice).

**Depends on:** A2, B2. **Size:** S.

### C2. Classifier: UPI Credit ✅
Same shape as C1, for the UPI Credit template (Appendix A.2) — `is_upi_credit`, matching
`"has been successfully credited to your HDFC Bank account"`. **Depends on:** A2, B2. **Size:** S.

### C3. Classifier: Credit Card Debit ✅
Same shape as C1, for the Credit Card Debit template (Appendix A.3) — `is_credit_card_debit`,
matching `"has been debited from your HDFC Bank Credit Card ending"`. **Depends on:** A2, B2.
**Size:** S.

Tests: `backend/tests/test_classification.py` — each of the three real samples classifies
correctly and doesn't cross-match the other two; also confirms matching survives the email being
HTML-wrapped (Edge Cases §10) and that `classify()` only ever considers the candidate
`content_pattern_id`s passed in (sender-then-content, per ADR-0010), not all four unconditionally.

### C4. Extractor: UPI Debit ✅
**As** the developer, **I want** a parser that turns a classified UPI Debit email into
structured fields, **so that** it can become a `Transaction` row.

**Acceptance criteria:**
- From Appendix A.1's sample, correctly extracts: amount 120.00, type debit, method UPI,
  instrument "account ending 4958", payee VPA + display name, date, reference number. ✅
  `extract_upi_debit` (`app/domain/extraction.py`); the instrument is stored as just the last 4
  digits (`"4958"`) per EXT-1's literal wording ("the last 4 digits of the account/card
  instrument"), not the full descriptive phrase.
- Handles the case where the parenthetical payee display name is absent (Edge Cases §10) —
  falls back to the VPA alone rather than failing. ✅
- Output confidence is high (EXT-5) since this is a known, matched template. ✅
  `ExtractedTransaction.confidence_score` defaults to `1.0`.

**Depends on:** C1, A2. **Size:** M.

### C5. Extractor: UPI Credit ✅
Same shape as C4, for the UPI Credit template (Appendix A.2) — including the "Sender" name +
VPA fields and the lettered "Transaction Details" layout (`extract_upi_credit`). **Depends on:**
C2, A2. **Size:** M.

### C6. Extractor: Credit Card Debit ✅
Same shape as C4, for the Credit Card Debit template (Appendix A.3) — `extract_credit_card_debit`.

**Additional acceptance criteria specific to this story:**
- Correctly parses the `18 Jul, 2026 at 18:56:45` date/time format (distinct from the UPI
  templates' `DD-MM-YY`). ✅
- Handles the **absence** of a reference number (confirmed gap in this template) without
  erroring — the field is stored as null, not a crash or a fabricated value. ✅
- Handles the `Rs. 554.00` (space after `Rs.`) vs. `Rs.120.00` (no space) formatting difference
  between templates. ✅ Single shared amount regex (`Rs\.\s*...`) tolerates both.

**Depends on:** C3, A2. **Size:** M.

Tests: `backend/tests/test_extraction.py` — all three real samples extract every field correctly;
the missing-display-name and missing-reference-number edge cases; both `Rs.`-spacing variants;
and each extractor raises `ExtractionError` (not a crash, not a guess) when a required field is
missing from otherwise-classified content.

### C7. Needs-review queue mechanics ✅
**As** the owner-operator, **I want** any email that doesn't classify or extract cleanly to be
flagged for my review instead of silently dropped or guessed at, **so that** nothing important
goes missing (EXT-5, EXT-6).

**Acceptance criteria:**
- An `email_messages` row that matches no known `SenderRule` content pattern is marked
  `needs-review`, not `ignored` or deleted, if it came from a configured sender address. ✅
  `run_classify_and_extract` (`app/application/run_classify_and_extract.py`) — every stored
  `EmailMessage` already came from a configured sender address by construction (B3/B4's
  ingestion-time sender filtering), so this applies to every row it processes.
- An email that classifies but fails extraction (e.g. unexpected internal structure) is also
  marked `needs-review`, with the classification result preserved for context. ✅ A new
  `email_messages.classified_pattern_id` column (migration `e5aa5f25c7b3`) is set as soon as
  classification succeeds, independent of whether extraction then succeeds.
- A queryable list of needs-review items exists (surfaced properly in Epic E/F). ✅
  `get_needs_review_emails` — a dedicated read helper was added (unlike B5's `sync_state`, which
  reused plain ORM queries) since Epic E's E5 endpoint will want exactly this query.

**Depends on:** C1–C6. **Size:** M.

Tests: `backend/tests/test_run_classify_and_extract.py` — unrecognized-content and
classifies-but-unparseable-content both land in `needs_review` (with `classified_pattern_id`
preserved only in the latter case); a real sample creates an `AUTO_ACCEPTED` `Transaction` with
its `Payee` correctly get-or-created (reused across two transactions for the same identifier);
a successful AI-fallback result still lands as a `NEEDS_REVIEW` transaction, never auto-accepted;
and re-running against already-`MATCHED`/`NEEDS_REVIEW` emails is a no-op (previews Epic D's D1).

### C8. AI fallback interface (stub) ✅
**As** the developer, **I want** a defined `AIFallbackClient` interface with a no-op/stub
implementation, **so that** the extraction module has a clean seam for a real AI fallback
later without being blocked on choosing a provider now (Constitution principle 10).

**Acceptance criteria:**
- Interface is defined (input: raw email content + sender; output: best-effort structured
  fields + confidence, or "unable to extract"). ✅ `AIFallbackClient` (`app/domain/ai_fallback.py`)
  — a `Protocol`, not an ABC, matching the rest of the codebase's lightweight-interface style.
- Stub implementation always returns "unable to extract," which routes the email to the
  needs-review queue (C7) — this proves the seam works without committing to a provider. ✅
  `StubAIFallbackClient.extract` always returns `None`; wired as `run_classify_and_extract`'s
  default so nothing needs to pass it explicitly yet.
- Swapping in a real implementation later requires no changes outside the Infrastructure layer.
  ✅ `run_classify_and_extract` depends only on the `AIFallbackClient` protocol, never on
  `StubAIFallbackClient` directly except as its own default value.

**Depends on:** C7. **Size:** S.

Tests: `backend/tests/test_ai_fallback.py`.

---

## Epic C — Status: Done (2026-07-19)

All eight stories (C1–C8) complete, tested (89/89 backend tests passing on macOS and the Ubuntu
VM per ADR-0017 — 36 new tests added), and run against the real confirmed HDFC samples
(REQUIREMENTS.md Appendix A) rather than synthetic stand-ins, per the Definition of Done.

**Bug found and fixed during the user's own live verification** (they made a real ₹10 UPI
transaction and separately confirmed 2 previously-backfilled real emails, per ADR-0014's
requirement that the user spot-check real results beyond the confirmed samples): the credit card
debit template's real HTML bolds its values (`Credit Card ending <b>2174</b>`), which the
extraction regexes didn't tolerate — 2 of the user's 6 originally-backfilled real emails failed
extraction and landed in needs-review as a result. Fixed by making all three extractors tolerate
HTML tags between an anchor phrase and its value, not just whitespace (`app/domain/extraction.py`
`_GAP`), with regression tests using fabricated values reproducing the shape. Verified against
the user's own real data: both previously-failed emails, and the new real ₹10 UPI debit + ₹10 UPI
credit transaction, now parse correctly — confirmed by reporting *only* type and amount back to
the user, per the same minimal-disclosure precedent as Epic B's live verification.

**Also discovered (not a bug):** a real 5th HDFC email shape — a credit card bill payment made
via net banking — correctly falls to needs-review rather than being counted as a transaction,
exactly matching REQUIREMENTS.md §7 Assumption 11's prediction. See REQUIREMENTS.md Edge Cases
§10 and CHANGELOG.md for the full record.

Demoed live (including the two real bugs above, found via the owner's own real transactions) and
confirmed by the owner. Committed as one whole and merged to main via
[PR #3](https://github.com/Naveen8f23/Expense-Tracker/pull/3), per the epic-checkpoint policy
(ADR-0014) and the same commit-once-per-epic approach as Epic B.

**Scope note:** classification currently considers every configured `SenderRule.content_pattern_id`
as a candidate for every processed email, rather than narrowing to the specific sender address an
email came from — correct today since exactly one sender address (`alerts@hdfcbank.bank.in`)
exists, but `EmailMessage` doesn't itself record which sender address a message came from. If a
second bank/sender is added later (REQUIREMENTS.md §9), this will need revisiting so classification
narrows candidates per-message rather than trying every known bank's patterns against every email.

---

## Epic D — Deduplication (ROADMAP.md M3)

**Design note before the stories below:** unlike Epics B/C, Epic D added no new production code.
DUP-1 and DUP-2 turned out to already be fully guaranteed by constraints introduced in earlier
epics — `email_messages.message_id` is `unique` (A2), `transactions.email_message_id` is
`unique` (A2), and C7's `run_classify_and_extract` only ever processes `UNPROCESSED` emails, so
an already-`MATCHED`/`NEEDS_REVIEW` email is never reprocessed. There is also no content-based
matching step anywhere (by design — ADR-0009 deliberately dropped the vendor/bank-alert
correlation problem that would have needed one). A dedicated `Deduplicator` component, as sketched
in `ARCHITECTURE.md`'s original module list, would have had no actual logic to hold — adding one
anyway would be exactly the unnecessary-abstraction Constitution principle 2 warns against. Both
stories below are confirming tests against the real pipeline, not new logic.

### D1. Message-ID based duplicate detection ✅
**As** the owner-operator, **I want** the same Gmail message never to become two transactions,
**so that** re-syncs or retries don't inflate my history (DUP-1).

**Acceptance criteria:**
- Re-running ingestion (B3/B4) against an already-processed message ID is a no-op — zero new
  `transactions` rows. ✅
- Covered by an automated test that ingests the same sample email twice. ✅
  `TestDup1MessageIdDeduplication` (`backend/tests/test_deduplication.py`) — ingests one message,
  confirms one `Transaction`; re-ingests the identical message ID, confirms it's recognized as an
  existing message (ING-6) with no second `EmailMessage` row; re-runs
  `run_classify_and_extract` again, confirms it's a no-op (the email is no longer `UNPROCESSED`)
  and the `Transaction` count is still exactly one.

**Depends on:** C4–C6. **Size:** S.

### D2. Reference-number / timestamp fallback disambiguation ✅
**As** the owner-operator, **I want** two genuinely separate transactions with the same
amount/payee/day to both be recorded, **not** merged, **so that** real spending isn't lost
(DUP-2).

**Acceptance criteria:**
- Two UPI transactions with the same amount, payee, and day but different reference numbers
  both create separate `transactions` rows. ✅
- For the Credit Card Debit template (no reference number, per C6), two same-day/same-
  amount/same-payee transactions are disambiguated by full timestamp instead, and still both
  recorded as separate rows if their timestamps differ. ✅

**Depends on:** D1. **Size:** M.

Tests: `TestDup2ReferenceNumberAndTimestampDisambiguation`
(`backend/tests/test_deduplication.py`) — two UPI debits, same amount/payee/day, different
reference numbers, both recorded (and correctly share one `Payee` row — reuse, not a merge); two
credit card debits, same amount/payee/day, different times, both recorded; and, to make the "no
content-based matching at all" design explicit rather than merely assumed, two credit card debits
with an *exact* coincidental match on amount/payee/day/time-to-the-second are still both recorded
as separate transactions, since disambiguation here is by Gmail message ID (DUP-1), never by
comparing transaction content across messages.

93/93 backend tests passing (4 new) on macOS and the Ubuntu VM (ADR-0017). Demoed and confirmed by
the owner; committed and merged to main via
[PR #4](https://github.com/Naveen8f23/Expense-Tracker/pull/4), per the epic-checkpoint policy
(ADR-0014).

---

## Epic E — API Layer (ROADMAP.md M4 foundation)

### E1. List/search transactions endpoint ✅
**As** the dashboard, **I want** an endpoint to list transactions with filters, **so that** the
UI never queries the database directly (SRCH-1).

**Acceptance criteria:**
- `GET /transactions` supports filtering by payee, category, date range, amount range, payment
  method, and type, plus free-text. ✅ `app/application/list_transactions.py`
  (`list_transactions`/`TransactionFilters`) + `app/presentation/transactions_router.py`.
  Free-text (`q`) matches payee name/identifier or category name — the human-readable text
  fields on a transaction, not amount/date/reference number (those have dedicated filters).
- Paginated; performs well against a few thousand rows (SRCH-2 — no hard number required yet,
  just "not obviously slow"). ✅ `limit`/`offset` query params (default 50, max 200); response
  includes `total` for the caller to build pagination controls.
- **Also enforced here (not stated as an E1 criterion, but load-bearing):** dismissed
  transactions (COR-4) are excluded by default.

**Depends on:** A2, C4–C6, D1–D2. **Size:** M.

### E2. Get single transaction (with source email) endpoint ✅
**As** the dashboard, **I want** to fetch one transaction plus its linked source email content,
**so that** the user can verify extraction against the original (TRC-1, TRC-2).

**Acceptance criteria:**
- `GET /transactions/{id}` returns the transaction fields and the cached email content
  (ADR-0012) it was derived from. ✅ `app/presentation/transactions_router.py`
  (`get_transaction_endpoint`); scoped to the requesting user's own transactions (returns 404,
  not another user's data, for an id that isn't theirs — REQUIREMENTS.md §9 multi-user
  readiness, even though only one user exists today).

**Depends on:** E1. **Size:** S.

### E3. Edit/correct transaction endpoint ✅
**As** the dashboard, **I want** an endpoint to update a transaction's fields, **so that** the
user can fix extraction mistakes (COR-1, COR-3).

**Acceptance criteria:**
- `PATCH /transactions/{id}` accepts amount, date, payee, category, payment method, type. ✅
  `app/application/correct_transaction.py` (`correct_transaction`/`TransactionCorrection`).
  **Design note on "payee":** correcting it renames the shared `Payee` row (`name`) rather than
  reassigning the transaction to a different `Payee` entity — REQUIREMENTS.md's data model
  explicitly defers "alias normalization" (treating two similar payee strings as one real-world
  entity) as a post-MVP idea; a full reassign-to-a-different-payee flow would be building that
  early. A naming correction is what COR-1 is understood to mean for MVP.
- Writes an entry to `correction_log` capturing the before/after values. ✅ One `CorrectionLog`
  row per changed field (a no-op field, e.g. re-submitting the same amount, doesn't log).
- Assigning a category to a payee is remembered so future transactions from that payee default
  to it (COR-2) — this is the categorization module's only real logic for MVP. ✅ New
  `payees.default_category_id` column (migration `dcdef4f896b2`); `run_classify_and_extract`
  (Epic C) now looks this up when creating a *new* transaction, rather than always leaving
  `category_id` null — a small, deliberate cross-epic change tying E3 back into C7's
  transaction-creation step.
- **Also added (not stated as a criterion, but the only place it makes sense to set):**
  correcting a transaction sets its `review_status` to `USER_CONFIRMED` — the one `ReviewStatus`
  value nothing else in the system ever sets.

**Depends on:** E1, E2. **Size:** M.

### E4. Mark "not a real expense" endpoint ✅
**As** the dashboard, **I want** to hide a misclassified transaction from analytics without
deleting its audit trail, **so that** my summaries stay accurate (COR-4).

**Acceptance criteria:**
- `POST /transactions/{id}/dismiss` (or similar) excludes it from search/analytics by default
  but keeps the row and its source email intact. ✅ `app/application/dismiss_transaction.py`;
  E1's `list_transactions` already excludes `dismissed=True` rows by default, so this criterion
  is satisfied by the two stories working together, not duplicated filtering logic.

**Depends on:** E1. **Size:** S.

### E5. Needs-review queue endpoint ✅
**As** the dashboard, **I want** an endpoint listing everything in the needs-review state,
**so that** the review UI (Epic F) has something to show (EXT-5, EXT-6, C7).

**Acceptance criteria:**
- `GET /needs-review` returns all `email_messages`/`transactions` currently flagged, with
  enough context (raw content, attempted classification) to review without leaving the app. ✅
  `app/application/get_needs_review_queue.py` combines both distinct needs-review concepts:
  `EmailMessage`s that never became a transaction at all (C7's `get_needs_review_emails`) and
  `Transaction`s an AI fallback produced but that were never auto-accepted (EXT-4/EXT-5) — the
  dashboard needs both to build one review screen.

**Depends on:** C7, E1. **Size:** S.

### E6. Category CRUD endpoints ✅
**As** the dashboard, **I want** endpoints to list, create, rename, and delete categories,
**so that** category assignment (EXT-2) is fully user-driven.

**Acceptance criteria:**
- Full CRUD on `categories`; no fixed system list is seeded (per REQUIREMENTS.md §5). ✅
  `app/application/manage_categories.py` + `app/presentation/categories_router.py`. Creating a
  duplicate name for the same user is rejected (409) rather than silently allowed — the existing
  `uq_category_user_name` constraint (Epic A) now actually gets exercised.
- Deleting a category in use prompts reassignment rather than leaving orphaned references. ✅
  `DELETE /categories/{id}` without a `reassign_to` query param returns 409 with the affected
  transaction count if the category is in use; providing `reassign_to` moves those transactions
  (and any payee's remembered `default_category_id` pointing at the deleted category) to the
  replacement before deleting. "Prompts" is realized as the API layer's contract here — the
  actual prompting UI is Epic F's job.

**Depends on:** A2. **Size:** S.

### E7. Sync health status endpoint ✅
**As** the dashboard, **I want** an endpoint exposing the last sync's health (B5), **so that**
the UI can show it without reading log files directly.

**Acceptance criteria:**
- `GET /sync/status` returns last sync time, counts (scanned/matched/skipped/failed), and any
  current error state. ✅ `app/application/get_sync_status.py` +
  `app/presentation/sync_router.py`. Returns 404 if no Gmail account is connected yet, and a
  distinct `"synced": false` shape if connected but the first backfill hasn't run.

**Depends on:** B5, A2. **Size:** S.

Tests: `backend/tests/test_transactions_routes.py` (E1-E4, 10 tests),
`backend/tests/test_needs_review_routes.py` (E5, 2 tests),
`backend/tests/test_categories_routes.py` (E6, 8 tests),
`backend/tests/test_sync_routes.py` (E7, 3 tests), plus one new test in
`test_run_classify_and_extract.py` confirming the COR-2 default-category wiring. 117/117 backend
tests passing (24 new) on macOS and the Ubuntu VM (ADR-0017); the new `payees.default_category_id`
migration (`dcdef4f896b2`) was applied to both the local and VM real databases.

---

## Epic E — Status: Done (2026-07-19)

All seven stories (E1–E7) complete. No dashboard exists yet to drive these endpoints through a
browser (that's Epic F) — verified via automated tests (TestClient), and additionally by starting
the real server against a throwaway database and exercising every endpoint live with curl, per
the Definition of Done for backend/logic stories. Demoed and confirmed by the owner; committed and
merged to main via [PR #5](https://github.com/Naveen8f23/Expense-Tracker/pull/5), per the
epic-checkpoint policy (ADR-0014).

---

## Epic F — Dashboard: Review & Correction (ROADMAP.md M4)

**Addendum discovered while planning F4 (2026-07-19):** F4's "each item can be... dismissed"
doesn't work as written for the *unmatched-email* half of the needs-review queue — E4's dismiss
only operates on a `Transaction`, and an unmatched email has none. Added a small new endpoint,
`POST /needs-review/emails/{id}/ignore` (`app/application/ignore_needs_review_email.py`), reusing
the previously-unused `EmailMessageStatus.IGNORED` value, so the dashboard has a real action for
this case. Confirmed with the user before building (not assumed).

### F1. Transaction list/table view ✅
**As** the owner-operator, **I want** to see my transactions in a searchable/filterable table,
**so that** I can browse my spending (SRCH-1).

**Acceptance criteria:** filters from E1 are all exposed in the UI; table is usable with a few
hundred rows without noticeable lag. ✅ `frontend/src/components/TransactionsView.tsx` — every
E1 filter (payee, category, date range, amount range, method, type, free-text) plus pagination
controls.

**Depends on:** E1, A3. **Size:** M.

### F2. Transaction detail + correction form ✅
**As** the owner-operator, **I want** to open a transaction and edit any field, **so that** I
can fix mistakes (COR-1).

**Acceptance criteria:** every editable field from E3 has a form control; saving calls E3 and
reflects immediately in F1's table. ✅ `frontend/src/components/TransactionDetailPanel.tsx` —
opens as a side panel from a table row (F1) or a needs-review item (F4); a "Not a real expense"
button (E4) is included alongside Save, since both act on the same transaction.

**Depends on:** E2, E3, F1. **Size:** M.

### F3. Source email viewer ✅
**As** the owner-operator, **I want** to see the original email a transaction came from,
**so that** I can verify the extraction (TRC-2).

**Acceptance criteria:** accessible from F2; shows the cached email content from E2. ✅ A
"View source email" toggle inside `TransactionDetailPanel`. **Security note:** the cached content
is untrusted external HTML (a real bank/UPI email; ADR-0006 explicitly deferred, not eliminated,
phishing-hardening). It is rendered as plain escaped text inside a `<pre>`, never via
`dangerouslySetInnerHTML` — rendering it as trusted HTML would be a real stored-XSS vector.

**Depends on:** E2, F2. **Size:** S.

### F4. Needs-review queue view ✅
**As** the owner-operator, **I want** a dedicated screen listing everything needing my
attention, **so that** nothing gets missed (EXT-5, EXT-6).

**Acceptance criteria:** lists items from E5; each item can be corrected (reuses F2) or
dismissed (reuses E4 pattern). ✅ `frontend/src/components/NeedsReviewView.tsx` — unmatched
emails get "View" (raw content, same safe rendering as F3) and "Ignore" (the new endpoint above);
low-confidence transactions get "Review", opening the same `TransactionDetailPanel` as F2/F1.

**Depends on:** E5, F2. **Size:** M.

**Bug found and fixed via live browser verification:** dismissing a low-confidence transaction
("Not a real expense") left it visibly stuck in the needs-review queue — `get_needs_review_queue`
filtered only by `review_status == NEEDS_REVIEW` and never checked `dismissed`, because dismissing
a transaction doesn't change its `review_status`. Fixed by also excluding `dismissed=True` rows;
regression test added (`test_a_dismissed_transaction_no_longer_appears_in_the_queue`). This is
exactly the kind of thing the "drive the actual running UI" Definition of Done exists to catch —
found by clicking through the real flow, not by reasoning about the code.

### F5. Category creation/assignment UI ✅
**As** the owner-operator, **I want** to create and assign categories directly from a
transaction, **so that** categorizing is a single smooth action, not a side trip.

**Acceptance criteria:** category picker on F2 supports "create new" inline; calls E6 and E3
together. ✅ The category `<select>` in `TransactionDetailPanel` has a "+ New category…" option
that reveals a name field; saving calls `POST /categories` (E6) then `PATCH /transactions/{id}`
(E3) with the new category's id, verified live (created "Friends & Family" inline, transaction
list updated immediately with the new category shown).

**Depends on:** E6, F2. **Size:** S.

Verified by directly driving the running dashboard (browser automation) through every flow above
against a seeded local backend — not just written and assumed to work, per the Definition of Done
for dashboard stories. **Not verified against the Ubuntu VM specifically**, unlike prior epics:
`scripts/vm_test.py`'s 121/121 backend pass confirms the backend logic is cross-platform-correct
(the actual risk ADR-0016 was about), and `scripts/dev.py` was confirmed to start both the backend
and Vite dev server correctly on the VM directly (its own log showed a clean startup), but the
SSH-tunneled *browser* pass against the VM's frontend couldn't be completed in this session due
to the tunnel not persisting reliably in the tool environment used — a tooling gap, not a finding
about the app. The dashboard itself is plain client-side React/Vite with no OS-specific code path,
so this is a materially lower-risk gap than the backend/interpreter divergence ADR-0016 covers.
Revisit if `scripts/vm_dev.py`'s tunnel proves flaky in normal use too, not just in this session.

**Also found and cleaned up (unrelated to this epic's code):** an orphaned `multiprocessing`
worker process on the VM, left over from an earlier `--reload`-mode session, had been silently
squatting on port 8000 for hours. It wasn't matched by `vm_dev.py`'s existing pkill patterns
(its command line doesn't contain `uvicorn app.presentation.main`), causing new backend starts
to silently fail to bind while an old process kept answering health checks. Killed manually;
not yet fixed in the tooling itself (a real, if minor, gap in ADR-0017's cleanup patterns) —
flagged here rather than left for the next person to rediscover.

---

## Epic F — Status: Done (2026-07-19)

All five stories (F1–F5) complete, verified by directly driving the running dashboard through
every flow (table filtering, opening a transaction, editing it, viewing its source email,
creating and assigning a category inline, dismissing a transaction, ignoring an unmatched email)
against a seeded local backend. One real bug found and fixed this way (dismissed transactions
stuck in the needs-review queue — see F4 above); zero bugs found in F1/F2/F3/F5's own flows.
Demoed live (the owner tested it directly, including making real transactions and watching them
sync), which led straight into H3/H4 the same day. Committed together with H3 and H4 and merged
to main via [PR #6](https://github.com/Naveen8f23/Expense-Tracker/pull/6), per the
epic-checkpoint policy (ADR-0014).

---

## Epic G — Search & Analytics (ROADMAP.md M5 — MVP complete)

### G1. Search/filter UI polish ✅
**As** the owner-operator, **I want** the filters from F1 to feel fast and easy to combine,
**so that** finding a specific transaction is quick.

**Scope note (no acceptance criteria given originally; resolved via AskUserQuestion 2026-07-19):**
the owner chose **functional + visual polish**, explicitly not URL-persisted filters.

**Acceptance criteria (as resolved):**
- The free-text (`q`) and payee-contains inputs are debounced (~400ms) so typing doesn't fire one
  request per keystroke. ✅ `frontend/src/components/TransactionsView.tsx` — a local `searchDraft`
  state holds the controlled input values; a `useEffect` timer commits them into the actual
  `filters` state (which triggers the fetch) only after the pause. Verified live: 6 keystrokes
  produced exactly one `GET /transactions?q=...` request (checked via the Network tab).
- A "Clear all filters" button resets every filter and the visible input/select/date values in
  one action. ✅ All filter inputs became controlled (bound to `filters`/`searchDraft`) so
  clearing state also visibly clears the DOM — the previous uncontrolled inputs couldn't have
  supported this.
- Active filters are shown as removable chips near the filter bar, each independently clearable.
  ✅ A chips row renders one chip per non-empty filter with a human-readable label and a "×".

**Depends on:** F1. **Size:** S.

### G2. Monthly summary ✅
**As** the owner-operator, **I want** a monthly total (and a way to move between months),
**so that** I can see my spending at a glance (ANL-1, ANL-4).

**Acceptance criteria:** a `GET /analytics/monthly` endpoint plus a dashboard view; bucketed
consistently by transaction date (not email-received date, per Edge Cases §10). ✅
`app/application/analytics.py` (`get_monthly_summary`) + `app/presentation/analytics_router.py`.
Reports `total_debit`/`total_credit`/`net` (ADR-0021's sign convention) for a `month=YYYY-MM`
query param, defaulting to the current month. `frontend/src/components/AnalyticsView.tsx` adds a
third "Analytics" tab with Previous/Next month navigation and summary cards. Verified live:
navigating between June 2026 (no data) and July 2026 (16 transactions) updated the cards
correctly.

**Depends on:** E1, F1. **Size:** M.

### G3. Category breakdown ✅
**As** the owner-operator, **I want** to see spend by category for a selected period, **so
that** I understand where money goes (ANL-2).

**Acceptance criteria:** a `GET /analytics/by-category` endpoint plus a dashboard view (a
simple table or bar chart is enough for MVP — no charting library commitment implied here). ✅
`get_category_breakdown` — debits only (ADR-0021: a refund isn't spend), grouped by category
with an "Uncategorized" bucket for `category_id IS NULL`, ordered by total descending. Rendered
as a plain `<table>` in `AnalyticsView.tsx` below the summary cards, reusing the same month
cursor as G2 (ADR-0021) rather than a separate period picker.

**Depends on:** G2. **Size:** M.

### G4. Payee history ✅
**As** the owner-operator, **I want** to see all transactions with a given payee and their
total, **so that** I can spot patterns per merchant/person (ANL-3).

**Acceptance criteria:** a `GET /analytics/by-payee/{payee}` endpoint plus a dashboard view,
reachable by clicking a payee name from F1. ✅ `get_payee_history` matches case-insensitively by
exact name (ADR-0021) and 404s for a name with no transactions; a new
`frontend/src/components/PayeeHistoryPanel.tsx` slides in (same `.panel` shape as F2's detail
panel) when a payee name is clicked in `TransactionsView`'s table, showing totals plus a
clickable transaction list — clicking one opens the existing `TransactionDetailPanel` on top,
verified live end-to-end.

**Depends on:** E1, F1. **Size:** S.

Tests: `backend/tests/test_analytics_routes.py` (8 tests) — monthly totals across a month
boundary and excluding dismissed rows; category breakdown excludes credits and buckets
uncategorized separately; payee history matches case-insensitively, excludes dismissed, and 404s
for an unknown name. 139/139 backend tests passing (8 new) on macOS and the Ubuntu VM
(`scripts/vm_test.py`). Dashboard verified by directly driving the running UI (Browser tool)
through every flow above, per the Definition of Done for dashboard stories — no bugs found this
time.

---

## Epic G — Status: Done (2026-07-19)

All four stories (G1–G4) complete — this closes out REQUIREMENTS.md §13's MVP definition, modulo
the still-pending 4th email template (credit card credit, REQUIREMENTS.md §8). Five money-
semantics/scope decisions not spelled out in the original story text (sign convention, debit-only
category breakdown, shared month cursor, exact-name payee matching, no date scoping on payee
history) are recorded as [DECISIONS.md](DECISIONS.md) ADR-0021.

---

## Epic H — Cross-cutting polish (rolling, alongside other epics)

### H1. Sensitive-field encryption verification ✅
**As** the owner-operator, **I want** confirmation that OAuth tokens and cached email content
are genuinely unreadable in the raw database file, **so that** the NFR in REQUIREMENTS.md §4
(as revised by ADR-0015) is actually true, not just assumed.

**Acceptance criteria:** an automated test opens the raw SQLite file directly (bypassing the
application) and asserts `gmail_connections.tokens` and `email_messages.content` are not
human-readable, while confirming this is understood as field-level, not whole-file, protection
(ADR-0015) — not a one-time manual check. ✅ **Already satisfied, no new code needed (confirmed
2026-07-19):** `backend/tests/test_schema.py::test_sensitive_fields_are_encrypted_at_rest`, built
during Epic A2 (2026-07-18), already does exactly this — reads the raw SQLite file's bytes
directly, asserts the OAuth token and email content aren't present as plaintext, confirms a plain
column (a payee name) *is* found as plaintext (proving field-level, not whole-file, protection),
and confirms the ORM transparently decrypts on read. This story was effectively done from Epic A
onward; just never cross-referenced here.

**Depends on:** A2. **Size:** S.

### H2. Manual "add a transaction" escape hatch ✅
**As** the owner-operator, **I want** to add a transaction that has no corresponding email,
**so that** the rare cash purchase isn't lost (COR-5).

**Acceptance criteria:** a form (reusing F2's shape) with no source email required; clearly
visually distinct from auto-ingested transactions so it stays the exception, not confused with
the norm. ✅ `transactions.email_message_id` is now nullable (ADR-0022, migration `8bcc9bb76003`)
— `NULL` *is* the "manually added" marker. `app/application/add_manual_transaction.py`
(`add_manual_transaction`) + `POST /transactions`
(`app/presentation/transactions_router.py`); payee matched case-insensitively by name (no VPA to
key on), COR-2 default-category behavior mirrors `correct_transaction`/
`run_classify_and_extract`. `frontend/src/components/AddTransactionPanel.tsx` — a new "+ Add
transaction" button in `TransactionsView`, a persistent "Manually added — no source email" banner
(not just a one-time confirmation), no time field (matches F2's shape). Visually distinct in the
table via a "Manual" badge next to the payee name wherever `email_message_id` is null;
`TransactionDetailPanel` replaces its "View source email" button with the same manual-entry note
for these rows, rather than showing a broken/empty toggle.

Tests: `backend/tests/test_transactions_routes.py::TestAddManualTransaction` (3 tests: no source
email created, case-insensitive payee reuse, COR-2 default-category both ways) +
`backend/tests/test_transaction_time.py` (new `created_at`-fallback tier). 148/148 backend tests
passing (4 new) on macOS and the Ubuntu VM. Verified live: added two manual transactions via the
running dashboard (Browser tool) for the same payee in different letter-casing — confirmed the
"Manual" badge, the detail panel's no-source-email note, correct sort position via the
`created_at` fallback, and that the second entry's category was auto-applied from the first
(COR-2) without being asked again.

**Depends on:** E3, F2. **Size:** S.

### H3. Packaging/run script ✅
**As** the owner-operator, **I want** a clean, documented way to start the whole system,
**so that** running this day-to-day doesn't require remembering developer setup steps.

**Acceptance criteria:** builds on A4; produces something closer to "double-click to start" or
a single documented command, once the frontend is built for real use (not just `npm run dev`).
✅ **Resolved 2026-07-19 (ADR-0020), superseding the original "local double-click" framing:** the
owner-operator asked for the Ubuntu VM to become the actual, permanent, day-to-day instance (not
just ADR-0017's test target) — so "day-to-day" now means "always running on the VM," not "start
it locally each time." The frontend is built for real use (`frontend/dist`, served by the backend
itself, `app/presentation/main.py`'s static mount — one process, one port, no separate Vite dev
server) — the literal thing this criterion had been waiting on. Running it is now a
`systemd --user` service (`deploy/expense-tracker.service`, `deploy/README.md`) that auto-starts,
auto-restarts, and needs no manual command day-to-day at all — stronger than "double-click," it
just stays up. `scripts/deploy_vm.py` is the single command for pushing a future code change live
(sync, deps, migrations, frontend rebuild, service restart).

**Depends on:** A4, and practically, most of the rest of the backlog. **Size:** M.

### H4. Automatic background sync + live dashboard updates ✅
**As** the owner-operator, **I want** new transactions to appear on the dashboard on their own,
**so that** I never need a manual "sync now" action, and can react to a new transaction (assign
its category) about as fast as if I'd gotten a push notification for it.

**Acceptance criteria (added 2026-07-19, requested live during Epic F testing):**
- The backend polls the connected Gmail account and runs classify/extract automatically, with no
  manual trigger. ✅ `SyncScheduler` (`app/infrastructure/sync_scheduler.py`) — a background
  thread, 5-second default interval, started/stopped from FastAPI's lifespan hook. See ADR-0019
  for why 5 seconds, not the 1 second first requested, and why this is a local poll rather than
  Gmail's real push API.
- The dashboard reflects new transactions without a page reload. ✅ New
  `GET /transactions/recent?since_id=` endpoint +
  `frontend/src/hooks/useNewTransactionNotifications.ts`, polled every 5 seconds; detected new
  transactions force a table refresh regardless of the currently-active filters.
- Getting alerted to a new transaction feels like a push notification, clickable straight to
  correcting/categorizing it. ✅ A real browser `Notification` (after a one-time permission grant
  — browsers require a user gesture, it can't be requested silently) whose `onclick` opens that
  transaction's `TransactionDetailPanel` (F2) directly.

**Depends on:** B4, C7, E1, F1, F2. **Size:** M.

Tests: `backend/tests/test_sync_scheduler.py` (6 tests: runs, skips gracefully with no
connection, skips gracefully with no backfill yet, survives a failing cycle, idempotent start),
`backend/tests/test_transactions_routes.py::TestGetRecentTransactions` (4 tests, including a
regression guard that `/transactions/recent` isn't swallowed by the `/{transaction_id}` route).
131/131 backend tests passing on macOS and the Ubuntu VM.

**Bug found and fixed via live verification:** the frontend polling hook tracked "has a baseline
been established" as `lastSeenId === null`, which broke when zero transactions existed at page
load — the first real new transaction afterward was silently absorbed into the (still-null)
baseline instead of triggering a refresh. Caught by inserting a transaction into an empty
database and watching the dashboard fail to react; fixed with an explicit `hasBaseline` flag
independent of what `lastSeenId` happens to be. See ARCHITECTURE.md §8 for the full note.

---

## Epic H — Status: Done (2026-07-19)

All four stories (H1–H4) complete. H1 turned out to already be satisfied by an Epic A2 test (no
new code); H3/H4 were built the same day as Epic F; H2 (this session) required a small,
intentional schema change (`transactions.email_message_id` now nullable, ADR-0022) to represent
"no source email" honestly rather than working around it. 148/148 backend tests passing (4 new)
on macOS and the Ubuntu VM; dashboard verified live via the Browser tool.

---

## Epic I — Ledger: iOS Foundation (ROADMAP.md M7)

**Status: Done (2026-07-19).** Every story below is presentation-only (Constitution principle 5)
— no backend endpoint is added, changed, or removed by this epic. Native Swift + SwiftUI per
ADR-0023. I1 confirmed running on the owner's own iPhone; I3's live phone check surfaced the real
VM/Tailscale reachability gap (ADR-0026) rather than an I3 defect — I3's own reachability-check
behavior is confirmed correct. Committed together with Epic J (J1-J4) and merged to main via
[PR #9](https://github.com/Naveen8f23/Expense-Tracker/pull/9).

### I1. Xcode project scaffold ✅
**As** the developer, **I want** a SwiftUI app target laid out with the same dependency
discipline as the rest of this codebase (a layer that renders UI must not itself make network
calls; a layer that makes network calls must not import SwiftUI), **so that** Ledger has an
obvious, consistent place for later stories to live, mirroring ARCHITECTURE.md §3's existing rule
for the backend and the frontend.

**Acceptance criteria:**
- A three-tab `TabView` shell (Ledger / Analytics / Review) builds and runs on the owner's own
  iPhone via Xcode, matching the tab icons/labels from the confirmed design concept. ✅ Confirmed
  building and running on the owner's real iPhone via free Xcode signing (following the trust/
  developer-mode prompts once). Tab icons (`list.bullet.rectangle` / `chart.pie` / `checklist`)
  are placeholders, not yet checked against the original confirmed design mockup's exact choices —
  revisit if/when that Artifact is available again; not a blocker for I2/I3.
- Folder structure has clearly separate places for views, view-state, and networking — a
  README note (or code comment) states the dependency direction, same spirit as A1's backend note.
  ✅ `ios/Ledger/Ledger/{App,Views,ViewState,Networking}` + `ios/Ledger/README.md` states the rule
  (Views may not call networking directly; Networking may not import SwiftUI).
- No business logic yet, no network calls yet — skeleton only. ✅ Each tab is a placeholder
  `Text` view.
- Installed via free Xcode signing (personal-team), not TestFlight — the accepted distribution
  path per ADR-0024. The provisioning profile's ~7-day expiry (requiring a reconnect-and-rebuild)
  is a known, accepted cost of this path, not a bug to chase. ✅ Confirmed working this way.

**Implementation note:** the `.xcodeproj` is generated from a checked-in `ios/Ledger/project.yml`
via [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`;
`cd ios/Ledger && xcodegen generate`) rather than hand-edited — keeps the project definition
diffable in git. The generated `.xcodeproj`/`DerivedData`/`xcuserdata` are gitignored, same
reasoning as not committing `node_modules`. Verified: `xcodebuild ... -sdk iphonesimulator build`
succeeds and the shell installs/launches correctly in the simulator (screenshot-checked) before
the owner separately confirmed it on their own physical iPhone.

**Depends on:** none. **Size:** S.

### I2. Backend API client module ✅
**As** the developer, **I want** a single networking module wrapping every backend endpoint
Ledger will call, **so that** no view ever talks to `URLSession` directly — the same rule
`frontend/src/api/client.ts` already follows for the web dashboard.

**Acceptance criteria:**
- Codable Swift structs modeling the JSON shape of every endpoint below; one function per
  endpoint, no speculative methods for endpoints that don't exist:
  `GET /transactions`, `GET /transactions/{id}`, `PATCH /transactions/{id}`,
  `POST /transactions/{id}/dismiss`, `POST /transactions` (H2 manual add),
  `GET /transactions/recent?since_id=`, `GET /needs-review`,
  `POST /needs-review/emails/{id}/ignore`, `GET`/`POST`/`PATCH`/`DELETE /categories`,
  `GET /sync/status`, `GET /analytics/monthly`, `GET /analytics/by-category`,
  `GET /analytics/by-payee/{payee}`. ✅ `ios/Ledger/Ledger/Networking/{Models,Requests,APIClient,
  APIError,URLSessionProtocol}.swift`. Also added `GET /health` (I3 explicitly needs it for its
  reachability check, and it's a real, already-built endpoint — not speculative). Every field name
  was read directly from `backend/app/presentation/serializers.py` and each router/application-
  layer file, not guessed from REQUIREMENTS.md's prose — e.g. money fields are `String` (the
  backend serializes `Decimal` as `str(Decimal)`, not a JSON number), `txn_time`/`category_id`/
  `category_name` are nullable, and `sync/status`'s `last_sync_*` fields are **absent entirely**
  (not `null`) until the first sync has run.
- Unit-testable against recorded fixtures/a local stub server, without a real backend running. ✅
  A `URLSessionProtocol` seam lets tests inject a `StubURLSession` returning canned JSON — no
  network, no real backend. 11 tests in `ios/Ledger/LedgerTests/APIClientTests.swift`, covering:
  list/single-object decoding (including `source_email` only appearing on the single-GET), that
  `PATCH`'s correction request omits unset fields entirely rather than sending `null` (the backend
  treats an omitted field as "leave unchanged"), all three `sync/status` response shapes, both
  distinct error-body shapes (`DELETE /categories/{id}`'s plain-string 404 vs. its nested-object
  409), an unreachable-host failure, and that a payee name with a space is percent-encoded exactly
  once (not double-encoded). All 11 pass via `xcodebuild test`.
- Errors (unreachable host, non-2xx response, decode failure) surface as a typed result the
  caller must handle explicitly — never a silently-swallowed failure (Constitution principle 21).
  ✅ `APIError` (`.unreachable`, `.httpError(status:detail:)`, `.categoryInUse(message:
  transactionCount:)`, `.decodingFailed`) — every `APIClient` function is `async throws`, nothing
  is swallowed.

**Depends on:** I1. **Size:** M.

### I3. Backend reachability & connection settings ✅
**As** the owner-operator, **I want** to tell Ledger where the backend lives and see plainly
whether it's reachable, **so that** the app never hangs pretending to be live when it isn't
(REQUIREMENTS.md MOB-5).

**Acceptance criteria:**
- A settings screen where the VM's Tailscale hostname/port is entered once and remembered locally
  (plain local storage — not sensitive enough to need Keychain, unlike a real credential). ✅
  `ViewState/ConnectionSettingsStore.swift` (`UserDefaults`-backed) +
  `Views/ConnectionSettingsView.swift`. No dedicated Settings tab exists in the confirmed 3-tab
  design, so it's reached via a gear button in the Ledger tab's toolbar — the same
  one-tap-deeper pattern Epic M uses for manual-add.
- A reachability check (calls `GET /sync/status` or `GET /health`) shown as a clear status row —
  a wrong host or an unreachable VM shows an explicit error, not an infinite spinner. ✅ Calls
  `GET /health` first, then `GET /sync/status` (a 404 there just means "no Gmail account
  connected yet," still reported as reachable, not an error). `APIClient.perform` now sets an
  explicit 8-second request timeout (down from `URLRequest`'s ~60s default) specifically so a
  wrong host fails fast into a visible "Unreachable" state instead of a long, spinner-like wait.
  `ConnectionSettingsStore` takes an injectable client factory (mirroring I2's `URLSessionProtocol`
  seam) so its reachability logic is unit-tested against a stub, not just eyeballed — 6 tests in
  `LedgerTests/ConnectionSettingsStoreTests.swift` (persistence round-trip, healthy+synced,
  healthy+no-Gmail-yet, unreachable, and "no host configured yet never touches the network").
- Assumes the Tailscale iOS app is already installed with **VPN On Demand set to "Always" for
  Wi-Fi and Cellular (ADR-0025)** — a one-time manual prerequisite performed by the owner, not
  automatable by Ledger (same category as the Gmail OAuth consent click, BACKLOG.md B1). Ledger
  itself needs no code to support this — it's a device setting, not an API or client behavior.

**Implementation note:** the backend has no TLS certificate (it's only ever reached over the
private tailnet), and its hostname is entered by the owner at runtime rather than known at build
time, so a scoped App Transport Security exception isn't possible — `Info.plist` sets
`NSAllowsArbitraryLoads`, documented in `project.yml` with the reasoning (personal app, free
Xcode signing only, never App-Store distributed, so ATS review doesn't apply).

**Verified:** `xcodebuild test` — 17/17 tests pass (11 from I2 + 6 new). Build succeeds and
installs/launches on the simulator with the gear button visible (screenshot-checked). **The owner
subsequently ran it live on their own iPhone** (per the Definition of Done's dashboard-story
standard) — entering the VM's real hostname correctly produced "Unreachable — the request timed
out," which is exactly the clear, non-hanging error state I3 asked for. That real attempt is what
surfaced a genuine infrastructure problem (see the note below and J1's infrastructure note) — the
VM itself turned out to be unreachable for reasons entirely outside Ledger's code. I3's own
behavior — reachability check, save-and-remember, explicit error state — is confirmed correct;
what's still open is the backend actually being reachable at a real address, tracked as
infrastructure work, not an I3 defect.

**Depends on:** I1. **Size:** S.

---

## Epic J — Ledger: Transaction List & Correction (mirrors F1–F3, F5)

**Status: Done (2026-07-19).** J1-J4 committed and merged to main via
[PR #9](https://github.com/Naveen8f23/Expense-Tracker/pull/9), together with Epic I. J5-J7
(this session) complete all seven stories — 52/52 iOS unit tests passing, each story additionally
verified live via the demo XCUITest harness against the real local backend (the developer's Mac,
per J1's infrastructure note — ADR-0026 is still unresolved).

### J1. Transaction list (Ledger tab) ✅
**As** the owner-operator, **I want** my transaction history on my phone in the same
searchable/filterable shape as the web dashboard, **so that** I can browse spending without
opening a laptop (SRCH-1).

**Acceptance criteria:**
- Calls `GET /transactions` with the same filters F1 exposes on the web (payee, category, date
  range, amount range, method, type, free-text), rendered as the chip-based filter bar from the
  confirmed design. ✅ `ViewState/TransactionListStore.swift` + `Views/LedgerListView.swift` +
  `Views/TransactionFilterSheet.swift`. All 7 filters are wired and functional (category picker,
  method/type segmented controls, date range, amount range, free-text search field). **Not yet
  the chip-based filter bar from the confirmed design** — plain functional controls for now, same
  placeholder-pending-mockup approach as I1's tab icons; J2 is explicitly where the debounced-
  search/removable-chip polish belongs, mirroring G1.
- Paginates via `limit`/`offset` as the list is scrolled. ✅ Via a "Load more" button (not
  scroll-position auto-trigger — simpler and more reliably testable); `TransactionListStore`
  tracks `hasMore` from the server's `total` vs. loaded count.
- Dismissed transactions excluded by default (already true server-side, E1) — no client-side
  re-filtering needed. ✅ No dismissed-filtering logic exists client-side at all.

**Verified:** 4 new unit tests (`LedgerTests/TransactionListStoreTests.swift`, 21/21 total passing)
covering no-connection, successful load + categories-fetched-once, pagination/`hasMore`, and a
server-error path. Also verified live against the real local backend (running on the developer's
Mac during this session while the VM's networking is blocked — see below): screenshot-confirmed
real transactions rendering correctly, including the "Manual" badge (H2) and debit/credit amount
coloring, both an error state (no connection configured) and a populated list.

**Infrastructure note (2026-07-19, unrelated to J1's own code):** the Ubuntu VM (ADR-0020) turned
out to have never actually joined Tailscale — REQUIREMENTS.md MOB-5 assumed it had, but it doesn't
appear anywhere in `dpkg`, has no `tailscaled` process, and isn't reachable at its supposed
Tailscale address even from the VM itself. Separately, `deploy/expense-tracker.service` was fixed
to bind `0.0.0.0` instead of `127.0.0.1` (needed regardless, since the old bind made the backend
unreachable from anywhere but itself) — both the repo file and the live VM unit were updated and
the service restarted. The VM is actually reached today through the owner's brother's NAS acting
as a Tailscale subnet router (a different setup than ADR-0002/0020 assumed), which currently only
allows SSH through its firewall to that subnet — the brother is opening ports 6000-6500 for this.
**Until that's confirmed open, Ledger development is proceeding against the backend running
directly on the developer's own Mac** — reachable both via its real Tailscale hostname
(`naveen-zoho-macbook`) and, for the Simulator, `http://localhost:8000` — not the VM. Full writeup
in **DECISIONS.md ADR-0026** (interim state, not yet resolved). Once the VM's ports are open: the
backend's production port likely needs to move into the newly-opened 6000-6500 range instead of
8000 (update `deploy/expense-tracker.service` + the live VM unit), REQUIREMENTS.md MOB-5 needs
revising to describe the actual subnet-router topology instead of the originally-assumed one, and
ADR-0026 itself should be updated to close out the interim state.

**Depends on:** I2. **Size:** M.

### J2. Search & filter chips ✅
**As** the owner-operator, **I want** filtering to feel fast, **so that** finding a transaction
on my phone is as quick as on the web (mirrors G1).

**Acceptance criteria:**
- Free-text and payee-contains inputs are debounced (~400ms) before triggering a request — doubly
  important over a Tailscale connection, which is slower than localhost. ✅
  `Views/LedgerListView.swift` — a cancel-and-reschedule `Task` (400ms sleep) fires on
  `onChange` of both the free-text search field and a new "Payee contains…" field.
  **Fixes a J1 gap:** J1's acceptance criteria listed `payee` among F1's filters, but the filter
  sheet built for J1 never actually exposed a payee input (only category/method/type/date/amount)
  — this story is where it was added, matching the web's own F1→G1 split (payee existed before
  G1; G1 just debounced it).
- Active filters render as removable chips; a "Clear all" resets everything. ✅ New
  `Views/FilterChip.swift`; a horizontally-scrolling chip row appears whenever any filter is
  active (search, payee, category, method, type, date range, amount range), each independently
  removable, plus a "Clear all" that resets everything (search text, payee text, and the sheet's
  filters) in one action.

**Verified:** live via the demo XCUITest harness (screenshots) — typing "Vendor" into the payee
field correctly narrowed the list to matching transactions after the debounce window; combining a
payee filter with a "Credit" type filter correctly produced "No transactions" (those entries are
debits); "Clear all" correctly reset both text fields and the sheet's filters and repopulated the
full list.

**Depends on:** J1. **Size:** S.

### J3. Transaction detail sheet ✅
**As** the owner-operator, **I want** to open a transaction and correct any field, **so that** I
can fix mistakes from my phone (COR-1).

**Acceptance criteria:**
- `GET`/`PATCH /transactions/{id}` — every E3-editable field has a control, presented as a sheet
  (not a full-screen push), matching the confirmed design. ✅ New
  `ViewState/TransactionDetailStore.swift` + `Views/TransactionDetailView.swift`. Every row in
  `LedgerListView` is now tappable (wrapped in a `Button`, trailing chevron affordance) and opens
  this sheet via `.sheet(item:)`. Amount, date, payee name, category, payment method, and
  debit/credit all have controls; no time field, matching H2's own web precedent.
- Category is assigned via a manual picker only — **no auto-suggested or pre-filled category**
  (REQUIREMENTS.md MOB-3, reconfirmed by the owner this session); the only durability mechanic is
  COR-2 (a category remembered per payee), identical to the web dashboard's own behavior. ✅
  **Known limitation, documented in code:** picking "Uncategorized" on an already-categorized
  transaction can't actually clear the category — the backend's PATCH endpoint has no way to
  explicitly null a field, only leave it unchanged (ground truth from I2). The picker silently
  no-ops in that case rather than corrupting data; the sheet dismisses immediately on save either
  way, so this isn't currently user-visible as a mismatch.
- A "Not a real expense" action calls `POST /transactions/{id}/dismiss` (COR-4). ✅ A destructive
  button + confirmation dialog, disabled if already dismissed.

**Verified:** 5 new unit tests (`LedgerTests/TransactionDetailStoreTests.swift`, 26/26 total
passing) covering load, a partial PATCH (confirms unset fields are omitted, not nulled), dismiss,
and a server-error path. **Also verified live** via the demo XCUITest harness against the real
local backend, with the actual database checked via `curl` before/after each action (not just
screenshots): editing a payee name persisted correctly (toggled "Local Vegetable Vendor" ↔
"Corner Vegetable Stall" across two separate runs — proof this isn't a fluke), and dismissing a
transaction ("SIRI SUPER MARKET") flipped its `dismissed` field to `true` on the server. One real
bug found and fixed this way: `TransactionDetailView`'s content view had a genuine blank-screen gap
— before `.task` starts, `transaction` is nil, `isLoading` is still false, and `errorMessage` is
nil, so none of the three view branches matched and nothing rendered. Fixed by making the loading
spinner the `else` catch-all instead of a separate `store.isLoading` condition.

**Follow-up fix (2026-07-19, spotted by the owner): transaction rows were missing the time
alongside the date** — the row only ever showed `txn_date`, never carrying over the web
dashboard's own Epic G follow-up (real `txn_time` when the template captured one, else an
approximate "~" time from the source email/manual-entry timestamp). New
`Networking/TransactionDisplayTime.swift` mirrors `frontend/src/utils/transactionTime.tsx`'s exact
fallback tiers. Building it surfaced a second real bug: the actual backend serializes
`email_received_at`/`created_at` with **no timezone suffix at all** (confirmed directly against
the running server — `"2026-07-19T10:40:39"`, not `"...+00:00"` as I2's original ground-truth
research had assumed for this specific field), which `ISO8601DateFormatter` silently fails to
parse — appending `"Z"` before parsing (matching the frontend's own handling of the same naive-UTC
values) fixed it. 5 new unit tests plus a live screenshot against real data (confirmed times like
`~9:33 AM` now render, not just bare dates).

**Depends on:** J1, I2. **Size:** M.

### J4. Source email viewer ✅
**As** the owner-operator, **I want** to see the original email a transaction came from, **so
that** I can verify the extraction from my phone (TRC-2), mirroring F3.

**Acceptance criteria:**
- Reachable as a disclosure from J3, showing the cached email content from `GET /transactions/{id}`.
  ✅ New `Views/SourceEmailView.swift`, reached via a "View source email" row in
  `TransactionDetailView` — shown only when `transaction.sourceEmail` is populated (real synced
  transactions); manually-added transactions (H2, `email_message_id == nil`) still show the
  existing "no source email" note instead, unchanged from J3.
- Rendered as plain, escaped text only — **never interpreted as live/rendered HTML** by any
  system text view or web view component. This is untrusted external content (a real bank email,
  ADR-0006); the same stored-XSS-shaped risk F3 already guards against on the web applies here. ✅
  **Simpler than the web's own version of this problem:** SwiftUI's `Text` never interprets its
  string as markup in the first place — there's no `dangerouslySetInnerHTML`-equivalent risk to
  avoid, as long as nothing reaches for `NSAttributedString(data:options:[.documentType: .html])`
  or a `WKWebView` (a code comment flags this explicitly so a future edit doesn't accidentally
  introduce one). Verified live via the demo XCUITest harness against a real synced transaction's
  cached email — screenshot confirms raw markup (`<!doctype html>`, `<meta>` tags, etc.) renders
  as literal visible text, not interpreted HTML.

**Depends on:** J3. **Size:** S.

### J5. Swipe actions (Edit / Dismiss) ✅
**As** the owner-operator, **I want** to act on a row without opening it, **so that** quick
triage is quick, matching the confirmed design's swipe gesture.

**Acceptance criteria:**
- Native `swipeActions` on each list row: Edit opens J3's sheet; Dismiss calls
  `POST /transactions/{id}/dismiss` directly. ✅ `Views/LedgerListView.swift` — Dismiss (red,
  destructive) is listed first so it sits at the trailing swipe edge (the full-swipe action,
  matching "quick triage is quick"); Edit (blue) sits next to it, opening J3's existing sheet. New
  `TransactionListStore.dismissTransaction(baseURL:id:)` calls the endpoint directly and removes
  the row from the local list on success (E1 already excludes dismissed rows server-side, so
  there's nothing to wait for a reload for); failures surface via a new `actionErrorMessage` +
  alert, distinct from the list's own load-error state.

**Verified:** 2 new unit tests (`LedgerTests/TransactionListStoreTests.swift`, 36/36 total passing)
covering the success path (row removed, total decremented) and a server-error path (row kept,
error surfaced). **Also verified live** via the demo XCUITest harness against the real local
backend: swiping revealed both actions, Edit opened the detail sheet, and Dismiss removed the row
immediately — confirmed via `curl` that the transaction's `dismissed` field flipped to `true`
server-side.

**Depends on:** J1, J3. **Size:** S.

### J6. Category management + inline "+ New category" ✅
**As** the owner-operator, **I want** to create and assign categories directly from a transaction,
**so that** categorizing stays a single action (mirrors F5/E6).

**Scope note (resolved via AskUserQuestion, 2026-07-19):** unlike the web dashboard (F5, which only
ever built inline "+ New category" creation), this story's acceptance criteria call for genuine
full CRUD — rename and delete-with-reassignment have no existing UI to mirror. The owner chose a
dedicated **"Manage categories" screen reached from a new gear-adjacent toolbar icon** (the same
one-tap-deeper pattern I3 established for Connection Settings) over deferring rename/delete to a
later story.

**Acceptance criteria:**
- Full CRUD via `GET`/`POST`/`PATCH`/`DELETE /categories`, including the reassign-on-delete flow
  (a delete without `reassign_to` on an in-use category surfaces E6's 409 + affected count, not a
  silent failure or an orphaned reference). ✅ New `ViewState/CategoryManagementStore.swift` +
  `Views/CategoryManagementView.swift`: create (inline text field + Add), rename (swipe → alert
  with a pre-filled text field), delete (swipe → either an immediate remove, or — if the backend
  409s — a `pendingReassignment` state driving a `ReassignmentSheet` listing every other category
  as a reassignment target; there is no "delete anyway" option, matching the backend's own
  contract).
- The category picker in J3 supports "+ New category…" inline, creating then assigning in one
  flow. ✅ `TransactionDetailView` — a sentinel picker option reveals an alert text field; the
  created category is appended to a local `newlyCreatedCategories` array and immediately selected,
  so the picker shows it as the current value without a second trip through the menu (verified
  live, see below).

**Two real bugs found and fixed via live UI verification (not by reasoning about the code, per the
project's Definition of Done):**
1. **Rename silently no-op'd.** The rename alert's `isPresented` binding was derived from the same
   optional (`categoryBeingRenamed != nil`) the Save action's async body read — tapping Save
   dismisses the alert, which (via that binding) nil'd the category out *before* the `async`
   `performRename()` task actually ran, so it read `nil` and returned early. Fixed by decoupling
   presentation (`showingRenameAlert: Bool`) from data (`categoryBeingRenamed: Category?`) — the
   same class of bug, and the same fix shape, applies to any SwiftUI alert/sheet whose dismissal
   and its own button action both mutate the same piece of state.
2. **The exact same race in the reassignment sheet.** Tapping a reassignment target called
   `onReassign` (unawaited, inside a `Task`) then `dismiss()` immediately — dismissal cleared
   `store.pendingReassignment` before the queued task read it. Fixed by awaiting the reassign call
   before dismissing, so the store's state stays valid for the whole operation.

**Also surfaced (real, now fixed):** dismissing "Manage Categories" only refreshed the category
*dropdown* (`store.refreshCategories`), not the transaction list itself — a transaction moved by a
reassign-and-delete kept showing its old (now-deleted) category name until the next manual
refresh. Fixed by also calling `reload()` in the sheet's `onDismiss`.

**Verified:** 9 new `CategoryManagementStoreTests` + 2 new `TransactionDetailStoreTests`
(`createCategory`), 45/45 total passing. **Also verified live** via two demo XCUITest walkthroughs
against the real local backend: create → rename → assign to a real transaction → delete-while-in-
use → reassignment sheet → confirm → transaction correctly shows the new category, deleted
category confirmed gone on a fresh load (`testJ6CategoryManagement`); and the inline "+ New
category…" flow creating and assigning a category in one trip without leaving J3's sheet
(`testJ6InlineNewCategoryFromDetailPicker`).

**Depends on:** J3. **Size:** S.

### J7. Sync-health indicator ✅
**As** the owner-operator, **I want** to see at a glance whether sync is healthy, **so that** I
never wonder if Ledger (or the VM) is silently broken (ING-8), mirroring the confirmed design's
nav-bar dot.

**Acceptance criteria:**
- A small colored dot (or equivalent) in the Ledger tab, calling `GET /sync/status`; tapping it
  shows the same scanned/matched/skipped/failed counts the endpoint already returns. ✅ New
  `ViewState/SyncHealthStore.swift` (framework-agnostic — classifies `SyncStatus` into a plain
  `Health` enum: `notConnected` / `pendingFirstSync` / `healthy` / `issues`, no SwiftUI import,
  matching the other stores) + `Views/SyncHealthView.swift`. A small `Circle` toolbar button in
  `LedgerListView` maps `Health` to a color (gray/yellow/green/red) and opens the detail sheet on
  tap.
- Pull-to-refresh re-fetches the current transaction list/state. **Explicitly out of scope:**
  there is no endpoint to trigger a new Gmail sync on demand — the VM's `SyncScheduler`
  (ADR-0019) already runs independently every 5 seconds regardless of whether Ledger is open, so
  pull-to-refresh is for reassurance and immediacy, not for making the VM check Gmail sooner. ✅
  `.refreshable` (already present from J1) and the initial `.task` both now also call
  `syncHealthStore.load`; no new sync-trigger endpoint was added or is called.

**Verified:** 7 new unit tests (`LedgerTests/SyncHealthStoreTests.swift`, 52/52 total passing)
covering all five health classifications (no connection configured, no Gmail connected yet,
connected-but-unsynced, healthy, issues via both a failed-count and a `last_error`) plus an
unreachable-host path. **Also verified live** via the demo XCUITest harness against the real local
backend: the dot rendered green (`"Sync status: healthy"`, matching the real `GET /sync/status`
response), and tapping it showed the actual scanned/matched/skipped/failed counts and last-sync
timestamp.

**Depends on:** J1. **Size:** S.

---

## Epic K — Ledger: Needs-Review Queue (mirrors F4)

**Status: Done (2026-07-19).** All four stories complete — 58/58 iOS unit tests passing (6 new).
K1, K2, and K4 verified live against the real local backend; K3 verified by unit test and code
review (it reuses J3's exact, already-live-verified sheet) since no low-confidence transaction
happened to exist in the real queue this session to drive live.

### K1. Review tab ✅
**As** the owner-operator, **I want** a dedicated screen listing everything needing my attention,
**so that** nothing gets missed from my phone (EXT-5, EXT-6).

**Acceptance criteria:**
- Calls `GET /needs-review`; displays both halves it already returns — unmatched emails and
  low-confidence transactions — as separate sections with reason chips, matching the confirmed
  design. ✅ New `ViewState/NeedsReviewStore.swift` + `Views/ReviewView.swift` (replacing I1's
  placeholder). Unmatched emails show a reason chip — "Unrecognized" if `classifiedPatternId` is
  nil, "Extraction failed" if it classified but couldn't extract (mirrors C7's two distinct
  needs-review causes) — and are reachable via `NavigationLink` to J4's existing `SourceEmailView`
  (read-only, same safe rendering). Low-confidence transactions show a "Low confidence" chip and
  reuse `TransactionRowView`'s look.

**Verified:** 6 new unit tests (`LedgerTests/NeedsReviewStoreTests.swift`, 58/58 total passing)
covering no-connection, both-halves-populate + categories-fetched-once, a server-error path, and
the ignore action's success/failure paths. **Also verified live** via the demo XCUITest harness
against the real local backend: the one real unmatched email currently in the queue (a credit card
bill payment via net banking — the known 5th HDFC shape from Epic C, correctly never classified)
rendered with its "Unrecognized" chip, and tapping it opened the real cached source email.

**Depends on:** I2. **Size:** M.

### K2. Swipe-to-ignore for unmatched emails ✅
**As** the owner-operator, **I want** to clear an unmatched email from the queue, **so that** I'm
not stuck reviewing something I've already decided isn't a real transaction (mirrors F4's addendum).

**Acceptance criteria:**
- Calls `POST /needs-review/emails/{id}/ignore` via a swipe action. ✅
  `NeedsReviewStore.ignoreEmail(baseURL:id:)`, wired to a destructive `swipeActions` button on each
  unmatched-email row; removes the row locally on success (mirrors J5's dismiss pattern) rather
  than waiting for a reload.

**Verified:** live via the demo XCUITest harness against the real local backend — swiping the real
unmatched email revealed "Ignore," tapping it removed the row immediately, and its
`email_messages.status` was confirmed flipped to `IGNORED` via direct sqlite inspection. Reverted
back to `NEEDS_REVIEW` afterward via the same route, since this was verification on the developer's
own real inbox data, not an action the owner asked for.

**Depends on:** K1. **Size:** S.

### K3. Review a low-confidence transaction ✅
**As** the owner-operator, **I want** tapping a low-confidence item to open the same correction
flow as any other transaction, **so that** there's only one correction UI to learn.

**Acceptance criteria:**
- Tapping a low-confidence item opens J3's detail sheet, not a separate review-specific form. ✅
  `ReviewView`'s low-confidence rows are wrapped in the exact same `.sheet(item:)` pattern
  `LedgerListView` uses, presenting the unmodified `TransactionDetailView` — no separate
  review-specific form exists.

**Verified:** by code (the sheet presentation is identical to J1/J3's own, already live-verified)
and by the fact that `NeedsReviewStore` supplies the same `categories`/`onChanged` shape J3 expects.
**Not separately live-verified this session** — the real backend's queue had zero low-confidence
transactions at the time (the AI-fallback path that produces them is rare by design, EXT-4/EXT-5),
so there was nothing real to tap through. Revisit with a live drive-through once a real one exists.

**Depends on:** K1, J3. **Size:** S.

### K4. Review tab badge count ✅
**As** the owner-operator, **I want** the Review tab to wear its queue size openly, **so that** I
always know before tapping in whether anything's waiting (matches the confirmed design).

**Acceptance criteria:**
- The tab badge reflects the queue size as of the last time it was fetched (app foreground/tab
  switch) — **not** a live/real-time count while another tab is open, since no push mechanism
  exists to update it silently in the background (ADR-0024). ✅ `NeedsReviewStore` is now owned by
  `RootTabView` (lifted up from `ReviewView` so the tab item itself can read its count) and
  refetched on launch (`.task`), on switching to the Review tab (`.onChange(of: selectedTab)`), and
  on the app returning to the foreground (`.onChange(of: scenePhase)`) — no polling, no push.
  `.badge(needsReviewStore.totalCount)` renders nothing when the count is 0.

**Verified:** live via the demo XCUITest harness against the real local backend — the tab bar
showed a badge of "1" on launch, matching the one real unmatched email in the queue at the time.

**Depends on:** K1. **Size:** S.

---

## Epic L — Ledger: Analytics (mirrors G2–G4)

**Status: Done (2026-07-19).** All three stories complete — 76/76 iOS unit tests passing (9 new).
Two real bugs were found and fixed via live verification, both the same underlying lesson as
J6's: don't let two pieces of state (or two independent triggers) that must stay in sync drift
apart. See L1 and L3 below for what each one actually was.

### L1. Analytics tab — monthly summary ✅
**As** the owner-operator, **I want** the monthly total on my phone, **so that** I can see my
spending at a glance without opening a laptop (ANL-1, ANL-4).

**Acceptance criteria:**
- Calls `GET /analytics/monthly`; month switcher (Previous/Next) plus spent/received/net summary
  cards, matching the confirmed design and ADR-0021's sign convention. ✅ New
  `ViewState/AnalyticsStore.swift` + `Views/AnalyticsView.swift`. `month` (`"yyyy-MM"`) is tracked
  client-side (`DateFormatter` pinned to `en_US_POSIX` — a plain, unpinned formatter can silently
  mis-parse a fixed-format string depending on device locale/calendar) and driven entirely by
  `.task(id: store.month)`, the single trigger for loading.

**Real bug found and fixed via live verification:** the month switcher's label and figures stayed
completely frozen after tapping Previous/Next, even though `AnalyticsStore.month` genuinely
changed (confirmed via direct instrumentation — same object instance, same thread, correct new
value). Two compounding causes, found by process of elimination:
1. `goToPreviousMonth`/`goToNextMonth` were originally `async` functions that changed `month` *and
   also* called `load()` themselves, racing against `.task`'s own (undocumented but real) habit of
   restarting whenever the `List` content it's attached to gets diffed for unrelated reasons. Fixed
   by making the month-shift functions pure and synchronous, and making `.task(id: store.month)`
   the *only* trigger for loading — one trigger, no race.
2. Even after that fix, the label still didn't update: the month switcher lived inside a `List`
   `Section`, and a `Section`'s direct (non-`ForEach`) content didn't reliably re-render on
   `@Published` changes from a sibling code path. Fixed by moving the month switcher entirely
   outside the `List` into a plain `VStack` above it — the same List/VStack split
   `LedgerListView` already uses successfully for its own filter controls.

**Verified:** 5 new unit tests (`LedgerTests/AnalyticsStoreTests.swift`) covering no-connection,
populate, server-error, and both month-shift directions (including a year rollover). **Also
verified live** against the real local backend: tapping Previous/Next now genuinely moves the
label and re-fetches real data for the new month (confirmed a real, populated July 2026 vs. an
empty June 2026).

**Depends on:** I2. **Size:** M.

### L2. Category breakdown ✅
**As** the owner-operator, **I want** to see spend by category for the selected month, **so
that** I understand where money goes, from my phone (ANL-2).

**Acceptance criteria:**
- Calls `GET /analytics/by-category`; ranked bars, debit-only, "Uncategorized" bucket included —
  same conventions as the web dashboard (ADR-0021), no reinterpretation on the client. ✅ Shares
  `AnalyticsStore`/`AnalyticsView` with L1 (same month cursor, ADR-0021); renders as a plain ranked
  list below the summary cards, reusing whatever order/bucketing the backend already returns.

**Verified:** covered by the same `AnalyticsStoreTests` as L1 (populate test asserts both halves
decode correctly together) plus the same live verification — real category breakdown rendered
correctly for July 2026 and correctly emptied for June 2026.

**Depends on:** L1. **Size:** S.

### L3. Payee history ✅
**As** the owner-operator, **I want** to tap any payee name and see their running history and
total, **so that** I can spot patterns per merchant/person (ANL-3).

**Acceptance criteria:**
- Tapping a payee name anywhere it appears (list rows, review queue) calls
  `GET /analytics/by-payee/{payee}` and opens a panel with the total and a clickable transaction
  list, matching the confirmed design's payee history view. ✅ New
  `ViewState/PayeeHistoryStore.swift` + `Views/PayeeHistoryView.swift` + shared `PayeeSelection`
  (an `Identifiable` wrapper). `TransactionRowView` gained an optional `onPayeeTapped` closure —
  when set, the payee name renders as its own `Button`, separate from the rest of the row (which
  opens the transaction detail sheet via `.onTapGesture` on the row container, since a `Button`
  can no longer wrap the whole row once another `Button` needs to live inside it). Wired into both
  `LedgerListView`'s rows and `ReviewView`'s low-confidence rows.

**Real bug found and fixed via live verification:** tapping a payee correctly opened the payee
history panel, but it always 404'd — even for a payee confirmed (via direct `curl`) to have real
data. Traced with file-based instrumentation (print/console output doesn't reliably surface from
the app process through `xcodebuild test`) to the actual value reaching the network call: an
**empty string**, not the tapped payee's name. Root cause: the panel was driven by two separate
`@State` variables — `showingPayeeHistory: Bool` and `payeeNameForHistory: String` — set together
in one closure, then read separately by `.sheet(isPresented:)` and its content closure. This is
the identical shape of bug J6 already found once (an alert's dismiss-vs-data race) — two pieces of
state that must stay consistent, read at different times. Fixed by replacing both with one
`PayeeSelection?` value driving `.sheet(item:)`, mirroring the already-reliable
`selectedTransaction: Transaction?` pattern used everywhere else in this codebase. **General
lesson, worth remembering for any future sheet/alert:** a single `Identifiable` optional is not
just tidier than a `Bool` + a data variable — it's the only shape that can't go internally
inconsistent with itself.

**Verified:** 4 new unit tests (`LedgerTests/PayeeHistoryStoreTests.swift`) covering no-connection,
populate + pagination + categories-fetched-once, load-more, and a server-error path. **Also
verified live** against the real local backend: tapping a real "NAVEEN V" transaction's payee name
correctly opened its history panel showing the real total and transaction count from a direct
`curl` cross-check.

**Depends on:** L1, J1. **Size:** S.

---

## Epic M — Ledger: Manual Add & In-App Notifications

**Status: Not started.**

### M1. Add Transaction sheet
**As** the owner-operator, **I want** to add a transaction with no corresponding email from my
phone, **so that** the rare cash purchase isn't lost (COR-5, REQUIREMENTS.md MOB-6), mirroring H2.

**Acceptance criteria:**
- Reached only via a small "+" in the Ledger tab's toolbar — **never its own tab** — keeping it a
  deliberate exception, not a primary workflow, matching the confirmed design's stated reasoning.
- Calls `POST /transactions`; category assigned manually via J6's picker, no auto-suggestion
  (MOB-3); no time field, matching J3's own shape (H2's precedent).

**Depends on:** J3, J6. **Size:** S.

### M2. In-app new-transaction notifications (ADR-0024)
**As** the owner-operator, **I want** to be told when a new transaction arrives while I'm using
Ledger, **so that** categorizing it feels almost as immediate as a push notification, within the
scope actually agreed (REQUIREMENTS.md MOB-4).

**Acceptance criteria:**
- While the app is foregrounded, or backgrounded within the short window iOS keeps a recently-
  backgrounded app suspended-but-alive, poll `GET /transactions/recent?since_id=` on the same
  ~5-second cadence as the web dashboard's H4 hook.
- A new transaction fires a local `UNNotificationRequest` (banner + badge); tapping it opens
  straight to that transaction's J3 detail sheet, via the notification's `userInfo` carrying the
  transaction id — not just a generic app-open.
- **Explicit non-goal, stated plainly and not to be silently "fixed" later without a fresh
  decision:** nothing arrives once Ledger has been fully backgrounded for more than a few minutes,
  or force-quit. This is ADR-0024's accepted scope, chosen after both a paid (APNs) and a free
  third-party-relay path were presented and declined.

**Depends on:** J1, J3. **Size:** M.

### M3. Background App Refresh supplement (best-effort)
**As** the owner-operator, **I want** Ledger to take advantage of whatever background time iOS
is willing to grant it, **so that** the closed-app gap in M2 is at least partially, honestly
narrowed rather than left completely dark.

**Acceptance criteria:**
- Registers a `BGAppRefreshTask`; when iOS grants it a run, checks `GET /transactions/recent`
  once and fires a local notification if something new turned up.
- **Explicitly documented as best-effort, not reliable** — iOS decides if/when this runs (based on
  the owner's own usage patterns, battery state, etc.), often not more than a few times a day or
  less. Must never be presented to the owner as a dependable channel, in the UI or in any future
  doc referencing it (Constitution principle 21).

**Depends on:** M2. **Size:** S.

---
_Revision history: track major changes here in [CHANGELOG.md](CHANGELOG.md). Architectural
implications of any story (new module boundary, new dependency) belong in
[DECISIONS.md](DECISIONS.md), not here._
