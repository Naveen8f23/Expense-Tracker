# Requirements

Status: **populated (v0.5) — ingestion scope simplified to four fixed bank/UPI email types
(ADR-0009); three of four confirmed against real HDFC samples with a sender+content
classification rule (ADR-0010, Appendix A). All open questions resolved except the pending 4th
template sample (credit card credit)** — per [CONSTITUTION.md](CONSTITUTION.md) principle 19.

## 1. Overview

- **Problem statement:** Manually logging expenses is tedious enough that most people (including
  the primary user) stop doing it within weeks. But every UPI transaction and every credit-card
  transaction already produces a fixed-format notification email from the bank/UPI provider.
  This product builds a complete, searchable financial history automatically by reading and
  structuring those four email types, so the user almost never types in a transaction by hand.
- **Target users:** A single individual (the product owner) for v1, in India, whose day-to-day
  spending is tracked via UPI and credit card. The system must be architected so that adding
  more users later (e.g. family members, or eventually other people entirely) does not require
  a rewrite — see §9 Extensibility & Multi-User Readiness.
- **Success criteria:**
  - The user can stop manually entering expenses almost entirely; manual entry becomes the
    rare exception, not the norm.
  - Every transaction in the expense history can be traced back to the source email that
    produced it.
  - The user can search/filter their spending history and get accurate summaries without
    reconciling anything by hand.
  - Extraction mistakes are easy to spot and correct, and corrections stick (don't need to be
    redone).

## 2. Users & Personas

**Primary persona — "Owner/Operator":** The product owner, who is both the sole end user and
the person maintaining the system. Comfortable with technical tools, wants low-maintenance
automation over a polished consumer UX in v1. Will personally grant Gmail OAuth access, review
flagged transactions periodically, and correct misclassifications.

**Future persona (not v1) — "Household member":** A second individual (e.g. family member)
who would connect their own Gmail account and see their own transaction history. Not built in
v1, but the data model and module boundaries must not preclude it — see §9.

## 3. Functional Requirements

### 3.1 Gmail Ingestion

| ID | Requirement |
|---|---|
| ING-1 | Connect to Gmail via OAuth 2.0; the user explicitly grants access through Google's consent screen. |
| ING-2 | Request the minimum viable OAuth scope needed to read email bodies (financial extraction needs body content, not just metadata). No send, delete, or modify scopes are requested. |
| ING-3 | **Simplified 2026-07-18 (ADR-0009):** ingestion is scoped to exactly four fixed email types — (i) UPI debit notification, (ii) UPI credit notification, (iii) credit card debit notification, (iv) credit card credit notification — which are the sole source of truth for the transaction history. No other senders — including e-commerce/food-delivery vendors (Amazon, Flipkart, Swiggy, Zomato, etc.) — are ingested at all. |
| ING-3a | **Refined 2026-07-18 (ADR-0010), based on real HDFC samples:** the sender address alone does not distinguish which of the four types an email is — for HDFC, all three known types so far (UPI debit, UPI credit, credit card debit) come from the same address, `alerts@hdfcbank.bank.in`. Classification requires a first-pass sender allow-list (is this a known bank/UPI alert address at all?) followed by a content-pattern match against fixed phrases in the body to determine the specific type. See Appendix A for the confirmed templates and their distinguishing markers. |
| ING-4 | **Resolved 2026-07-18 (ADR-0011):** the initial backfill covers from the first day of the calendar month in which the app is first set up, through the moment of setup — not a rolling window (e.g. "last 12 months") and not the user's full mailbox history. After that one-time backfill, synchronize incrementally using Gmail's History API (or equivalent): subsequent syncs only fetch changes since the last checkpoint. |
| ING-5 | Persist a per-account sync checkpoint (e.g. last `historyId` and timestamp) so a crashed or interrupted sync resumes without reprocessing everything. |
| ING-6 | Never process the same email twice: every ingested message is keyed by its immutable Gmail message ID, and re-ingestion is a no-op if that ID was already processed. |
| ING-7 | Handle Gmail API pagination and rate limits (backoff/retry) without losing sync state. |
| ING-8 | **Confirmed as a core requirement, not just a nice-to-have:** surface sync health to the user — last successful sync time, number of messages scanned/matched/skipped/failed, and any errors — so the user never wonders whether sync is silently broken. |

### 3.2 Extraction

| ID | Requirement |
|---|---|
| EXT-1 | Extract, per transaction, at minimum: amount, currency (implied by the "Rs." prefix — INR), transaction date (format differs per template — see Appendix A), transaction time when the template provides it (HDFC's credit card debit template includes time-to-the-second; its UPI templates only give a date), payee/sender name and identifier as it appears in the email (VPA + display name for UPI; a bank-assigned merchant descriptor for credit card, which may be cryptic — e.g. `ASSPL` — rather than a friendly name), the last 4 digits of the account/card instrument used, transaction type (debit / credit), payment method (exactly one of: UPI, Credit Card), and the transaction/reference number **when present** — HDFC's UPI templates include a reference number; its credit card debit template, per the sample provided, does not (see DUP-2 and Appendix A). |
| EXT-2 | Category is **user-assigned, not auto-inferred, for MVP** (see §8 resolution below) — the user picks or creates a category when reviewing a transaction. Auto-deriving a suggested category from the email content is a future idea, tracked in [ROADMAP.md](ROADMAP.md). |
| EXT-3 | **Deterministic, confirmed 2026-07-18 (ADR-0007, narrowed further by ADR-0009):** write exactly four fixed parsing rules, one per email type/sender. Since there are only four known, stable templates, this is almost entirely rule-based. AI-based extraction is used only as a fallback when a message from one of the four known senders doesn't match its expected fixed format (e.g. the bank changes its template) — and that output is always flagged for review (EXT-5) rather than trusted outright. |
| EXT-4 | Any AI-based extraction fallback must sit behind a well-defined interface (Constitution principle 10) so the underlying model/provider can change without touching the rest of the system. |
| EXT-5 | Every extracted transaction carries a confidence indicator. Low-confidence extractions (including anything that hit the AI fallback path) are flagged for user review rather than silently accepted. |
| EXT-6 | **Confirmed as a core requirement, not just a nice-to-have:** an email from one of the four known senders that doesn't parse cleanly under its fixed rule (format drift, unexpected content) is never silently dropped — it goes into the same "needs review" queue as low-confidence extractions, so nothing important goes missing without the user knowing. |
| EXT-7 | **Deferred for v1 (accepted risk, per ADR-0006):** hardening extraction against phishing emails or prompt-injection attempts embedded in email text is explicitly postponed. The user has accepted this risk for now, on the basis that this is their own personal inbox, not a shared or adversarial environment. Revisit before any multi-user or externally-exposed version. |

### 3.3 Deduplication

With ingestion narrowed to four fixed, known email types (ADR-0009), the deduplication problem
is much smaller than originally scoped — there is no more vendor-vs-bank-alert overlap to
resolve, because vendor emails are no longer ingested at all.

| ID | Requirement |
|---|---|
| DUP-1 | Detect true duplicate ingestion of the same email (e.g. a re-sync or retried fetch) via Gmail's unique message ID, and never create a second transaction record for it. |
| DUP-2 | Distinguish true duplicates from legitimately repeated transactions (e.g. two separate ₹500 UPI payments to the same person on the same day) using the transaction/reference number as the primary disambiguator — amount + payee + day alone is not sufficient. **Refined 2026-07-18:** for email types that don't include a reference number (per the sample HDFC credit card debit template — see Appendix A), fall back to the full transaction timestamp (date + time to the second, which that template does provide) combined with amount and payee as the disambiguator instead (see Edge Cases §10). |

### 3.4 Correction & Feedback

| ID | Requirement |
|---|---|
| COR-1 | The user can view, edit, and correct any extracted field on a transaction (amount, date, payee, category, payment method, type). |
| COR-2 | Corrections are durable: the same mistake should not need to be corrected twice. At minimum, a category assigned to a payee should be easy to reapply to that payee's future transactions (simple lookup, not AI). |
| COR-3 | The system keeps a record of what was originally extracted vs. what the user corrected, for traceability and for future evaluation of extraction accuracy. |
| COR-4 | The user can mark a transaction as "not a real expense" and remove it from the expense history without deleting the underlying email reference/audit trail. |
| COR-5 | The user can manually add a transaction that has no corresponding email (e.g. a cash purchase) as an explicit exception path — this should exist, but its use should be rare per the product's core goal. |

### 3.5 Traceability

| ID | Requirement |
|---|---|
| TRC-1 | Every transaction retains a reference back to the original email it was derived from (message ID at minimum). Since each of the four email types maps one-to-one to one transaction, this is always a single reference, not a list. |
| TRC-2 | The user can, from any transaction, get back to the source email content to verify the extraction. |
| TRC-3 | **Resolved 2026-07-18 (ADR-0012):** the system caches the relevant email content locally at ingestion time, rather than only storing a reference that depends on the email persisting in Gmail. Traceability (TRC-2) then works even if the user later deletes or archives the original email from Gmail. |

### 3.6 Search & History

| ID | Requirement |
|---|---|
| SRCH-1 | Search/filter the transaction history by payee, category, date range, amount range, payment method (UPI/Credit Card), transaction type (debit/credit), and free-text. |
| SRCH-2 | Results must be fast enough for interactive use even as history grows across years (see §4 Performance). |

### 3.7 Analytics & Summaries

| ID | Requirement |
|---|---|
| ANL-1 | Spending summaries by time period (daily/weekly/monthly/yearly). |
| ANL-2 | Category breakdown (spend by category, over a selected period), based on the user-assigned categories (EXT-2). |
| ANL-3 | Payee history (all transactions with a given payee/merchant; total spend per payee). |
| ANL-4 | Monthly report view combining the above into a single digestible summary. |

## 4. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Deployment model** | Local-first: the application and its data run on a single machine the user controls, per [DECISIONS.md](DECISIONS.md) ADR-0002. No multi-tenant cloud hosting in v1. **Refined 2026-07-19 (ADR-0020):** "a single machine the user controls" is now the owner's own Ubuntu VM (previously only a cross-platform test target, ADR-0017) rather than their Mac — still fully local-first (their own machine, not a third-party cloud service), running persistently as a `systemd --user` service. |
| **Primary interface** | Web dashboard (browser-based UI), served locally, per ADR-0003. A mobile app is planned for a later phase, consuming the same backend/API rather than a separate pipeline. |
| **Currency** | INR-only for MVP; every monetary value is stored with an explicit currency code so multi-currency is additive, not a rewrite, per ADR-0004. |
| **Security — credentials** | Gmail OAuth tokens are stored encrypted at rest (application-level encryption, per ADR-0015), never logged, and scoped to the minimum permission needed (read-only). Token refresh and revocation must be handled gracefully (see Edge Cases §10). |
| **Security — data at rest** | **Revised 2026-07-18 (ADR-0015):** Gmail OAuth tokens and cached raw email content — the genuinely sensitive, PII-bearing fields — are encrypted at the application level. Structured transaction fields (amount, date, payee, category) are stored unencrypted in the local SQLite file; their at-rest protection depends on file permissions and whichever OS-level disk encryption the user has enabled, not a guarantee the application itself makes. (Whole-database encryption via SQLCipher was attempted and rejected — it isn't reliably installable across the project's target platforms; see ADR-0015.) |
| **Portability (platform)** | **Added 2026-07-18:** the system must run identically on macOS (development) and Ubuntu (the actual deployment target, an Ubuntu VM) — no platform-specific dependencies, paths, or scripts (ADR-0015). |
| **Security — AI processing** | Since extraction is now deterministic-first with AI only as a rare format-drift fallback (ADR-0007, ADR-0009), the privacy exposure of AI processing is now limited to a small, occasional slice of emails rather than the whole pipeline. Whether that rare fallback calls a cloud API or a local model is a smaller follow-up decision, not blocking. |
| **Privacy** | No financial data is shared with any third party beyond what's strictly required for the rare AI fallback (see above), and never for advertising, analytics, or resale purposes. |
| **Reliability / idempotency** | Sync and extraction must be safely re-runnable: crashes, retries, or re-running the same sync window must never duplicate transactions (ties to ING-6, DUP-1). |
| **Performance** | Search and summary views should feel instant (sub-second) for a single-user history up to tens of thousands of transactions. Full historical backfill may run in the background and does not need to be instant. |
| **Extensibility / modularity** | Plug-and-play, non-monolithic design: ingestion source (Gmail today), extraction engine, deduplication, categorization, storage, and analytics are separable modules behind clear interfaces, so e.g. a new ingestion source can be added without modifying existing modules. See [ARCHITECTURE.md](ARCHITECTURE.md). |
| **Multi-user readiness** | Every record in the data model is scoped to a user/account from day one, even though only one user exists in v1 (see §9). |
| **Portability** | Web dashboard should work in a current evergreen browser (Chrome/Firefox/Safari, desktop). |
| **Accessibility** | Baseline accessibility (readable contrast, keyboard navigation for core flows) — no formal WCAG target set for v1. |
| **Data retention** | The user can export their full transaction history and can delete individual transactions or the entire dataset. Underlying cached email content (cached at ingestion time, per TRC-3/ADR-0012) follows the same deletion guarantees. |

## 5. Data Model (high level)

Details belong in [ARCHITECTURE.md](ARCHITECTURE.md); this section captures only the entities
the domain requires and why.

- **User** — even in a single-user v1, transactions and connections are owned by a user record, not implicit globals (multi-user readiness).
- **GmailConnection** — OAuth credentials/tokens and connection metadata for one Gmail account, owned by a User.
- **SenderRule** — **refined 2026-07-18 (ADR-0010):** not a simple 1:1 sender→type mapping. Each rule pairs a sender address (e.g. `alerts@hdfcbank.bank.in`) with a content-matching pattern that identifies one of the four transaction types, since one sender address can host more than one email template (confirmed with HDFC: the same address sends UPI debit, UPI credit, and credit card debit notifications, distinguished only by body content — see Appendix A).
- **EmailMessage** — a reference to (and optionally cached content of) a source email: Gmail message ID, thread ID, received timestamp, processing status (unprocessed / matched / needs-review / ignored), and a pointer to the one Transaction it produced, if any.
- **SyncState** — per-GmailConnection checkpoint (last historyId, last sync time, last error) enabling incremental, resumable sync.
- **Transaction** — the core record: amount, currency, transaction date, transaction time (nullable — not every template provides it), payee/merchant name, instrument last-4-digits, category, payment method (UPI/Credit Card), type (debit/credit), reference number (nullable — not every template provides it), confidence score, review status, and a link to its one contributing EmailMessage.
- **Payee** (formerly "Merchant") — the payee/merchant name as it appears in the bank/UPI email. Alias normalization across apps (e.g. the same person paying via different UPI apps showing slightly different names) is a deferred improvement (§11), not built now.
- **Category** — entirely user-defined for MVP (no fixed system list); each Transaction has one Category, freely created/renamed by the user.
- **CorrectionLog** — records of what was originally extracted vs. what a user corrected (COR-3).
- **Budget** — deferred to a later phase (§12), but noted here because it will attach to Category and time period once built.

## 6. Constraints

- Built and run by one person, for one person, initially — operational simplicity matters more
  than horizontal scalability in v1.
- Depends on Gmail's API (quotas, history retention limits — a sync gap longer than Gmail's
  History API retention window requires falling back to a bounded re-scan; an implementation
  detail for ARCHITECTURE.md, not a product requirement).
- Depends on a small set of sender addresses (currently one, `alerts@hdfcbank.bank.in`, hosting
  three of the four types) plus their content-matching patterns being correctly identified and
  stable — if the bank changes the sending address or the wording of a notification type, the
  relevant `SenderRule` needs to be updated (see Edge Cases §10).
- No dedicated budget assumed for a paid third-party AI API for the rare extraction fallback.

## 7. Assumptions (confirmed 2026-07-18, updated with the ingestion-scope change)

1. **Single Gmail account** is the only ingestion source for v1.
2. **Financial emails arrive directly** in this Gmail account's inbox/archive — not forwarded
   from another account, and not auto-deleted by an existing mail filter before this system can
   read them.
3. **English-language emails** are the norm — no dedicated multi-language extraction support
   assumed for v1.
4. **Both expenses and income/credits are tracked** — this maps directly onto the four email
   types (two are debit, two are credit).
5. **A single logical "wallet"** is fine for v1 — the system records the payment method (UPI or
   Credit Card) per transaction, but does not model multiple bank accounts as separate ledgers
   with running balances.
6. **The user will periodically review a "needs review" queue** rather than expecting 100%
   unattended accuracy.
7. **Resolved 2026-07-18 (ADR-0011):** the initial backfill is not a rolling historical window
   (e.g. "last 12 months") — it starts from the **first day of the calendar month in which the
   application is first set up and run**. There is no deep historical import of past years'
   transactions; the tracker's history effectively begins at the start of that month. (This
   also means the "very large historical backfill" concern in Edge Cases §10 is much less of a
   risk in practice — at most, a few weeks of email to scan on day one.)
8. **The user does not require real-time (sub-minute) transaction detection** — periodic
   polling sync is acceptable, since Gmail push notifications would require a publicly
   reachable endpoint, in tension with the local-first deployment model.
   **Refined 2026-07-19 (ADR-0019):** this remains true as a *requirement* (nothing here demands
   sub-minute detection), but the owner asked for automatic background sync with a fast poll
   interval anyway, wanting a push-notification-like feel without a manual sync action. Built as
   a 5-second local poll (`SyncScheduler`) + browser notifications while the dashboard tab is
   open — comfortably within this assumption's spirit (still polling, still local-first, no
   public endpoint), just faster than the minimum this assumption requires.
9. **Confirmed 2026-07-18:** these four email types capture the large majority of the user's
   spending. A small, occasional residue (e.g. cash purchases) falls outside this scope and is
   accepted as a known, minor gap — not something the system needs to solve for. Covered by
   the existing manual "add a transaction" escape hatch (COR-5), not a dedicated feature.
10. **Confirmed 2026-07-18:** HDFC Bank is, for now, the user's sole bank/card issuer — all of
    the user's tracked transactions are assumed to flow through the one HDFC sender/template set
    (Appendix A). If the user opens an account or card with another bank in the future,
    that bank's own sender address and templates would need to be added as additional
    `SenderRule`s — the design must not hardcode "HDFC" as the only possible bank (see §9
    Extensibility).
11. **Confirmed 2026-07-18:** "credit card credit" primarily means a merchant refund credited
    back to the card — not a bill-payment/repayment confirmation (paying off the card balance
    from a bank account). This matters because a bill-payment credit would not be new
    income/spend and would need to be excluded from analytics to avoid inflating totals; since
    the user's primary case is merchant refunds, this is not expected to be a real concern for
    now. If a bill-payment-confirmation email is ever encountered with different wording, it
    won't match the confirmed "credit card credit" content pattern and will fall to the
    needs-review queue (EXT-6) rather than being silently miscounted.

## 8. Open Questions

Only one item remains open:

- [ ] **The credit card credit (4th) template sample hasn't been provided yet** — three of the
  four templates are confirmed (Appendix A); the fourth (money credited/refunded to a credit
  card) is still pending from the user. Its parsing rule can't be finalized until then.

Resolved and removed from this list since the last revision:
- ~~Category taxonomy ownership~~ — resolved: fully user-defined/freeform for MVP; auto-suggestion from email content is a future idea (see [ROADMAP.md](ROADMAP.md)).
- ~~Cancelled/failed transaction handling~~ — resolved: not applicable. There is no "order" concept anymore — only confirmed bank/UPI debits and credits are ever ingested, so a failed/cancelled order (which never reaches settlement) has no corresponding email to ingest in the first place.
- ~~Historical backfill window~~ — resolved (Assumption §7.7, ADR-0011): backfill starts from the first day of the calendar month the app is first set up in, not a rolling historical window.
- ~~Email content caching~~ — resolved (ADR-0012): the system caches source email content locally at ingestion time, so traceability (TRC-3) doesn't depend on the email still existing in Gmail later.
- ~~Export/API need~~ — resolved: no near-term need; the web dashboard is sufficient for now. The API-boundary discipline behind the dashboard (ADR-0003) still applies so a future mobile app remains a clean additional client, not a rebuild.
- ~~Bank/card issuer scope~~ — resolved (Assumption §7.10): HDFC is the sole bank/card issuer for now.
- ~~Credit card credit semantics~~ — resolved (Assumption §7.11): primarily means a merchant refund, not a bill-payment/repayment confirmation.
- ~~Sender allow-list / vendor scope~~ — resolved and superseded: replaced entirely by the four fixed sender addresses (ADR-0009).
- ~~AI extraction approach~~ — resolved (ADR-0007, ADR-0009): deterministic-first, four fixed rules, AI only as a rare fallback.
- ~~Spending coverage gap~~ — resolved (Assumption §7.9): the four email types capture the large majority of spend; small/occasional exceptions (e.g. cash) are an accepted, minor gap covered by the manual add-transaction escape hatch (COR-5).
- ~~Bank-alert double counting~~ — resolved and moot: no longer applicable since vendor emails aren't ingested at all.

## 9. Extensibility & Multi-User Readiness

Not a v1 feature, but a constraint on how v1 is designed:

- All data is owned by a `User` record from day one; nothing is a bare global.
- The Gmail connector is one implementation of an "ingestion source" concept — the module
  boundary should not assume Gmail-specific details leak into extraction, dedup, storage, or
  analytics. The four-sender-rule approach (ADR-0009/ADR-0010) is itself a form of
  configuration this ingestion source module should expose cleanly, not hardcode.
- **HDFC is the only configured bank for now (Assumption §7.10), but the `SenderRule` design
  must not hardcode HDFC-specific assumptions.** Adding a second bank later should mean adding
  more `SenderRule` entries (a new sender address + content patterns), not restructuring the
  ingestion or extraction modules.
- The extraction engine's interface is the same regardless of whether a fixed rule or an AI
  fallback produced the output — callers don't need to know which.
- **Confirmed 2026-07-18:** no export/API is being built now (the web dashboard is sufficient),
  but a future mobile app is expected to be an additional client of the same backend/API that
  the web dashboard uses (ADR-0003) — so whatever backend/API shape is designed for the
  dashboard must genuinely be reusable by a mobile client later, not something that needs
  reworking once the mobile app is actually built.
- Multi-user support later means adding authentication/authorization and per-user data
  isolation at the API boundary — it should not require redesigning Transaction, Payee, or
  Category shapes, because they are already user-scoped.

## 10. Edge Cases

**Ingestion**
- Gmail access is revoked or the OAuth token expires and refresh fails — sync must fail
  visibly (ING-8), not silently stop.
- A sync is interrupted mid-run (crash, network loss) — must resume from the last checkpoint
  (ING-5).
- A gap between syncs exceeds Gmail's History API retention window — must detect this and fall
  back to a bounded re-scan rather than fail silently.
- **The bank/UPI provider changes the sending address** for one of the four notification types
  (e.g. after a system migration) — the existing `SenderRule` would stop matching new emails.
  This needs to be noticeable (via ING-8 sync health, e.g. a sudden drop in matched emails)
  rather than silently missed.
- **One sender address hosts multiple email types** — confirmed with HDFC (`alerts@hdfcbank.bank.in`
  sends UPI debit, UPI credit, and credit card debit notifications). Filtering by sender alone
  is not enough; the content-pattern match (Appendix A) that distinguishes the type must run on
  every email from that sender, and must fail safely (→ needs-review, EXT-6) rather than
  guessing if none of the known patterns match.
- **HDFC's alert emails are HTML with promotional images/branding around the transactional
  text** — confirmed from the samples: the amount, date, and reference number are plain text
  within the HTML body, not embedded in an image. This validates the earlier decision not to
  build a dedicated OCR pipeline (at least for this sender) — extraction just needs to parse
  past marketing boilerplate to the relevant sentence(s).
  - **Refined 2026-07-19, from the user's own live transaction spot-check (a real, if small,
    amount and debit/credit type each — per ADR-0014's "user verifies real results" step):**
    "plain text" doesn't mean "unformatted." The real credit card debit template wraps its
    merchant name, amount, card-ending digits, and date/time in `<b>...</b>` tags — a detail
    lost when Appendix A's samples were transcribed as plain-text quotes. Extraction regexes
    must tolerate arbitrary HTML tags between an anchor phrase and its value, not just
    whitespace (fixed; see [DECISIONS.md](DECISIONS.md)/[CHANGELOG.md](CHANGELOG.md)).
  - **Also discovered the same day:** HDFC sends a fifth, distinct notification — "Credit Card
    Payment done using HDFC Bank Online Banking" (paying the card bill via net banking) — with
    wording that matches none of the four confirmed templates. This is exactly the
    bill-payment/repayment scenario Assumption 11 (§7) anticipated: it correctly falls to
    needs-review (EXT-6) rather than being counted as a transaction, and is *not* added as a
    fifth `SenderRule` — paying your own card bill isn't new spend or income.
- ~~Very large historical backfill (years of email)~~ — **largely moot per ADR-0011:** the
  initial backfill only covers from the start of the current calendar month, so this is at most
  a few weeks of email on day one, not years. Revisit only if the user later chooses to run a
  deeper, explicit backfill.

**Extraction**
- One email contains multiple line-item transactions (e.g. a periodic account/card statement
  summary, as opposed to a single-transaction alert) — if such an email ever matches one of the
  four sender addresses, it must not be misread as a single transaction; needs a rule to detect
  and either split it or exclude it, since the four sender rules are meant to target
  single-transaction alerts specifically.
- A transaction is a foreign-currency charge converted to INR by the card issuer, with two
  amounts present (original + converted) in the same email.
- The bank/UPI provider changes its email template over time — older emails must not silently
  stop matching just because a newer template exists later (ties to the ingestion edge case
  above).
- A malicious or phishing email mimics a real bank alert — **deferred / accepted risk for v1
  per ADR-0006** (EXT-7).
- Pending/authorization-hold notifications vs. actual settled charges for the same credit-card
  purchase — must not be double-counted as two transactions if both happen to arrive as
  separate emails from the same sender address.
- **Credit-card merchant descriptors can be cryptic, abbreviated codes** rather than a
  recognizable name — confirmed from the sample: a real HDFC credit card debit alert shows the
  payee as `ASSPL`, not a human-readable merchant name. Left as-is for MVP; the user can rename
  or annotate it via correction (COR-1), and a personal payee-alias mapping is a deferred idea
  (§11) if this becomes a recurring annoyance.
- **Date and time format/granularity differ per template** — confirmed from the samples: HDFC's
  UPI templates give a date only, in `DD-MM-YY` form (e.g. `18-07-26`); its credit card debit
  template gives a full date and time to the second, in a different format (e.g.
  `18 Jul, 2026 at 18:56:45`). Each template's parsing rule must handle its own format; these
  must not be assumed to be interchangeable.

**Deduplication**
- The same email is fetched twice across two sync runs (e.g. a retried request) — solved simply
  by keying on Gmail's unique message ID (ING-6, DUP-1) — no content-based matching needed.
- Two genuinely separate transactions share amount, payee, and day (e.g. two ₹500 UPI payments
  to the same person on the same day) — must not be incorrectly merged; the transaction
  reference number is the disambiguator (DUP-2).

**Correction & Traceability**
- The user deletes or archives the source email in Gmail after it's been ingested —
  traceability must still work if content was cached, or must degrade gracefully if only a
  reference was kept (see Open Questions §8).
- The user corrects a payee's category — must apply going forward without requiring the same
  correction repeatedly (COR-2).
- The user marks something "not a real expense" — it should disappear from analytics/search by
  default but remain in an audit trail, not be hard-deleted.

**Analytics**
- Transaction date (from the email body) vs. email received date (from the mail header) can
  differ near a month/day boundary — monthly reports must be consistent about which date they
  bucket by.
- A shared Gmail inbox has transactions from more than one person mixed together — out of
  scope for v1; flagged as a known limitation rather than pretend it's handled.

## 11. Suggested Improvements (beyond the original ask) — deferred

**Status: not needed for now, per user decision.** Kept here as a reference list to revisit
post-MVP, not as active scope.

- **Payee normalization & enrichment** — collapse minor formatting variants of the same payee
  name into one canonical Payee, so payee history (ANL-3) is accurate rather than fragmented.
- **Confidence-scored review queue** — rank the "needs review" queue so review time goes where
  it matters most (partially superseded by EXT-5/EXT-6 now being core requirements — revisit
  whether ranking specifically is still worth adding later).
- **Auto-suggested categories from email content** — the user's own idea for a future
  iteration (see [ROADMAP.md](ROADMAP.md)); category assignment is fully manual for MVP.
- **Export for personal backup** — a simple CSV/JSON export of the full transaction history.
- **Encrypted local storage** — already required under §4 NFR Security, listed here only for
  historical reference to the original suggestion.

## 12. Deferred / Postponed Features

Explicitly out of scope for the MVP (§13), to revisit later. Listed here (not deleted) so
they're not forgotten and don't silently creep into v1 scope.

- **Vendor-level tracking (Amazon, Flipkart, Swiggy, Zomato, Uber, Ola order emails)** —
  superseded by ADR-0009, not merely deferred. May be reconsidered in the future only if the
  four-email approach proves insufficient (e.g. to get itemized purchase detail the bank/UPI
  email doesn't include), but is not on the roadmap by default.
- Multi-user / multi-tenant support (design allows for it; not built now).
- Mobile app (planned next after the web dashboard + pipeline are proven — see
  [ROADMAP.md](ROADMAP.md)).
- Multi-currency conversion and mixed-currency transaction handling.
- Budget tracking and budget alerts.
- Shared/family expense splitting and multi-person attribution.
- Additional ingestion sources beyond Gmail (SMS, bank statement PDF/CSV upload, other mail
  providers, debit card / net banking / wallet notifications — pending the answer to Open
  Question §8 on spending coverage).
- Notifications/alerts via push, SMS, or email (in-app "needs review" surfacing is sufficient
  for v1).
- Spending forecasts, anomaly detection, or other advanced analytics beyond §3.7.
- Items in §11 Suggested Improvements not already folded into core requirements.
- Defending extraction against phishing/prompt-injection attempts in email content (EXT-7) —
  explicitly accepted as a risk for v1 (ADR-0006).

## 13. MVP Definition

The smallest version that delivers on the core goal — "rarely, if ever, manually enter
expenses" — end to end, for one user, one Gmail account:

1. Connect one Gmail account via OAuth (read-only) (ING-1, ING-2).
2. Configure `SenderRule`s for the four transaction types (sender address + content-matching
   pattern per type — see Appendix A; three of four confirmed, one pending).
3. Run the initial backfill from the start of the current calendar month (ADR-0011), then sync
   incrementally on a schedule, matching only configured senders and classifying each match by
   content pattern (ING-3, ING-3a, ING-4–ING-8).
4. Extract structured transactions using four fixed parsing rules, one per email type, with an
   AI fallback only for the rare format-drift case, always flagged for review (EXT-1–EXT-7).
5. Avoid duplicate records via Gmail message ID and reference-number disambiguation (DUP-1,
   DUP-2).
6. Store every transaction with a traceable link back to its source email (TRC-1, TRC-2).
7. Web dashboard providing: a searchable/filterable transaction list (SRCH-1), a correction UI
   including manual category creation/assignment (COR-1–COR-5), a "needs review" queue for
   both low-confidence and unrecognized-format emails (EXT-5, EXT-6), a sync health panel
   (ING-8), and basic analytics — monthly summary and category breakdown (ANL-1, ANL-2, ANL-4).
8. Manual "add a transaction" as an escape hatch, not a primary flow (COR-5).
9. Local-first deployment with encrypted storage of tokens and data (NFR: Security).

Explicitly **not** in MVP: vendor-level tracking, multi-user, mobile app, multi-currency,
budgets, notifications, additional ingestion sources — all listed in §12.

## 14. Glossary

- **Ingestion** — the process of connecting to and pulling raw emails from Gmail.
- **Extraction** — turning a raw email into structured transaction fields.
- **Backfill** — the initial, potentially large, one-time sync of historical email.
- **Incremental sync** — fetching only what changed since the last checkpoint.
- **SenderRule** — a configured pairing of a sender email address and a content-matching
  pattern that together identify one of the four recognized transaction email types. One
  sender address can host more than one type (confirmed with HDFC — see Appendix A).
- **Deduplication (dedup)** — ensuring the same real-world transaction is never recorded twice.
- **Confidence score** — a measure of how certain the extraction pipeline is about a given
  transaction's fields, used to decide whether it needs human review.
- **Needs-review queue** — the set of transactions flagged for manual confirmation due to low
  confidence or an unrecognized/format-drifted email.
- **Local-first** — the application and its data reside on a machine the user controls.
- **Plug-and-play module** — a component (ingestion source, extraction engine, etc.) that
  implements a defined interface and can be swapped or extended without changes to other
  modules.

## Appendix A: Known Email Templates (reference)

Confirmed 2026-07-18, from real samples provided by the user. These are the concrete templates
the extraction module's fixed parsing rules (EXT-3) must handle. Three of four are confirmed;
the fourth (credit card credit) is still pending (see Open Questions §8).

**Shared sender for all HDFC templates below:** `alerts@hdfcbank.bank.in` — sender address
alone does not distinguish type; see the "Distinguishing marker" row for each.

### A.1 UPI Debit

> Dear Customer,
>
> Greetings from HDFC Bank!
>
> Rs.120.00 is debited from your account ending 4958 towards VPA vyapar.171813527289@hdfcbank (GOLKONDAS CAFE) on 18-07-26.
>
> UPI transaction reference no.: 126479299557.
>
> If you did not authorize this transaction, please report it immediately at: ...

| Field | Value in sample | Notes |
|---|---|---|
| Amount | 120.00 | Prefixed `Rs.`, no space before the number |
| Type | Debit | |
| Payment method | UPI | |
| Instrument | Account ending 4958 | |
| Payee VPA | vyapar.171813527289@hdfcbank | |
| Payee display name | GOLKONDAS CAFE | In parentheses after the VPA |
| Date | 18-07-26 | `DD-MM-YY`, no time given |
| Reference no. | 126479299557 | Present |
| Distinguishing marker | `"is debited from your account ending"` + `"towards VPA"` | |

### A.2 UPI Credit

> Dear Customer,
>
> Greetings from HDFC Bank!
>
> We're writing to inform you that Rs.10.00 has been successfully credited to your HDFC Bank account ending in 4958.
>
> Transaction Details:
> a. Date: 18-07-26
> b. Sender: NAVEEN V (VPA: naveen8f23@oksbi)
> c. UPI Reference No.: 619901283303
>
> Need Help? ...

| Field | Value in sample | Notes |
|---|---|---|
| Amount | 10.00 | |
| Type | Credit | |
| Payment method | UPI | |
| Instrument | Account ending 4958 | |
| Sender/payer name | NAVEEN V | |
| Sender VPA | naveen8f23@oksbi | |
| Date | 18-07-26 | Same `DD-MM-YY` format as A.1, but in a lettered "Transaction Details" list rather than inline prose |
| Reference no. | 619901283303 | Labeled "UPI Reference No." (capitalization differs slightly from A.1's "reference no.") |
| Distinguishing marker | `"has been successfully credited to your HDFC Bank account"` | Different sentence structure from A.1 despite same sender |

### A.3 Credit Card Debit

> Dear Customer,
>
> Greetings from HDFC Bank.
>
> We would like to inform you that Rs. 554.00 has been debited from your HDFC Bank Credit Card ending 2174 towards ASSPL on 18 Jul, 2026 at 18:56:45.
>
> To check your available balance ...

| Field | Value in sample | Notes |
|---|---|---|
| Amount | 554.00 | Note the space after `Rs.` here, unlike A.1/A.2 — parsing must not assume a fixed spacing |
| Type | Debit | |
| Payment method | Credit Card | |
| Instrument | Card ending 2174 | |
| Payee | ASSPL | Cryptic merchant descriptor, not a friendly name (see Edge Cases §10) |
| Date & time | 18 Jul, 2026 at 18:56:45 | Different format from UPI templates, and includes time to the second |
| Reference no. | **Not present in this sample** | Dedup must fall back to timestamp + amount + payee (DUP-2) |
| Distinguishing marker | `"has been debited from your HDFC Bank Credit Card ending"` | |

### A.4 Credit Card Credit — pending

Not yet provided by the user. Expected to be structurally similar to A.3 but for a credit
(e.g. a refund or payment received on the card). Do not guess its wording — the parsing rule
for this type is blocked on getting a real sample.

---
_Revision history: track major changes to requirements in [CHANGELOG.md](CHANGELOG.md) and,
if the change reflects a deliberate tradeoff, in [DECISIONS.md](DECISIONS.md)._
