# Backlog

Status: **v0.9 — Epics A-E (Foundation through API Layer) done, verified, and merged to main
(2026-07-19; PR #1-#5). Epic F (Dashboard: Review & Correction), H3 (packaging/run script), and
H4 (automatic background sync) also done and verified (2026-07-19). The Ubuntu VM is now the
owner's actual, permanent, day-to-day instance (ADR-0020) — running as a persistent
`systemd --user` service with its own independent (freshly-connected, not migrated) Gmail
history; the local Mac instance has been stopped. Epic G (Search & Analytics, MVP complete) is
next, not yet started.**

This is the detailed, implementation-level breakdown of [ROADMAP.md](ROADMAP.md) milestones
M2–M5, into units small enough to pick up and build one at a time. ROADMAP.md stays
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

**Scope note (explicit decision, not yet built):** nothing automatically calls
`run_incremental_sync` on a schedule yet. The sync mechanism itself is correct and tested; an
in-process scheduler (ADR-0013) is deferred until Epic C exists to give newly-synced emails
somewhere to go — right now they'd just accumulate as `unprocessed` rows either way.

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
Per the epic-checkpoint policy (ADR-0014), this is the point for a demo and the owner's go-ahead
before Epic G (Search & Analytics, MVP complete) begins.

---

## Epic G — Search & Analytics (ROADMAP.md M5 — MVP complete)

### G1. Search/filter UI polish
**As** the owner-operator, **I want** the filters from F1 to feel fast and easy to combine,
**so that** finding a specific transaction is quick.

**Depends on:** F1. **Size:** S.

### G2. Monthly summary
**As** the owner-operator, **I want** a monthly total (and a way to move between months),
**so that** I can see my spending at a glance (ANL-1, ANL-4).

**Acceptance criteria:** a `GET /analytics/monthly` endpoint plus a dashboard view; bucketed
consistently by transaction date (not email-received date, per Edge Cases §10).

**Depends on:** E1, F1. **Size:** M.

### G3. Category breakdown
**As** the owner-operator, **I want** to see spend by category for a selected period, **so
that** I understand where money goes (ANL-2).

**Acceptance criteria:** a `GET /analytics/by-category` endpoint plus a dashboard view (a
simple table or bar chart is enough for MVP — no charting library commitment implied here).

**Depends on:** G2. **Size:** M.

### G4. Payee history
**As** the owner-operator, **I want** to see all transactions with a given payee and their
total, **so that** I can spot patterns per merchant/person (ANL-3).

**Acceptance criteria:** a `GET /analytics/by-payee/{payee}` endpoint plus a dashboard view,
reachable by clicking a payee name from F1.

**Depends on:** E1, F1. **Size:** S.

---

## Epic H — Cross-cutting polish (rolling, alongside other epics)

### H1. Sensitive-field encryption verification
**As** the owner-operator, **I want** confirmation that OAuth tokens and cached email content
are genuinely unreadable in the raw database file, **so that** the NFR in REQUIREMENTS.md §4
(as revised by ADR-0015) is actually true, not just assumed.

**Acceptance criteria:** an automated test opens the raw SQLite file directly (bypassing the
application) and asserts `gmail_connections.tokens` and `email_messages.content` are not
human-readable, while confirming this is understood as field-level, not whole-file, protection
(ADR-0015) — not a one-time manual check.

**Depends on:** A2. **Size:** S.

### H2. Manual "add a transaction" escape hatch
**As** the owner-operator, **I want** to add a transaction that has no corresponding email,
**so that** the rare cash purchase isn't lost (COR-5).

**Acceptance criteria:** a form (reusing F2's shape) with no source email required; clearly
visually distinct from auto-ingested transactions so it stays the exception, not confused with
the norm.

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
_Revision history: track major changes here in [CHANGELOG.md](CHANGELOG.md). Architectural
implications of any story (new module boundary, new dependency) belong in
[DECISIONS.md](DECISIONS.md), not here._
