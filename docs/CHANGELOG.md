# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once
versioned releases begin.

## [Unreleased]

### Added (code)
- **H3 + ADR-0020: the Ubuntu VM becomes the real, permanent, day-to-day instance (2026-07-19)**
  — requested live right after confirming H4's automatic sync worked as intended.
  - `app/presentation/main.py` now serves the frontend's production build (`frontend/dist`) as
    static files at `/`, mounted after all API routes — one process, one port, no separate Vite
    dev server or CORS needed for that origin. Only mounts if the build exists, so `npm run dev`
    and the test suite (neither of which builds the frontend) are unaffected.
  - `frontend/.env.production` sets `VITE_API_BASE_URL=` (relative/same-origin) instead of the
    dev default's hardcoded `http://localhost:8000`, since production is now same-origin with
    whatever serves it (a future SSH tunnel on any local port, in this case).
  - `deploy/expense-tracker.service` + `deploy/README.md` — a persistent `systemd --user` service
    (auto-restart, survives reboot after a one-time `sudo loginctl enable-linger` run by the owner
    directly). `scripts/deploy_vm.py` automates future updates: sync, backend deps,
    `alembic upgrade head`, frontend rebuild, `systemctl --user restart`, health check.
  - **The VM got its own fresh Gmail connection and backfill** (15 emails scanned/matched, 14
    transactions created, 1 correctly flagged needs-review — the same "bill payment via net
    banking" template found during Epic F) — a deliberate fresh start, not a migration of the
    Mac's existing data, per the owner's own choice when the tradeoff was presented. The local Mac
    instance was then stopped.
  - **Two real operational issues found and fixed while making this persistent:** (1) a
    `systemd --user` service stops the moment the user's last session ends — discovered directly
    when the service kept dying every ~10 seconds in lockstep with SSH connect/disconnect, fixed
    by the owner enabling lingering; (2) the OAuth client secret file (`gmail_client_secret.json`,
    gitignored, never in `rsync`) was copied directly between the owner's own two machines via
    `scp` with permissions locked to `600` on arrival — never viewed or printed through any tool
    output.
  - See [DECISIONS.md](DECISIONS.md) ADR-0020 for the full reasoning and alternatives considered.

### Added (code)
- **H4: automatic background sync + live dashboard updates (2026-07-19)** — requested live while
  testing Epic F: new transactions now appear on the dashboard with no manual "sync now" action.
  - `app/infrastructure/sync_scheduler.py` (`SyncScheduler`) — a background thread polling every
    5 seconds by default (`SYNC_POLL_INTERVAL_SECONDS`), running the existing incremental-sync +
    classify/extract pipeline each cycle; started/stopped from FastAPI's lifespan hook.
  - New `GET /transactions/recent?since_id=` endpoint + `get_transactions_since`
    (`app/application/list_transactions.py`), ordered by `id` (creation order) rather than
    `txn_date`, for the dashboard to detect newly-arrived transactions.
  - `frontend/src/hooks/useNewTransactionNotifications.ts` polls that endpoint every 5 seconds;
    new transactions trigger a table refresh and a real browser `Notification` (after a one-time
    permission click) whose `onclick` opens straight to that transaction's correction form.
  - **Real Gmail push (Watch API + Cloud Pub/Sub) was considered and explicitly not adopted** —
    it requires a public HTTPS endpoint, in tension with the local-first deployment model
    (ADR-0002). The 1-second poll interval originally requested was also reconsidered after
    discussion: REQUIREMENTS.md §7 Assumption 8 already states sub-minute detection isn't
    required, and the bank's own email delivery lag dominates real latency regardless of poll
    speed. See [DECISIONS.md](DECISIONS.md) ADR-0019 for the full reasoning, presented to and
    agreed with the owner before building.
  - **Bug found and fixed via live verification:** the polling hook's baseline-tracking used
    `lastSeenId === null` as its "have I established a baseline" signal, which broke when zero
    transactions existed at page load — the first genuinely new transaction was silently
    absorbed into the (still-null) baseline instead of triggering a refresh. Fixed with an
    explicit `hasBaseline` flag. Caught by inserting a transaction into an empty database and
    watching the dashboard fail to react.
  - 131/131 backend tests passing (10 new) on macOS and the Ubuntu VM.

### Added (code)
- **Epic F (Dashboard: Review & Correction) complete (2026-07-19)** — all five stories (F1–F5):
  - **F1 (transaction list):** `frontend/src/components/TransactionsView.tsx` — every E1 filter
    exposed (payee, category, date range, amount range, method, type, free-text), plus pagination.
  - **F2 (detail + correction form):** `TransactionDetailPanel.tsx` — opens from a table row (F1)
    or a needs-review item (F4); every E3-editable field has a control; Save calls E3, "Not a
    real expense" calls E4 (both act on the same transaction, so both live in one panel).
  - **F3 (source email viewer):** a toggle inside the same panel. Renders the cached email
    content as plain escaped text (`<pre>`), never via `dangerouslySetInnerHTML` — it's untrusted
    external HTML (a real bank email; ADR-0006), so rendering it as trusted markup would be a
    real stored-XSS vector.
  - **F4 (needs-review queue view):** `NeedsReviewView.tsx` — lists both unmatched emails and
    low-confidence transactions (E5); a new small endpoint,
    `POST /needs-review/emails/{id}/ignore` (`app/application/ignore_needs_review_email.py`,
    confirmed with the user before building since it's beyond E1-E7's original scope), reuses the
    previously-unused `EmailMessageStatus.IGNORED` so an unmatched email — which has no
    `Transaction` for E4's dismiss to act on — can still be cleared from the queue.
  - **F5 (inline category creation):** the category picker in `TransactionDetailPanel` has a
    "+ New category…" option; saving calls `POST /categories` (E6) then `PATCH /transactions/{id}`
    (E3) with the new id.
  - No new dependency (e.g. React Router) was added for view navigation — `frontend/src/App.tsx`
    switches between the two current views with plain `useState`.
  - Verified by directly driving the actual running dashboard (browser automation) through every
    flow, per the Definition of Done for dashboard stories — not just written and assumed to
    work. **Found and fixed one real bug this way:** dismissing a low-confidence transaction left
    it visibly stuck in the needs-review queue, because `get_needs_review_queue` never checked
    `dismissed`, only `review_status` (which dismissing doesn't change). Fixed; regression test
    added. 121/121 backend tests passing (4 new) on macOS and the Ubuntu VM.
  - **Not verified against the Ubuntu VM specifically this time** — the SSH tunnel needed for a
    live browser pass against the VM's dashboard didn't persist reliably in this session's tool
    environment (see ARCHITECTURE.md §7/§8 for the full note); `scripts/dev.py` was confirmed to
    start cleanly on the VM directly, just not tunneled to a browser this session. Also found and
    manually cleaned up an orphaned process from an earlier session that had been silently
    squatting on the VM's port 8000 for hours, undetected by `vm_dev.py`'s existing cleanup
    patterns — noted as a real, if minor, tooling gap, not yet fixed.

### Added (code)
- **Epic E (API Layer) complete (2026-07-19)** — all seven stories (E1–E7):
  - **E1 (list/search):** `GET /transactions` (`app/application/list_transactions.py` +
    `app/presentation/transactions_router.py`) — filters by payee (substring), category, date
    range, amount range, payment method, type, and free-text (payee/category name); paginated
    (`limit`/`offset`, response includes `total`); excludes dismissed transactions by default.
  - **E2 (single transaction):** `GET /transactions/{id}` returns the transaction plus its
    linked source email content; scoped to the requesting user's own transactions.
  - **E3 (correct):** `PATCH /transactions/{id}` (`app/application/correct_transaction.py`) —
    amount, date, payee name, category, payment method, type; writes one `correction_log` row
    per changed field; sets `review_status=USER_CONFIRMED`. New `payees.default_category_id`
    column (migration `dcdef4f896b2`, COR-2) is set when a category is assigned, and now read
    back by `run_classify_and_extract` (Epic C) so a payee's *future* transactions default to
    it. Correcting "payee" renames the shared `Payee` row rather than reassigning to a different
    one — see BACKLOG.md E3 for the reasoning (alias normalization is explicitly deferred).
  - **E4 (dismiss):** `POST /transactions/{id}/dismiss` (`app/application/dismiss_transaction.py`)
    sets `dismissed=True`; the row and source email are never deleted (COR-4).
  - **E5 (needs-review):** `GET /needs-review` (`app/application/get_needs_review_queue.py`)
    combines unmatched/unparseable `EmailMessage`s (C7) and low-confidence `Transaction`s (an AI
    fallback result never auto-accepted) into one queue.
  - **E6 (categories):** full CRUD (`app/application/manage_categories.py` +
    `app/presentation/categories_router.py`); duplicate names for one user are rejected (409);
    deleting a category in use without an explicit `reassign_to` is rejected (409, with the
    affected count) rather than orphaning references.
  - **E7 (sync status):** `GET /sync/status` (`app/application/get_sync_status.py`) surfaces the
    last sync's health without reading log files directly.
  - 117/117 backend tests passing (24 new) on macOS and the Ubuntu VM (ADR-0017), via FastAPI's
    `TestClient` against the real request/response contract — no dashboard exists yet to drive
    these through an actual browser (that's Epic F).

### Added (code)
- **Epic D (Deduplication) complete (2026-07-19), no new production code** — DUP-1 (message-ID
  based duplicate detection) and DUP-2 (reference-number/timestamp disambiguation of genuinely
  repeated transactions) were both already guaranteed by constraints introduced in earlier epics:
  `email_messages.message_id` and `transactions.email_message_id` are both `unique` (A2), and
  `run_classify_and_extract` only processes `UNPROCESSED` emails (C7), so an already-handled
  message is never reprocessed. There is no content-based (amount/payee/day) matching step
  anywhere by design (ADR-0009), so two genuinely separate transactions sharing those fields are
  never at risk of being merged. `backend/tests/test_deduplication.py` (4 new tests) confirms
  this end-to-end rather than trusting the architecture on faith — including a same-day/amount/
  payee/exact-timestamp coincidence for the credit card debit template (no reference number),
  proving disambiguation is by Gmail message ID, never by comparing transaction content across
  messages. No dedicated `Deduplicator` component was added, since it would have had no logic to
  hold (Constitution principle 2). 93/93 backend tests passing on macOS and the Ubuntu VM.

### Fixed
- **Real HDFC HTML bolds transactional values — extraction regexes didn't tolerate it (found
  2026-07-19 during the user's own live spot-check, per ADR-0014's requirement that the user
  verify real results beyond the confirmed samples).** The plain-text quotes in
  REQUIREMENTS.md Appendix A don't show it, but the actual credit card debit template's HTML
  wraps the merchant name, amount, card-ending digits, and date/time in `<b>...</b>` tags (e.g.
  `Credit Card ending <b>2174</b>`) — a plain `\s*`/`\s+` gap between an anchor phrase and its
  value doesn't match through that. `app/domain/extraction.py` now uses a shared `_GAP` fragment
  (tolerant of any mix of whitespace and HTML tags) at every such anchor point across all three
  extractors, not just the one confirmed broken — the UPI templates only use `<br>` between
  whole fields in production, but hardening them the same way costs nothing and guards against
  the same bug class if that ever changes. Regression tests added with fabricated (not the
  user's real) values reproducing the tag-wrapping shape. Verified against the user's own two
  real, previously-misclassified emails (read-only check, then reprocessed once confirmed) — both
  now correctly extract; only type and amount were ever displayed, never other fields, per the
  minimal-disclosure precedent from Epic B's live verification. 89/89 backend tests passing (2
  new) on macOS and the Ubuntu VM.
- **Discovered a real fifth HDFC email type, correctly excluded by design, not a bug:** a
  "Credit Card Payment done using HDFC Bank Online Banking" notification (paying off the card
  bill via net banking) — distinct wording from all four confirmed templates, so it classifies
  as no match and lands in needs-review rather than being miscounted as spend. This is exactly
  the behavior REQUIREMENTS.md §7 Assumption 11 predicted for a bill-payment/repayment
  confirmation. Not a new `SenderRule` — recorded as a known, deliberately-unmatched email
  shape in REQUIREMENTS.md Edge Cases §10, since paying your own card bill isn't new spend and
  must never be counted as one.

### Added (code)
- **Epic C (Classification & Extraction) complete (2026-07-19)** — all eight stories (C1–C8):
  - **C1–C3 (classifiers):** `app/domain/classification.py` — `is_upi_debit`, `is_upi_credit`,
    `is_credit_card_debit` (pure content-pattern matchers per ADR-0010's confirmed markers) plus
    `classify()`, which picks the one matching `content_pattern_id` out of the caller-supplied
    candidates rather than trying all four unconditionally.
  - **C4–C6 (extractors):** `app/domain/extraction.py` — `extract_upi_debit`,
    `extract_upi_credit`, `extract_credit_card_debit`, each returning a structured
    `ExtractedTransaction` or raising `ExtractionError` (never a partial/fabricated result) when
    a required field can't be found. Handles the confirmed edge cases: absent parenthetical
    payee display name (UPI debit), absent reference number (credit card debit, dedup falls back
    to timestamp — DUP-2), differing `Rs.`-prefix spacing, and the credit card template's
    distinct `DD Mon, YYYY at HH:MM:SS` date/time format vs. the UPI templates' date-only
    `DD-MM-YY`.
  - **C7 (needs-review queue mechanics):** `app/application/run_classify_and_extract.py`
    (`run_classify_and_extract`) — classifies and extracts every `UNPROCESSED` `EmailMessage`;
    a clean match creates an `AUTO_ACCEPTED` `Transaction` (with `Payee` get-or-created by
    identifier) and marks the email `MATCHED`; anything that fails to classify or extract is
    marked `NEEDS_REVIEW` instead of dropped, with the classification result (if any) preserved
    via a new `email_messages.classified_pattern_id` column (migration `e5aa5f25c7b3`).
    `get_needs_review_emails` gives Epic E's E5 endpoint a ready-made query. Same
    not-yet-scheduled pattern as B4's incremental sync — nothing calls this automatically yet.
  - **C8 (AI fallback interface, stub):** `app/domain/ai_fallback.py` — `AIFallbackClient`
    protocol + `StubAIFallbackClient`, which always reports "unable to extract," proving the
    seam (Constitution principle 10) without committing to a provider. A fallback that *did*
    produce fields would still create a `Transaction`, but always `NEEDS_REVIEW`, never
    auto-accepted (EXT-4/EXT-5).
  - All extractors/classifiers tested directly against the real confirmed HDFC samples
    (REQUIREMENTS.md Appendix A), not synthetic stand-ins, per the Definition of Done. 87/87
    backend tests passing (34 new) on both macOS and the Ubuntu VM (ADR-0017); the new migration
    was applied to both the local and VM real databases so the running app stays consistent with
    the schema, even though this epic needed no live Gmail interaction (classification/extraction
    are pure functions over already-cached content).
  - **Noted, not fixed:** classification currently tries every configured
    `SenderRule.content_pattern_id` against every processed email rather than narrowing by the
    specific sender an email came from, since `EmailMessage` doesn't record that. Correct today
    (one sender address hosts all three confirmed patterns); would need revisiting for a second
    bank/sender. Also noted: `app/domain/classification.py`/`extraction.py` import
    `PaymentMethod`/`DebitOrCredit` from `app/infrastructure/models.py`, a minor Domain→
    Infrastructure layering wrinkle inherited from Epic A's enum placement — see
    [ARCHITECTURE.md](ARCHITECTURE.md) §3 for the full note.
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
