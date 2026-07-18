# Backlog

Status: **populated (v0.1) — MVP backlog broken into independent, SCRUM-style stories.**

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

## Definition of Done (confirmed 2026-07-18, ADR-0014)

A story is not done just because code was written for it. It's done when:

1. **Its acceptance criteria are all met**, checked explicitly against the story text — not
   assumed from "the general approach works."
2. **Automated tests exist and pass**, run for real (not just written) — this applies fully to
   Epics A–E (backend/logic): schema, classifiers, extractors, dedup, API endpoints. These are
   deterministic and get tested directly against the real sample emails in REQUIREMENTS.md
   Appendix A plus the known edge cases.
3. **For dashboard stories (Epics F–G):** the actual running UI is driven directly (browser
   automation) through the flow the story describes — click search, edit a transaction, view
   the source email, etc. — and the result is observed, not just asserted.
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

### B1. Gmail OAuth connect flow
**As** the owner-operator, **I want** to grant read-only Gmail access through Google's consent
screen from within the app, **so that** the system can start reading my transaction emails.

**Acceptance criteria:**
- A "Connect Gmail" action completes the OAuth flow and stores the resulting tokens encrypted
  in `gmail_connections` (ING-1, ING-2).
- Only read-only scope is requested — no send/delete/modify permission.
- Token refresh works without user intervention; if refresh fails (e.g. access revoked), this
  is surfaced, not silently swallowed (ties into B5).

**Depends on:** A2. **Size:** M.

### B2. SenderRule configuration + seed data
**As** the developer, **I want** the three confirmed HDFC `SenderRule`s (UPI debit, UPI credit,
credit card debit — REQUIREMENTS.md Appendix A) loaded into the database, **so that**
ingestion and classification have something real to match against.

**Acceptance criteria:**
- `sender_rules` table has one row per confirmed template: sender address
  (`alerts@hdfcbank.bank.in`), a content-pattern identifier, and the resulting transaction
  type.
- Adding a fourth rule later (credit card credit, or a second bank) requires only a new row,
  not a code change (validates the extensibility goal in REQUIREMENTS.md §9).

**Depends on:** A2. **Size:** S.

### B3. One-time backfill sync
**As** the owner-operator, **I want** the first sync to pull matching emails from the start of
the current calendar month, **so that** my tracker has a clean starting point (ADR-0011).

**Acceptance criteria:**
- On first connect, the system fetches all Gmail messages from `sender_rules` senders dated
  from the 1st of the current month to now.
- Each matched raw email is stored as an `email_messages` row with status `unprocessed`
  (classification/extraction happens in Epic C, not here).
- No transaction records are created yet — this story only proves ingestion, not extraction.

**Depends on:** B1, B2. **Size:** M.

### B4. Incremental sync via Gmail History API
**As** the owner-operator, **I want** subsequent syncs to only fetch what's new since the last
check, **so that** the app stays fast and doesn't reprocess my whole inbox every time (ING-4,
ING-5, ING-6).

**Acceptance criteria:**
- `sync_state` stores the last processed `historyId` per connection.
- A sync run only fetches changes since that checkpoint.
- Re-running a sync with no new mail creates zero new `email_messages` rows (idempotent,
  ties to DUP-1 in Epic D).
- If the checkpoint is too old for Gmail's History API retention window, the system detects
  this and falls back to a bounded re-scan rather than failing silently.

**Depends on:** B3. **Size:** M.

### B5. Sync health logging & status
**As** the owner-operator, **I want** to see when the last sync ran and whether anything went
wrong, **so that** I never have to wonder if the system is silently broken (ING-8).

**Acceptance criteria:**
- Each sync run logs: start/end time, messages scanned, matched, skipped, failed.
- A simple status is queryable (even just a log file or a DB row at this stage — a dedicated
  API endpoint for this is Epic E, story E7).
- A failed OAuth refresh (from B1) shows up here, not just in a stack trace.

**Depends on:** B1, B3, B4. **Size:** S.

---

## Epic C — Classification & Extraction (ROADMAP.md M3)

### C1. Classifier: UPI Debit
**As** the developer, **I want** a function that identifies an email as "UPI Debit" using the
confirmed content markers, **so that** downstream extraction knows which template to apply.

**Acceptance criteria:**
- Given the real UPI Debit sample (REQUIREMENTS.md Appendix A.1), correctly classifies as UPI
  Debit.
- Given the UPI Credit or Credit Card Debit samples, does **not** misclassify as UPI Debit.
- Given an unrelated email from the same sender, returns "no match" rather than a false
  positive.

**Depends on:** A2, B2. **Size:** S.

### C2. Classifier: UPI Credit
Same shape as C1, for the UPI Credit template (Appendix A.2). **Depends on:** A2, B2. **Size:** S.

### C3. Classifier: Credit Card Debit
Same shape as C1, for the Credit Card Debit template (Appendix A.3). **Depends on:** A2, B2.
**Size:** S.

### C4. Extractor: UPI Debit
**As** the developer, **I want** a parser that turns a classified UPI Debit email into
structured fields, **so that** it can become a `Transaction` row.

**Acceptance criteria:**
- From Appendix A.1's sample, correctly extracts: amount 120.00, type debit, method UPI,
  instrument "account ending 4958", payee VPA + display name, date, reference number.
- Handles the case where the parenthetical payee display name is absent (Edge Cases §10) —
  falls back to the VPA alone rather than failing.
- Output confidence is high (EXT-5) since this is a known, matched template.

**Depends on:** C1, A2. **Size:** M.

### C5. Extractor: UPI Credit
Same shape as C4, for the UPI Credit template (Appendix A.2) — including the "Sender" name +
VPA fields and the lettered "Transaction Details" layout. **Depends on:** C2, A2. **Size:** M.

### C6. Extractor: Credit Card Debit
Same shape as C4, for the Credit Card Debit template (Appendix A.3).

**Additional acceptance criteria specific to this story:**
- Correctly parses the `18 Jul, 2026 at 18:56:45` date/time format (distinct from the UPI
  templates' `DD-MM-YY`).
- Handles the **absence** of a reference number (confirmed gap in this template) without
  erroring — the field is stored as null, not a crash or a fabricated value.
- Handles the `Rs. 554.00` (space after `Rs.`) vs. `Rs.120.00` (no space) formatting difference
  between templates.

**Depends on:** C3, A2. **Size:** M.

### C7. Needs-review queue mechanics
**As** the owner-operator, **I want** any email that doesn't classify or extract cleanly to be
flagged for my review instead of silently dropped or guessed at, **so that** nothing important
goes missing (EXT-5, EXT-6).

**Acceptance criteria:**
- An `email_messages` row that matches no known `SenderRule` content pattern is marked
  `needs-review`, not `ignored` or deleted, if it came from a configured sender address.
- An email that classifies but fails extraction (e.g. unexpected internal structure) is also
  marked `needs-review`, with the classification result preserved for context.
- A queryable list of needs-review items exists (surfaced properly in Epic E/F).

**Depends on:** C1–C6. **Size:** M.

### C8. AI fallback interface (stub)
**As** the developer, **I want** a defined `AIFallbackClient` interface with a no-op/stub
implementation, **so that** the extraction module has a clean seam for a real AI fallback
later without being blocked on choosing a provider now (Constitution principle 10).

**Acceptance criteria:**
- Interface is defined (input: raw email content + sender; output: best-effort structured
  fields + confidence, or "unable to extract").
- Stub implementation always returns "unable to extract," which routes the email to the
  needs-review queue (C7) — this proves the seam works without committing to a provider.
- Swapping in a real implementation later requires no changes outside the Infrastructure layer.

**Depends on:** C7. **Size:** S.

---

## Epic D — Deduplication (ROADMAP.md M3)

### D1. Message-ID based duplicate detection
**As** the owner-operator, **I want** the same Gmail message never to become two transactions,
**so that** re-syncs or retries don't inflate my history (DUP-1).

**Acceptance criteria:**
- Re-running ingestion (B3/B4) against an already-processed message ID is a no-op — zero new
  `transactions` rows.
- Covered by an automated test that ingests the same sample email twice.

**Depends on:** C4–C6. **Size:** S.

### D2. Reference-number / timestamp fallback disambiguation
**As** the owner-operator, **I want** two genuinely separate transactions with the same
amount/payee/day to both be recorded, **not** merged, **so that** real spending isn't lost
(DUP-2).

**Acceptance criteria:**
- Two UPI transactions with the same amount, payee, and day but different reference numbers
  both create separate `transactions` rows.
- For the Credit Card Debit template (no reference number, per C6), two same-day/same-
  amount/same-payee transactions are disambiguated by full timestamp instead, and still both
  recorded as separate rows if their timestamps differ.

**Depends on:** D1. **Size:** M.

---

## Epic E — API Layer (ROADMAP.md M4 foundation)

### E1. List/search transactions endpoint
**As** the dashboard, **I want** an endpoint to list transactions with filters, **so that** the
UI never queries the database directly (SRCH-1).

**Acceptance criteria:**
- `GET /transactions` supports filtering by payee, category, date range, amount range, payment
  method, and type, plus free-text.
- Paginated; performs well against a few thousand rows (SRCH-2 — no hard number required yet,
  just "not obviously slow").

**Depends on:** A2, C4–C6, D1–D2. **Size:** M.

### E2. Get single transaction (with source email) endpoint
**As** the dashboard, **I want** to fetch one transaction plus its linked source email content,
**so that** the user can verify extraction against the original (TRC-1, TRC-2).

**Acceptance criteria:**
- `GET /transactions/{id}` returns the transaction fields and the cached email content
  (ADR-0012) it was derived from.

**Depends on:** E1. **Size:** S.

### E3. Edit/correct transaction endpoint
**As** the dashboard, **I want** an endpoint to update a transaction's fields, **so that** the
user can fix extraction mistakes (COR-1, COR-3).

**Acceptance criteria:**
- `PATCH /transactions/{id}` accepts amount, date, payee, category, payment method, type.
- Writes an entry to `correction_log` capturing the before/after values.
- Assigning a category to a payee is remembered so future transactions from that payee default
  to it (COR-2) — this is the categorization module's only real logic for MVP.

**Depends on:** E1, E2. **Size:** M.

### E4. Mark "not a real expense" endpoint
**As** the dashboard, **I want** to hide a misclassified transaction from analytics without
deleting its audit trail, **so that** my summaries stay accurate (COR-4).

**Acceptance criteria:**
- `POST /transactions/{id}/dismiss` (or similar) excludes it from search/analytics by default
  but keeps the row and its source email intact.

**Depends on:** E1. **Size:** S.

### E5. Needs-review queue endpoint
**As** the dashboard, **I want** an endpoint listing everything in the needs-review state,
**so that** the review UI (Epic F) has something to show (EXT-5, EXT-6, C7).

**Acceptance criteria:**
- `GET /needs-review` returns all `email_messages`/`transactions` currently flagged, with
  enough context (raw content, attempted classification) to review without leaving the app.

**Depends on:** C7, E1. **Size:** S.

### E6. Category CRUD endpoints
**As** the dashboard, **I want** endpoints to list, create, rename, and delete categories,
**so that** category assignment (EXT-2) is fully user-driven.

**Acceptance criteria:**
- Full CRUD on `categories`; no fixed system list is seeded (per REQUIREMENTS.md §5).
- Deleting a category in use prompts reassignment rather than leaving orphaned references.

**Depends on:** A2. **Size:** S.

### E7. Sync health status endpoint
**As** the dashboard, **I want** an endpoint exposing the last sync's health (B5), **so that**
the UI can show it without reading log files directly.

**Acceptance criteria:**
- `GET /sync/status` returns last sync time, counts (scanned/matched/skipped/failed), and any
  current error state.

**Depends on:** B5, A2. **Size:** S.

---

## Epic F — Dashboard: Review & Correction (ROADMAP.md M4)

### F1. Transaction list/table view
**As** the owner-operator, **I want** to see my transactions in a searchable/filterable table,
**so that** I can browse my spending (SRCH-1).

**Acceptance criteria:** filters from E1 are all exposed in the UI; table is usable with a few
hundred rows without noticeable lag.

**Depends on:** E1, A3. **Size:** M.

### F2. Transaction detail + correction form
**As** the owner-operator, **I want** to open a transaction and edit any field, **so that** I
can fix mistakes (COR-1).

**Acceptance criteria:** every editable field from E3 has a form control; saving calls E3 and
reflects immediately in F1's table.

**Depends on:** E2, E3, F1. **Size:** M.

### F3. Source email viewer
**As** the owner-operator, **I want** to see the original email a transaction came from,
**so that** I can verify the extraction (TRC-2).

**Acceptance criteria:** accessible from F2; shows the cached email content from E2.

**Depends on:** E2, F2. **Size:** S.

### F4. Needs-review queue view
**As** the owner-operator, **I want** a dedicated screen listing everything needing my
attention, **so that** nothing gets missed (EXT-5, EXT-6).

**Acceptance criteria:** lists items from E5; each item can be corrected (reuses F2) or
dismissed (reuses E4 pattern).

**Depends on:** E5, F2. **Size:** M.

### F5. Category creation/assignment UI
**As** the owner-operator, **I want** to create and assign categories directly from a
transaction, **so that** categorizing is a single smooth action, not a side trip.

**Acceptance criteria:** category picker on F2 supports "create new" inline; calls E6 and E3
together.

**Depends on:** E6, F2. **Size:** S.

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

### H3. Packaging/run script
**As** the owner-operator, **I want** a clean, documented way to start the whole system,
**so that** running this day-to-day doesn't require remembering developer setup steps.

**Acceptance criteria:** builds on A4; produces something closer to "double-click to start" or
a single documented command, once the frontend is built for real use (not just `npm run dev`).

**Depends on:** A4, and practically, most of the rest of the backlog. **Size:** M.

---
_Revision history: track major changes here in [CHANGELOG.md](CHANGELOG.md). Architectural
implications of any story (new module boundary, new dependency) belong in
[DECISIONS.md](DECISIONS.md), not here._
