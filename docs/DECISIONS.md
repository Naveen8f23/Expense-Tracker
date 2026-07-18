# Architecture Decision Log

This is an ADR (Architecture Decision Record) log. Every significant architectural or
engineering decision made on this project must be recorded here, per
[CONSTITUTION.md](CONSTITUTION.md) principle 11. Entries are append-only: to change a past
decision, add a new entry that supersedes it — don't edit history.

## ADR Template

Copy this block for each new decision:

```
## ADR-XXXX: <Short title>

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded by ADR-YYYY | Deprecated
- **Decision:** <What was decided, stated plainly>
- **Context:** <What problem or situation prompted this decision>
- **Alternatives considered:** <Other options and why they were not chosen>
- **Reasoning:** <Why this option won — tradeoffs weighed>
- **Consequences:** <What this makes easier/harder going forward; any follow-up work created>
```

## Log

### ADR-0001: Establish `/docs` engineering foundation before writing application code

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** Create `CONSTITUTION.md`, `REQUIREMENTS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
  `DECISIONS.md`, and `CHANGELOG.md` under `/docs` as the governing set of documents for this
  project, and read/consult them before any significant future task, before writing any
  application code.
- **Context:** The project (`expense_tracker`) is starting from an empty repository. Without an
  agreed set of principles, requirements template, and decision log in place first, early
  implementation work risks accumulating undocumented assumptions and inconsistent
  architecture as AI-assisted development proceeds.
- **Alternatives considered:**
  1. Start writing application code directly and document architecture retroactively —
     rejected because retroactive docs tend to drift from reality and undocumented decisions
     get made by default rather than deliberately.
  2. Use a single combined `docs/README.md` instead of six separate files — rejected because
     the six concerns (principles, requirements, architecture, roadmap, decisions, changelog)
     have different update cadences and audiences; separating them keeps each one focused and
     easier to keep current.
- **Reasoning:** A small upfront investment in a documentation scaffold pays for itself by
  giving every future task a place to check for existing constraints (Constitution), a source
  of truth for scope (Requirements), a living picture of structure (Architecture), a sequencing
  plan (Roadmap), a rationale trail (Decisions), and a user-facing history (Changelog).
- **Consequences:** All future significant tasks must read these five docs (excluding
  Changelog, which is written to, not read for guidance) before implementation, per the
  Working Rules in `CONSTITUTION.md`. `REQUIREMENTS.md` and `ARCHITECTURE.md` remain templates
  until real requirements and structure are defined — no application code should be written
  until at least the core of `REQUIREMENTS.md` is filled in.

### ADR-0002: Local-first deployment model

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** The application and all its data (Gmail OAuth tokens, cached email content,
  extracted transactions) run on a single machine the user controls. No multi-tenant cloud
  hosting in v1.
- **Context:** The product reads the user's Gmail and builds a complete personal financial
  history — a highly sensitive dataset. The user is also the only user for the foreseeable
  future, so there is no immediate need for remote access from multiple devices/locations.
- **Alternatives considered:** A cloud-hosted service, accessible from anywhere and easier to
  extend to multiple users later — rejected for v1 because it requires a real multi-tenant
  security model, encrypted token storage in a shared environment, and hosting costs, none of
  which are justified yet for a single user.
- **Reasoning:** Local-first minimizes the security/privacy surface for the most sensitive
  possible data (financial history) while the product is unproven, at the cost of not being
  accessible remotely without extra setup.
- **Consequences:** Gmail push notifications (Watch API) require a publicly reachable
  endpoint, which is in tension with local-first — sync will need to be polling-based (see
  [REQUIREMENTS.md](REQUIREMENTS.md) Assumption §7.8) unless a future decision changes this.
  Multi-user support later most likely means either running separate local instances per user
  or a deliberate follow-up decision to move to a hosted model — either path is still open.

### ADR-0003: Web dashboard as the primary interface; mobile app as a later, separate client

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** Build a browser-based web dashboard as the v1 interface. A mobile app is
  planned for a later phase, built as an additional client of the same backend/API rather than
  a parallel pipeline.
- **Context:** Needed a primary interface for reviewing/correcting transactions and viewing
  analytics. The user confirmed they want mobile eventually but are comfortable sequencing it
  after the ingestion/extraction pipeline is proven, and asked whether building a mobile app on
  top of a pre-existing pipeline is a sound approach.
- **Alternatives considered:** CLI/API-only (rejected — makes correction and analytics review
  clunky, which undermines the "corrections should be easy" requirement); mobile-first
  (rejected — highest build cost up front, before the extraction pipeline is validated).
- **Reasoning:** A web dashboard is the fastest path to a usable review/correction/analytics
  surface. Keeping the backend as a clean API from the start (per the plug-and-play module
  requirement) means a future mobile app is genuinely just another client — this is a standard
  and low-risk pattern, not a rewrite.
- **Consequences:** The API boundary between backend and any UI must be designed deliberately
  from v1, even though only a web frontend consumes it initially, so the mobile app doesn't
  force a backend redesign later.

### ADR-0004: INR-only currency scope for MVP, multi-currency-ready data model

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** The MVP assumes INR as the only transaction currency. Every monetary value is
  still stored with an explicit currency code so multi-currency support is additive later.
- **Context:** The user's example transaction sources (UPI, Flipkart, Swiggy, Zomato, Ola) are
  India-centric. Full multi-currency support (conversion, mixed-currency display, foreign-card
  spend handling) adds real complexity that isn't needed yet.
- **Alternatives considered:** Full multi-currency from day one — rejected for MVP as
  premature scope given no current need, but the data model still carries a currency field per
  [CONSTITUTION.md](CONSTITUTION.md) principle 2 (avoid premature abstraction, but don't
  paint into a corner on a field that's essentially free to add now and expensive to retrofit).
- **Reasoning:** Keeps MVP scope tight while avoiding a schema migration when multi-currency
  is eventually needed (e.g. a foreign-currency card charge).
- **Consequences:** Foreign-currency transactions (e.g. while traveling) may extract with a
  non-INR currency code and should be flagged for review rather than mishandled, even though
  full conversion/display support isn't built yet.

### ADR-0005: Ingest only order-confirmation emails from known e-commerce/food-delivery vendors; use bank/card/UPI alerts for everything else

- **Date:** 2026-07-18
- **Status:** Superseded by ADR-0009
- **Decision:** For known e-commerce/food-delivery marketplace vendors (Amazon, Flipkart,
  Swiggy, Zomato, Uber, Ola, etc.), only the vendor's order-confirmation email is ingested —
  it already contains the amount debited/credited. The vendor's own payment-confirmation and
  delivery/shipping emails are explicitly excluded. Bank, card, and UPI/wallet alert emails
  remain the source of truth for spend that has no corresponding vendor order-confirmation
  email (direct card swipes, UPI transfers, utility bills, bookings, subscriptions charged
  directly).
- **Context:** The original spec assumed the system would need to correlate multiple emails
  per purchase (order + payment + bank debit alert) and merge them into one transaction. The
  user clarified that, in practice, only the vendor's order-confirmation email is needed —
  it's simpler and sufficient.
- **Alternatives considered:** Ingesting all email types per purchase and merging them after
  the fact (the original DUP-1 design) — rejected as unnecessary complexity once a single
  authoritative email per purchase is available; multi-email correlation is real work
  (matching logic, ambiguity, false merges) that this decision avoids entirely for the
  marketplace-vendor case.
- **Reasoning:** Filtering at the ingestion/classification stage (by email type, not just
  sender) is simpler and more reliable than ingesting everything and deduplicating downstream.
  It also reduces the volume of email content that needs extraction/processing at all,
  which is a privacy and cost win.
- **Consequences:** Opens a new, currently unresolved question (REQUIREMENTS.md §8, blocking):
  if a bank/card also sends a separate debit alert for the same marketplace purchase, that
  alert must not become a second transaction. This needs to be resolved before the
  deduplication module (DUP-1) is implemented for real.

### ADR-0006: Defer phishing/prompt-injection hardening of the extraction pipeline

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** The extraction pipeline will not be hardened against phishing emails or
  prompt-injection attempts embedded in email content for v1. This is an explicitly accepted
  risk, not an oversight.
- **Context:** The original spec (EXT-7) required treating email content as untrusted input to
  any AI extraction step, given that a malicious email could otherwise try to manipulate an
  AI-based extractor. The user asked to deprioritize this for now.
- **Alternatives considered:** Building input-sanitization/prompt-hardening now — rejected for
  v1 given the user's explicit call to deprioritize it, and because the mailbox in question is
  the user's own personal, single-owner inbox rather than a shared or externally-exposed
  system where this risk is more acute.
- **Reasoning:** For a single-user, local-first system reading one person's own inbox, the
  realistic exposure to adversarial email content is low relative to the cost of building
  defenses now. This tradeoff should be revisited before any multi-user, externally-exposed,
  or higher-stakes version (see [ROADMAP.md](ROADMAP.md) M8).
- **Consequences:** If AI-based extraction is used (now only as a rare fallback per ADR-0007),
  a sufficiently crafted malicious email could in principle influence what the extractor
  reports for that one email. Accepted as a known limitation for v1; tracked in
  REQUIREMENTS.md §12 (Deferred Features) so it isn't forgotten.

### ADR-0007: Deterministic-first extraction; AI only as a fallback for unrecognized emails

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** Extraction is built primarily as fixed, per-vendor/per-sender parsing rules
  for the known, stable set of templates (Amazon, Flipkart, Swiggy, Zomato, banks, etc.). An
  AI model is used only as a fallback when an email matches no known template, and its output
  is always routed to the "needs review" queue rather than trusted outright.
- **Context:** This resolves the blocking question of whether extraction requires sending
  email content to a cloud AI API, which was in tension with the local-first deployment
  decision (ADR-0002). Given the narrow, named set of vendors confirmed in ADR-0005, most
  emails follow a small number of stable formats well-suited to fixed parsing rules.
- **Alternatives considered:** Always use a cloud AI API (rejected — sends all processed email
  content to a third party, undermining local-first); always use a locally-run AI model with
  no fixed rules (rejected — unnecessarily weaker/slower for formats that are simple and
  stable enough to parse deterministically, per Constitution principle 9).
- **Reasoning:** Per Constitution principle 9 (prefer deterministic solutions over AI when
  sufficient) and principle 10 (isolate AI behind a well-defined interface), this narrows the
  privacy/security exposure of ADR-0006 and the local-first guarantee of ADR-0002 to a small,
  rare slice of unmatched emails rather than the entire pipeline.
- **Consequences:** Whether the rare-case AI fallback itself runs locally or via a cloud API
  is a smaller, non-blocking follow-up decision (low volume, already flagged for review either
  way) — to be made when the extraction module is designed, not before.

### ADR-0008: Exclude bank/card alerts that match an already-covered known vendor

- **Date:** 2026-07-18
- **Status:** Superseded by ADR-0009
- **Decision:** When a bank/card/UPI alert's merchant string matches a vendor already covered
  by the order-confirmation-only rule (ADR-0005), that alert is excluded at ingestion and never
  becomes a transaction. The vendor's order-confirmation email remains the sole source for that
  purchase.
- **Context:** The user confirmed that their bank/card does send a separate debit alert for
  purchases from vendors like Amazon, in addition to the vendor's own order-confirmation email.
  Without a rule to handle this, the same purchase would be recorded twice.
- **Alternatives considered:** Matching and merging the vendor order email with the
  corresponding bank alert after both are ingested (i.e. reintroducing the original DUP-1
  multi-email correlation this design was trying to avoid) — rejected as unnecessary
  complexity when a simple exclusion filter at ingestion achieves the same outcome more
  reliably.
- **Reasoning:** An exclusion filter (by merchant-name match against the known-vendor list) is
  simpler, cheaper, and less error-prone than post-hoc correlation between two independently
  ingested emails.
- **Consequences:** The known-vendor list becomes a load-bearing piece of configuration — a
  bank alert for a vendor not yet on that list would be ingested as its own transaction
  (correct, since no order-confirmation email exists for it), but a newly added vendor must be
  added to the list on both sides of the filter consistently.

### ADR-0009: Narrow ingestion to exactly four fixed bank/UPI email types; drop vendor-email tracking entirely

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** Ingestion and extraction are scoped to exactly four bank/UPI
  transaction-notification email types, each identified by a specific known sender address the
  user supplies: (i) UPI debit, (ii) UPI credit, (iii) credit card debit, (iv) credit card
  credit. These four are the sole and complete source of truth for the transaction history.
  All third-party vendor emails (Amazon, Flipkart, Swiggy, Zomato, Uber, Ola order/payment/
  delivery emails) are dropped entirely — not filtered down, removed as an ingestion source.
- **Context:** ADR-0005 (order-confirmation-only ingestion from known vendors) and ADR-0008
  (excluding bank alerts that overlap with a known vendor) were both designed to avoid
  double-counting between two independent sources of the same purchase — a vendor's email and
  a bank's email. The user determined this dual-source problem isn't worth solving: the four
  bank/UPI notification emails alone already capture every debit and credit with an amount, are
  uniform in structure, and come from a small, fixed set of senders — simpler and more complete
  than maintaining a growing list of vendor formats.
- **Alternatives considered:** Keep both vendor-email and bank-alert ingestion with the
  exclusion-filter approach from ADR-0005/ADR-0008 — rejected as needless complexity now that a
  single, uniform, complete source (bank/UPI alerts) is available on its own. A hybrid approach
  (vendor emails for richer per-item detail, bank alerts as fallback) — rejected for MVP; could
  be revisited later if itemized purchase detail (what was bought, not just how much) becomes a
  real need (see REQUIREMENTS.md §12).
- **Reasoning:** Four fixed, known templates from four known senders is about as simple and
  deterministic as this problem gets, directly serving Constitution principles 2 (avoid
  unnecessary abstraction) and 9 (prefer deterministic solutions). It also shrinks the
  ingestion/extraction surface area dramatically, which reduces both engineering effort and the
  AI-processing privacy exposure discussed in ADR-0006/ADR-0007.
- **Consequences:** ADR-0005 and ADR-0008 are superseded — the vendor allow-list and the
  vendor/bank exclusion-filter logic they introduced are no longer needed. This loses
  itemized/merchant-page detail a vendor's own order email might have included (the bank/UPI
  email typically shows only a payee name/reference, not line items). It also surfaces a new
  open question, not yet resolved: does this fully cover the user's spending, or are there
  payment methods (debit card, net banking, mobile wallet, cash) not captured by these four
  templates? Tracked as REQUIREMENTS.md §7 Assumption 9 / §8 Open Question (important, pending
  user confirmation).
  - **Update 2026-07-18:** this spending-coverage question was resolved directly in
    REQUIREMENTS.md §7 Assumption 9 — the four email types cover the large majority of spend;
    small exceptions (e.g. cash) are an accepted minor gap.

### ADR-0010: Email-type classification requires content-pattern matching, not sender address alone

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** Classifying which of the four transaction types a matched email represents
  requires a two-stage check: (1) a sender allow-list (is this address a known bank/UPI alert
  sender at all?), then (2) a content-pattern match against fixed phrases in the email body to
  determine the specific type. `SenderRule` (REQUIREMENTS.md §5 Data Model) is redefined as a
  pairing of sender address + content pattern → type, not a simple 1:1 sender → type mapping.
- **Context:** ADR-0009 assumed each of the four transaction types would be identifiable by a
  distinct sender address. Real sample emails provided by the user (REQUIREMENTS.md Appendix A)
  show this isn't true for HDFC: `alerts@hdfcbank.bank.in` sends UPI debit, UPI credit, and
  credit card debit notifications — three different types from one address, distinguished only
  by differences in body content (e.g. "is debited from your account ending" + "towards VPA"
  for UPI debit, vs. "has been successfully credited to your HDFC Bank account" for UPI
  credit).
- **Alternatives considered:** Treating sender address as sufficient and requiring the user to
  set up a different forwarding/filter per type outside the system — rejected as pushing
  complexity onto the user for something the system can determine directly from content it
  already has to read anyway.
- **Reasoning:** Per Constitution principle 9 (prefer deterministic solutions), a fixed
  content-pattern match is just as deterministic as a sender-address check — it's simply a
  second, necessary discriminator once real data showed sender address alone was
  insufficient. This is a correction based on evidence, not new complexity for its own sake.
- **Consequences:** The extraction/classification module must check body content even to
  determine transaction *type*, not only to extract fields — these two steps are more coupled
  than originally modeled. Also confirmed as a side effect: these HDFC alert emails are
  HTML-with-images-and-branding, but the transactional details are in plain text, not embedded
  in an image — reinforcing that no OCR pipeline is needed, at least for this sender (see
  REQUIREMENTS.md Edge Cases §10).

### ADR-0011: Initial backfill starts from the first day of the current calendar month, not a rolling historical window

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** The one-time initial backfill (ING-4) covers email from the first day of the
  calendar month in which the application is first set up and run, through the moment of setup
  — not a rolling window like "last 12 months," and not the user's full mailbox history.
- **Context:** The original spec left the backfill window as an open question, defaulting to
  something like a 12-month lookback. The user decided instead to start the tracker's history
  at the beginning of the setup month, effectively choosing "start fresh from now" over "import
  my past."
- **Alternatives considered:** A rolling N-month window (e.g. 12 months) — rejected by the
  user in favor of a simpler, smaller starting point. Full mailbox history — rejected as
  unnecessary given the decision to start fresh.
- **Reasoning:** Starting from the current month keeps the very first sync small and fast
  (at most a few weeks of email, not years), removes the need to handle a large one-time
  backfill as a real engineering concern, and gives clean, complete monthly reporting from
  month one (backfilling from the 1st, not the setup date, avoids a partial first month in
  ANL-1/ANL-4 summaries).
- **Consequences:** No historical transaction data from before the setup month will ever be in
  the system unless the user later explicitly chooses to run a deeper backfill (not built for
  MVP). The Edge Cases §10 concern about "very large historical backfill" is now largely moot
  for the default path.

### ADR-0012: Cache source email content locally at ingestion time

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:** The system stores a local copy of each ingested email's relevant content at
  ingestion time, rather than only keeping a reference (message ID) that depends on the email
  continuing to exist in Gmail.
- **Context:** TRC-3 left open whether traceability (TRC-1, TRC-2) should depend on the email
  still being present in Gmail, or be self-contained locally. Since the deployment is
  local-first (ADR-0002) and all data already lives on the user's own machine, storing a local
  copy doesn't introduce a new third-party exposure — it only adds local storage.
- **Alternatives considered:** Reference-only (store just the Gmail message ID and re-fetch on
  demand) — rejected because it makes traceability fragile: if the user deletes, archives, or
  loses access to the original email (or revokes Gmail access entirely), the system would lose
  its ability to show "here's the email this came from," undermining a core product goal
  (every transaction traceable to its source, REQUIREMENTS.md §1).
- **Reasoning:** For a local-first system where the whole point is owning your own data, making
  traceability depend on an external system (Gmail) continuing to hold the same content
  indefinitely is a weaker guarantee than just keeping the copy locally. The storage cost is
  small (short transactional emails, not large attachments) relative to the reliability gained.
- **Consequences:** The local database's storage footprint includes email content, not just
  extracted fields — reinforces the existing requirement to encrypt data at rest (§4 NFR
  Security). Deleting a transaction (COR-4) or the whole dataset (§4 NFR Data retention) must
  also delete its cached email content, not leave orphaned copies behind.

### ADR-0013: Technology stack (Python/FastAPI, SQLite, React)

- **Date:** 2026-07-18
- **Status:** Accepted (confirmed by the user 2026-07-18; originally proposed same day)
- **Decision:** Recommend, but not yet lock in: a Python + FastAPI backend service (ingestion,
  classification, extraction, dedup, API layer); an encrypted SQLite database (e.g. via
  SQLCipher) as the sole data store; a React (with Vite) single-page web app as the dashboard,
  talking to the backend only through its API; a simple in-process timer as the sync scheduler
  (no external job queue); and a pluggable `AIFallbackClient` interface with the actual
  provider (cloud vs. local model) deferred as a smaller, separate decision.
- **Context:** [ARCHITECTURE.md](ARCHITECTURE.md) needed a concrete stack to make the build
  plan (ROADMAP.md M2–M5) actionable. Earlier spec work deliberately deferred technology
  choices (per the user's original instruction) while requirements were being nailed down;
  those are now settled enough that a stack recommendation is useful, but it is being proposed
  for confirmation rather than assumed, per Constitution principle 20 (present tradeoffs,
  recommend one, before implementation).
- **Alternatives considered:**
  - **Node.js/TypeScript full-stack** (one language for backend and frontend) — a reasonable
    alternative; not chosen because Python's Gmail API tooling and general text-parsing
    ecosystem are somewhat more mature for this specific ingestion/extraction-heavy workload,
    and the team is a single person so "one language everywhere" matters less than for a team.
  - **PostgreSQL instead of SQLite** — rejected for v1: a separate database server is
    unnecessary operational overhead for a single-user, single-machine deployment (Constitution
    principle 2, avoid unnecessary complexity); can be revisited if multi-user (ROADMAP.md M8)
    ever demands it.
  - **Django instead of FastAPI** — a heavier, more opinionated framework than needed for a
    small API surface with no built-in-admin/templating requirement; FastAPI is lighter and
    sufficient.
  - **A job queue (e.g. Celery + Redis) for the scheduler** — unnecessary infrastructure for
    "check for new email every N minutes" at single-user scale; a simple in-process timer is
    sufficient and removes two more moving parts to install/run.
- **Reasoning:** Every choice favors fewer moving parts and mainstream, well-documented
  tooling over anything exotic, matching Constitution principles 2 (simplicity), 3 (justify
  every dependency), and the local-first deployment model (ADR-0002). Each piece is also
  swappable later without a rewrite, since the layered design (ARCHITECTURE.md §3) keeps
  Infrastructure choices behind interfaces.
- **Consequences:** If accepted, this becomes the concrete stack for ROADMAP.md M2 onward.
  Encryption mechanism (SQLCipher specifically) still needs to be verified as suitable when
  implementation starts. This ADR's status should be updated to Accepted (or replaced with a
  new ADR if the user picks differently) before Phase 1 implementation begins.
  - **Update 2026-07-18: Status changed to Accepted.** The user confirmed this stack as-is.
    The detailed build backlog derived from it is tracked in `docs/BACKLOG.md`.
  - **Update 2026-07-18: encryption mechanism revised — see ADR-0015.** SQLCipher (mentioned
    here as the presumed encryption approach) turned out not to be reliably installable
    cross-platform; superseded by ADR-0015's application-level field encryption.

### ADR-0015: Platform-independence constraint, and encrypting only sensitive fields instead of the whole database

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:**
  1. The system must run identically on macOS (development machine) and Ubuntu (the actual
     deployment target, an Ubuntu VM) — nothing platform-specific may be baked into the code,
     scripts, or dependency choices.
  2. "Encrypted at rest" (REQUIREMENTS.md §4 NFR Security) is implemented as **application-level
     encryption of the genuinely sensitive fields only** — Gmail OAuth tokens
     (`gmail_connections`) and cached raw email content (`email_messages`) — using the
     `cryptography` package (Fernet/AES). Transaction fields (amount, date, payee, category,
     etc.) are stored unencrypted in the SQLite file; their at-rest protection relies on file
     permissions and whatever OS-level disk encryption the user has enabled (FileVault on
     macOS, LUKS on many Ubuntu setups) — not guaranteed by the application itself.
- **Context:** The user clarified that although development happens on their MacBook (Apple
  Silicon), the application will actually run on an Ubuntu VM after completion — a constraint
  not previously stated. This surfaced a real problem with the presumed encryption approach:
  attempting to install `sqlcipher3-binary` and `pysqlcipher3` on the development machine
  itself failed (no compatible wheel; native build failure — see session log), demonstrating
  exactly the kind of native-compiled-dependency fragility that tends to behave differently
  across OS/architecture combinations. Continuing to rely on it would risk the same or worse
  failures on the Ubuntu VM, discovered late.
- **Alternatives considered:**
  - **Keep pursuing SQLCipher**, e.g. via a Linux-specific build step — rejected: even if it
    could be made to work on Ubuntu specifically, it already failed on the development machine,
    meaning local development/testing would be broken or require a different code path than
    production — violating the platform-independence goal directly.
  - **Whole-database file encryption via decrypt-on-start/encrypt-on-stop** — considered;
    rejected by the user in favor of the simpler option, given it adds real complexity (a
    temporary decrypted copy on disk while running) and a crash-safety gap (an unclean shutdown
    could leave that decrypted copy behind).
- **Reasoning:** The `cryptography` package is one of the most widely used, well-maintained
  Python libraries, with robust prebuilt wheels across macOS/Linux/Windows and both common
  architectures — verified working on the development machine in this session. Encrypting only
  the fields that are genuinely sensitive (credentials; raw email content, which contains PII
  and full transaction context) protects what actually matters most, while avoiding a fragile
  native dependency, in line with Constitution principle 2 (avoid unnecessary complexity) and
  principle 3 (justify every dependency).
- **Consequences:** This is a **weaker guarantee than "the whole database is encrypted"** as
  originally worded in REQUIREMENTS.md §4 — transaction amounts, dates, and payee names are
  plaintext in the SQLite file if the OS disk itself isn't encrypted. REQUIREMENTS.md §4 has
  been reworded to describe this honestly rather than overstate the guarantee.
  `BACKLOG.md` stories A2 and H1 are updated to reflect field-level (not whole-file) encryption
  as their acceptance criteria. Any dev-tooling scripts (A4) must avoid OS-specific commands
  (e.g. no macOS-only utilities), favoring Python-based orchestration for portability.

### ADR-0014: Verification policy — automated tests + agent-driven UI checks, epic checkpoints, user-gated Gmail live testing

- **Date:** 2026-07-18
- **Status:** Accepted
- **Decision:**
  1. Backend/logic stories (Epics A–E) are verified with automated tests, run for real, using
     the confirmed sample emails (REQUIREMENTS.md Appendix A) as fixtures — not just written
     and assumed to pass.
  2. Dashboard stories (Epics F–G) are verified by directly driving the running UI (browser
     automation) through the flow each story describes, observing the actual result.
  3. The live Gmail OAuth consent step (starting with story B1) is tested mechanically with
     mocked responses, but the one-time real consent grant happens against the user's actual
     HDFC-linked Gmail account, performed by the user directly — this cannot be done on the
     user's behalf.
  4. After the first real backfill (story B3), the user spot-checks a handful of resulting
     transactions against their own memory/bank statement, since real inbox variety can exceed
     what the three confirmed templates cover.
  5. A short demo and explicit user go-ahead is required at the end of each epic before the
     next epic begins — epics are checkpoints, not silent internal milestones.
- **Context:** The user asked directly how completed epics/stories would be verified as working
  correctly, rather than just assumed. This also surfaces a genuine constraint: some
  verification (live account consent, real-inbox correctness beyond known samples) cannot be
  self-verified and requires the user's direct involvement.
- **Alternatives considered:** Fully autonomous build-through with no checkpoints, flagging only
  clear failures — rejected; the user explicitly chose per-epic demo/sign-off over this to catch
  misunderstandings early rather than at the end of the whole backlog. A separate/throwaway
  Gmail account for initial OAuth testing before touching the real account — considered and
  rejected by the user in favor of testing directly against the real HDFC-linked account.
- **Reasoning:** Matches Constitution principle 16 (correctness first) and principle 19 (don't
  assume — ask/verify) applied to the build phase, not just the requirements phase. Splitting
  verification by story type (deterministic backend vs. UI vs. live-credential-gated) matches
  what can actually be checked by which means, rather than a one-size-fits-all testing claim.
- **Consequences:** Every epic in [BACKLOG.md](BACKLOG.md) ends with a demo/checkpoint before
  the next begins (see its "Definition of Done" section). Story B1 and B3 explicitly require
  the user's direct participation, not just review — this should be scheduled for when Epic B
  is reached, not assumed to be automatic.
