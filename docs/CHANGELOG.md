# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once
versioned releases begin.

## [Unreleased]

### Added (planning, no code yet)
- **Ledger (iOS app, ROADMAP.md M7) — visual design concept, then a five-epic backlog (2026-07-19).**
  A visual design concept (screen mockups, navigation model, endpoint mapping) was reviewed and
  confirmed by the owner first. Two decisions followed, made explicitly rather than assumed
  (Constitution principle 20):
  - **ADR-0023:** Ledger is native Swift + SwiftUI, not cross-platform — only iOS is planned for
    now.
  - **ADR-0024:** new-transaction notifications are in-app/foreground-only. Two stronger paths
    were presented and declined: direct Apple Push (APNs, requires the $99/year Apple Developer
    Program) and a free third-party push relay (ntfy.sh, which would route transaction text
    through a third party) — the owner chose neither, picking the weaker but fully first-party,
    fully free fallback instead. A best-effort `BGAppRefreshTask` supplement is included but
    explicitly documented as unreliable, not a substitute for either declined path.
  - `docs/BACKLOG.md` gained Epics I–M (iOS Foundation, Transaction List & Correction,
    Needs-Review Queue, Analytics, Manual Add & Notifications) — the detailed story breakdown,
    none yet started. `docs/REQUIREMENTS.md` gained §15 (MOB-1 through MOB-6). `docs/ARCHITECTURE.md`
    and `docs/ROADMAP.md` updated to reflect M7 moving from Planned to In Progress. No backend
    code changes — Ledger consumes the existing API surface exactly as it stands.
- **Ledger connectivity resolved: Tailscale VPN On Demand, not a manual toggle (2026-07-19,
  ADR-0025).** Daily manual Tailscale toggling was raised as a real usability concern. True
  per-app-only VPN (tunnel active only while Ledger runs) was investigated and found not possible
  on an unmanaged iPhone — it requires an MDM/supervised-device entitlement Apple doesn't grant to
  personal devices; Tailscale itself has an open, unresolved feature request for it
  ([tailscale/tailscale#18408](https://github.com/tailscale/tailscale/issues/18408)). Also
  clarified: Tailscale doesn't proxy general internet traffic by default (only tailnet-addressed
  traffic, unless an exit node is explicitly configured, which this setup doesn't use) — so the
  "always on" cost is a lightweight background tunnel, not a full-traffic VPN. Resolved as: the
  owner sets iOS Tailscale's **VPN On Demand to "Always" for Wi-Fi and Cellular**, once, on their
  own phone — a device setting, not app code. `docs/REQUIREMENTS.md` MOB-5 and `docs/BACKLOG.md`
  I3 updated to name this specific mechanism.

### Added (code)
- **Epic K complete: K1-K4 (2026-07-19), the needs-review queue.** New `Views/ReviewView.swift`
  (replacing I1's placeholder) + `ViewState/NeedsReviewStore.swift` — lists both halves
  `GET /needs-review` returns as separate sections with reason chips ("Unrecognized" /
  "Extraction failed" for unmatched emails, "Low confidence" for transactions), swipe-to-ignore for
  unmatched emails, and low-confidence transactions reusing J3's own detail sheet rather than a
  separate review-specific form. The Review tab's badge count is now owned by `RootTabView` (not
  `ReviewView` itself, so the tab item can read it) and refetched on launch, tab-switch, and
  app-foreground only — no polling. 58/58 iOS unit tests passing (6 new). K1, K2, and K4 verified
  live against the real local backend (one real unmatched email — a credit card bill payment via
  net banking, the known 5th HDFC shape from Epic C — showed its "Unrecognized" chip, and
  swipe-to-ignore correctly flipped its status server-side, reverted afterward since it was
  verification, not a real user action); K3 verified by code/tests only, since no real
  low-confidence transaction existed to drive through live this session.
- **Epic J complete: J5-J7 (2026-07-19), closing out Epic J entirely.** J5 (swipe actions) adds
  native `swipeActions` to each list row — Edit opens J3's sheet, Dismiss calls
  `POST /transactions/{id}/dismiss` directly and removes the row locally. J6 (category management)
  adds a new "Manage categories" screen (full CRUD, including the reassign-on-delete flow for a
  category still in use) reached from a gear-adjacent toolbar icon, plus an inline "+ New
  category…" option in J3's picker — two real SwiftUI alert/dismiss race bugs were found and fixed
  via live verification (an alert's `isPresented` binding must not be derived from the same state
  its own action reads, since dismissal and the action can run out of order). J7 (sync-health
  indicator) adds a small colored nav-bar dot reflecting `GET /sync/status`, tappable for the full
  scanned/matched/skipped/failed breakdown. 52/52 iOS unit tests passing (18 new); every story
  additionally verified live via the demo XCUITest harness against the real local backend.
- **Epic J: J4 (Source email viewer) complete (2026-07-19).** New
  `Views/SourceEmailView.swift`, reached via a "View source email" row in
  `TransactionDetailView` (shown only when `sourceEmail` is populated — manual entries keep J3's
  existing "no source email" note). Simpler than the web's equivalent story: SwiftUI's `Text`
  never interprets its string as HTML, so there's no `dangerouslySetInnerHTML`-shaped risk to
  avoid at all, just a code comment warning not to introduce one later (`NSAttributedString` HTML
  parsing or a `WKWebView`). Verified live via the demo XCUITest harness against a real synced
  transaction — screenshot confirms raw markup renders as literal text, not interpreted HTML.
- **Epic J: J3's row time-display gap fixed (2026-07-19).** Transaction rows only ever showed
  `txn_date`, missing the web dashboard's own Epic G follow-up (a time alongside the date, real or
  an approximate "~" one) — the owner caught this. New `Networking/TransactionDisplayTime.swift`
  mirrors `frontend/src/utils/transactionTime.tsx` exactly. Building it surfaced a second bug: the
  real backend serializes `email_received_at`/`created_at` with no timezone suffix at all
  (confirmed directly against the running server), which silently failed to parse — fixed by
  appending `"Z"` before parsing, matching the frontend's own naive-UTC handling. 5 new tests (31
  total), verified live with a screenshot against real data.
- **Epic J: J3 (Transaction detail sheet) complete (2026-07-19).** New
  `ViewState/TransactionDetailStore.swift` + `Views/TransactionDetailView.swift` — every row in
  `LedgerListView` is now tappable and opens an edit sheet (amount, date, payee, category,
  method, type) plus "Not a real expense" with a confirmation dialog. Known limitation documented
  in code: picking "Uncategorized" can't clear an already-set category (the backend's PATCH has no
  way to null a field, only leave it unchanged). 5 new tests (26 total). Verified live via the
  demo XCUITest harness with the real database checked via `curl` before/after each action —
  editing a payee name persisted correctly across two separate runs, dismissing a transaction
  flipped its `dismissed` field server-side. One real bug found and fixed this way: the detail
  view had a blank-screen gap before its `.task` even started (transaction nil, isLoading still
  false, errorMessage nil — none of the three view branches matched).
- **Epic J: J2 (Search & filter chips) complete (2026-07-19).** Debounced (~400ms) free-text and
  a new "payee contains" field (fixing a gap where J1 never actually exposed a payee input despite
  listing it as a required filter); removable chips for every active filter plus "Clear all". New
  `Views/FilterChip.swift`. Verified live via an XCUITest walkthrough (screenshots): payee filter
  narrows the list correctly, combining filters (payee + credit-type) correctly yields zero
  results, "Clear all" resets everything.
- **Epic J: J1 (Transaction list) complete (2026-07-19).** New
  `ios/Ledger/Ledger/ViewState/TransactionListStore.swift` +
  `Views/{LedgerListView,TransactionRowView,TransactionFilterSheet}.swift`. All 7 web-parity
  filters wired (category, date range, amount range, method, type, free-text, plus pagination via
  a "Load more" button); dismissed transactions excluded server-side, no client re-filtering.
  4 new tests (21/21 total). Filter UI is plain/functional for now, not yet the chip-based bar
  from the confirmed design — that's explicitly J2's job. Verified live against a real backend
  (screenshots): both the "no connection configured" error state and a populated list with real
  transactions, the "Manual" badge (H2), and debit/credit amount coloring.
- **Infrastructure: fixed the VM's backend bind address; discovered Tailscale was never actually
  set up on it (2026-07-19, ADR-0026).** While getting Ledger to talk to the production VM (I3's
  live check), found `deploy/expense-tracker.service` bound uvicorn to `127.0.0.1` only —
  unreachable from anywhere but itself, regardless of network. Fixed to `0.0.0.0` in both the repo
  file and the live VM unit; service restarted. This alone didn't fix reachability: further
  investigation found the VM has no `tailscaled` process, package, or state directory at all —
  REQUIREMENTS.md MOB-5's "reachable over Tailscale" assumption for this VM was never actually
  true. The owner's actual path to the VM is through their brother's NAS acting as a **Tailscale
  subnet router** (a different topology than ADR-0002/ADR-0020 assumed) — its firewall currently
  only forwards SSH; the brother is opening ports 6000-6500. **Not yet resolved** — once open, the
  production port likely needs to move off 8000 into that range, and REQUIREMENTS.md MOB-5 needs
  revising to describe the actual subnet-router topology. Meanwhile, Ledger development is
  proceeding against the backend running directly on the developer's own Mac (a genuine Tailscale
  peer, reachable as `naveen-zoho-macbook`).
- **Epic I: I3 (Backend reachability & connection settings) complete, code-side (2026-07-19).**
  New `ios/Ledger/Ledger/ViewState/ConnectionSettingsStore.swift` (`UserDefaults`-backed host/port,
  injectable client factory for testability) + `Views/ConnectionSettingsView.swift`, reached via a
  gear button in the Ledger tab's toolbar (no dedicated Settings tab in the confirmed 3-tab
  design). Checks `GET /health` then `GET /sync/status`, treating a 404 there ("no Gmail account
  yet") as still-reachable rather than an error. `APIClient` gained an explicit 8s request timeout
  so an unreachable host fails fast rather than hanging like `URLRequest`'s ~60s default would.
  Info.plist gained an `NSAllowsArbitraryLoads` ATS exception (the backend has no TLS cert and its
  hostname is runtime-entered, so a scoped exception isn't possible; documented in `project.yml`
  since Ledger is never App-Store distributed). 6 new tests, 17/17 total passing. **Not yet fully
  done:** the settings sheet's actual UI wasn't screenshot- or tap-verified (no GUI automation
  available in this environment) — needs a live check on the owner's phone against the real VM
  before Epic I's checkpoint demo.
- **Epic I: I2 (Backend API client module) complete (2026-07-19).** New
  `ios/Ledger/Ledger/Networking/` — Codable models and one `async throws` function per backend
  endpoint (transactions, needs-review, categories, sync status, analytics), built by reading the
  actual serializers/routers directly rather than guessing from REQUIREMENTS.md's prose (e.g.
  money fields are wire-level strings, `sync/status`'s `last_sync_*` keys are absent, not null,
  before the first sync). A `URLSessionProtocol` seam plus a `StubURLSession` test double make the
  client fully unit-testable without a real backend; 11 tests in
  `ios/Ledger/LedgerTests/APIClientTests.swift`, all passing. Typed `APIError` (unreachable /
  HTTP error / the one nested-object 409 shape / decode failure) — no silent failures.
- **Epic I started: Ledger iOS Foundation, I1 (Xcode project scaffold) complete (2026-07-19).**
  New `ios/Ledger/` — native SwiftUI app, project defined via a checked-in XcodeGen `project.yml`
  (not a hand-edited `.xcodeproj`); folder layout (`App`/`Views`/`ViewState`/`Networking`) and its
  dependency-direction rule documented in `ios/Ledger/README.md`, mirroring the backend's own A1
  convention. A 3-tab (`Ledger`/`Analytics`/`Review`) skeleton shell, no networking or business
  logic yet. Verified: builds and runs in the iOS Simulator (screenshot-checked), and separately
  confirmed by the owner running it on their own physical iPhone via free Xcode signing
  (ADR-0024) — including the one-time "trust this developer" / Developer Mode steps. Tab icons
  are placeholders pending a check against the original confirmed design mockup.
- **Epic H (Cross-cutting polish) complete (2026-07-19)** — the two remaining stories:
  - **H1 (encryption verification):** already satisfied, no new code — credited to
    `backend/tests/test_schema.py::test_sensitive_fields_are_encrypted_at_rest`, built during
    Epic A2 (2026-07-18), which already opens the raw SQLite file directly and confirms
    `gmail_connections.tokens`/`email_messages.content` aren't human-readable while a plain
    column is. Just never cross-referenced in BACKLOG.md's Epic H section until now.
  - **H2 (manual "add a transaction" escape hatch, COR-5):** `transactions.email_message_id` is
    now a nullable FK (migration `8bcc9bb76003`) — `NULL` is the "manually added" marker, not a
    separate flag (ADR-0022). New `app/application/add_manual_transaction.py`
    (`add_manual_transaction`) + `POST /transactions`; payee matched case-insensitively by name
    (no VPA to key on for a typed-in name), COR-2's remembered-category behavior applies the same
    way it does for corrections and auto-ingestion. `frontend/src/components/
    AddTransactionPanel.tsx` — a new "+ Add transaction" button in `TransactionsView`, a
    persistent "Manually added — no source email" banner framing it as the exception (not the
    norm). Rows with no source email get a "Manual" badge in the table;
    `TransactionDetailPanel` substitutes a note for its "View source email" button on these rows
    rather than showing a broken toggle. `app/domain/transaction_time.py`'s
    `effective_sort_datetime` gained a third fallback tier (`created_at`) for transactions that
    have neither a real `txn_time` nor a source email to borrow a time from.
  - `serialize_transaction`/`GET /transactions/{id}` updated to handle a null `email_message`
    (`email_received_at`/`source_email` become `None`) — the one place Epic G's time-display
    follow-up had assumed every transaction has a source email.
  - Tests: `TestAddManualTransaction` (3 tests) + a new `effective_sort_datetime` fallback-tier
    unit test. 148/148 backend tests passing (4 new) on macOS and the Ubuntu VM
    (`scripts/vm_test.py`). Verified live: added two manual transactions via the running
    dashboard for the same payee in different casing — confirmed the badge, the detail panel's
    note, correct time-based sort position, and that the category assigned on the first entry was
    automatically applied to the second (COR-2) without being asked again.

### Added (code)
- **Epic G (Search & Analytics) complete (2026-07-19)** — all four stories (G1–G4), closing out
  REQUIREMENTS.md §13's MVP definition (modulo the still-pending 4th email template):
  - **G2 (monthly summary):** `app/application/analytics.py` (`get_monthly_summary`) +
    `app/presentation/analytics_router.py` — `GET /analytics/monthly?month=YYYY-MM` (defaults to
    the current month), bucketed by `txn_date` (not email-received date, per Edge Cases §10).
    A new "Analytics" tab (`frontend/src/components/AnalyticsView.tsx`) adds Previous/Next month
    navigation and summary cards (spent/received/net/count).
  - **G3 (category breakdown):** `get_category_breakdown` — debits only (a refund isn't spend),
    grouped by category with an "Uncategorized" bucket for untagged transactions, ordered by
    total descending; rendered as a plain table in the same Analytics tab, reusing G2's month
    cursor rather than a separate date-range picker.
  - **G4 (payee history):** `get_payee_history` — matches by case-insensitive exact payee name
    (not substring, since the dashboard's one caller is always an exact click on an exact name),
    404s for an unknown name; `frontend/src/components/PayeeHistoryPanel.tsx` opens as a side
    panel (matching `TransactionDetailPanel`'s shape) when a payee name is clicked in
    `TransactionsView`'s table, showing totals plus a clickable transaction list that opens the
    existing detail panel on top.
  - **G1 (search/filter polish)** — no acceptance criteria existed in BACKLOG.md; resolved via a
    clarifying question to the owner (functional + visual polish, no URL-persisted filters).
    `TransactionsView.tsx`'s free-text/payee inputs are now debounced (~400ms) instead of firing
    one request per keystroke; a "Clear all filters" button resets every filter (all inputs are
    now controlled, so this also visibly clears the DOM); active filters render as removable
    chips.
  - Five money-semantics/scope decisions not spelled out in the original story text (sign
    convention, debit-only category spend, shared month cursor for G3, exact-name payee
    matching, no date scoping on G4) recorded in [DECISIONS.md](DECISIONS.md) ADR-0021.
  - 139/139 backend tests passing (8 new) on macOS and the Ubuntu VM (`scripts/vm_test.py`).
    Dashboard verified by directly driving the running UI (Browser tool): confirmed the debounce
    via the Network tab (6 keystrokes → 1 request), chip removal and "Clear all," month
    navigation between a populated and an empty month, category breakdown excluding a real
    credit, and the full payee-history-panel → transaction-detail-panel click-through. No bugs
    found this time. Deployed live to the production VM via `scripts/deploy_vm.py` and confirmed
    working against the owner's real data.
  - **Requested live during the epic-checkpoint demo (2026-07-19):** the transaction date column
    (F1's table, and G4's payee history panel) now shows a time next to the date, in 12-hour
    AM/PM format, for every transaction — not just the ones whose source template captured one.
    The UPI templates are date-only (REQUIREMENTS.md Appendix A), so there's no real bank
    transaction time to show for those; the owner was asked directly (rather than fabricating a
    time silently) and chose to show the source email's received time instead, visually marked as
    an approximation (`~` prefix, muted/dotted styling, a tooltip explaining it's not the actual
    transaction time). `serialize_transaction` (`app/presentation/serializers.py`) now exposes
    `email_received_at`; `list_transactions`/`get_transactions_since`/`get_payee_history` eager-
    load the `email_message` relationship (`joinedload`) to avoid an N+1 query per row now that
    every serialized transaction touches it. A shared `frontend/src/utils/transactionTime.tsx`
    (`TransactionDateTime`) replaces the two components' previously-duplicated formatting logic.
  - **Follow-up, requested immediately after (2026-07-19):** the transaction list wasn't actually
    sorted by the time it now displays — `list_transactions`/`get_payee_history` still ordered by
    `Transaction.id` within a date (creation order), which visibly scrambled same-day rows once a
    time column existed to notice it by. Fixed with a new `app/domain/transaction_time.py`
    (`effective_sort_datetime`) — the same "real `txn_time`, or the email's received time shifted
    to IST" logic the display uses, now also driving the sort, so the two can't disagree. Since
    this mixes two different source columns/tables, it can't be expressed as a single SQL
    `ORDER BY`; `list_transactions` and `get_payee_history` now fetch all matching rows (already
    eager-loading `email_message`) and sort in Python before paginating, trading a small, currently
    negligible amount of query efficiency for correctness (Constitution principle 16) — acceptable
    at this product's single-user scale, revisit only if a real performance problem is measured.
    `backend/tests/test_transaction_time.py` (pure-function unit tests, including the IST
    day-boundary edge case) plus new ordering assertions in `test_transactions_routes.py` and
    `test_analytics_routes.py`. 144/144 backend tests passing (5 new) on macOS and the Ubuntu VM.

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
