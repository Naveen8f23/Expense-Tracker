# Roadmap

Status: **populated — milestones defined through MVP and beyond.**

This document tracks planned milestones at a high level. It is not a task tracker — the
detailed, day-to-day story breakdown for M2–M5 lives in [BACKLOG.md](BACKLOG.md); this file
captures only the shape and sequencing of major phases.

## How to use this file

- Each milestone should be small enough to ship and evaluate independently.
- A milestone moves from "Planned" to "In Progress" to "Done" — update status here as it
  changes.
- When a milestone's scope changes materially, note it in [CHANGELOG.md](CHANGELOG.md).
- Milestones should trace back to requirements in [REQUIREMENTS.md](REQUIREMENTS.md).

## Milestone Template

Copy this block per milestone:

```
### M_: <Milestone Name>
- **Status:** Planned | In Progress | Done
- **Target:** <date or "TBD">
- **Goal:** <one-sentence outcome>
- **Requirements covered:** <links to REQUIREMENTS.md sections>
- **Success criteria:** <how we know it's done>
- **Dependencies:** <what must exist first>
```

## Milestones

### M0: Engineering Foundation
- **Status:** Done
- **Target:** 2026-07-18
- **Goal:** Establish governing docs (`CONSTITUTION.md`, `REQUIREMENTS.md`, `ARCHITECTURE.md`,
  `ROADMAP.md`, `DECISIONS.md`, `CHANGELOG.md`) before any application code is written.
- **Requirements covered:** N/A (process milestone)
- **Success criteria:** All six docs exist under `/docs` and are reviewed.
- **Dependencies:** None.

### M1: Product Specification
- **Status:** Done
- **Target:** 2026-07-18
- **Goal:** Define the full product requirements, assumptions, edge cases, and MVP scope for
  the Gmail-driven expense tracker before any implementation or technology choice.
- **Requirements covered:** `REQUIREMENTS.md` v0.1 (all sections).
- **Success criteria:** Requirements populated; blocking open questions identified (notably:
  AI-extraction privacy model — see `REQUIREMENTS.md` §8); MVP definition agreed.
- **Dependencies:** M0.

### M2: Ingestion Foundation
- **Status:** Done
- **Target:** 2026-07-18
- **Goal:** Reliably and securely connect to Gmail and pull in exactly the four configured
  bank/UPI notification email types, without processing anything twice.
- **Requirements covered:** REQUIREMENTS.md §3.1 (Gmail Ingestion, incl. `SenderRule`
  configuration per ADR-0009), relevant NFRs (security — credentials, reliability/idempotency).
- **Success criteria:** A connected Gmail account can be backfilled and then kept in sync
  incrementally against the four configured senders, with sync health visible to the user
  (ING-8). Met via BACKLOG.md Epic B (B1–B5), verified against the owner's real Gmail account —
  note only 3 of the 4 templates are seeded (`SenderRule`) so far, since the 4th (credit card
  credit) sample is still pending (REQUIREMENTS.md §8).
- **Dependencies:** M1. Needs the four sample emails and sender addresses from the user before
  the `SenderRule` parsing logic can be designed in detail.

### M3: Extraction & Deduplication
- **Status:** In Progress
- **Target:** TBD
- **Goal:** Turn the four matched email types into accurate, deduplicated, structured
  transactions using fixed per-type parsing rules.
- **Requirements covered:** REQUIREMENTS.md §3.2 (Extraction), §3.3 (Deduplication).
- **Success criteria:** Each of the four email types extracts correctly via its fixed rule, or
  is flagged for review rather than silently wrong (EXT-6); no duplicate or double-counted
  transactions (DUP-1, DUP-2).
- **Dependencies:** M2. **Progress (2026-07-19):** both halves are now done. Extraction (Epic C,
  C1–C8) — three of the four templates classify and extract correctly (the fourth, credit card
  credit, is still blocked on a real sample, REQUIREMENTS.md §8); needs-review routing (EXT-6)
  and the AI-fallback seam are in place. Deduplication (Epic D, DUP-1/DUP-2) — both guarantees
  turned out to already be structural (unique constraints + status-gated reprocessing), confirmed
  by tests rather than new code. **M3 is effectively complete for the three confirmed templates**;
  fully closing it out is blocked only on the pending 4th template sample.

### M4: Review, Correction & Traceability
- **Status:** Done
- **Target:** 2026-07-19
- **Goal:** Let the user see, correct, and trust the extracted data, with every transaction
  traceable to its source email.
- **Requirements covered:** REQUIREMENTS.md §3.4 (Correction & Feedback), §3.5 (Traceability).
- **Success criteria:** Corrections are one-time (don't recur for the same merchant); every
  transaction links back to its source email(s).
- **Dependencies:** M3. **Completed 2026-07-19:** BACKLOG.md Epics E (API) and F (dashboard) both
  done. The user can now actually see, edit, dismiss, and categorize a transaction, and view its
  source email, through the real dashboard — verified by driving it directly (browser
  automation), not just at the API-contract level. One-time corrections (COR-2) confirmed
  end-to-end: assigning a category to a payee via the dashboard is remembered and applied to that
  payee's next new transaction automatically.

### M5: Search, History & Core Analytics (MVP Complete)
- **Status:** Done
- **Target:** 2026-07-19
- **Goal:** Deliver the searchable expense history and the baseline summaries/analytics that
  complete the MVP as defined in REQUIREMENTS.md §13.
- **Requirements covered:** REQUIREMENTS.md §3.6 (Search & History), §3.7 (Analytics &
  Summaries).
- **Success criteria:** MVP definition (REQUIREMENTS.md §13) fully met end-to-end for one
  Gmail account.
- **Dependencies:** M2–M4. **Completed 2026-07-19:** BACKLOG.md Epic G (G1–G4) done — monthly
  summary, category breakdown, and payee history are live on the dashboard, plus search/filter
  UI polish (debounce, clear-all, active-filter chips). This is the last epic REQUIREMENTS.md
  §13 lists, so the MVP is now fully met **except** the still-pending 4th email template
  (credit card credit — REQUIREMENTS.md §8), which was never an M5 dependency and remains the
  one open item blocking a fully-complete Appendix A.

### M6: Post-MVP Enhancements
- **Status:** Planned
- **Target:** TBD
- **Goal:** Revisit the deferred features (REQUIREMENTS.md §12) once the core pipeline is
  proven in daily use. Candidates include:
  - **Auto-suggested categories from email content** — the user's own idea, raised during
    spec work: find a way to derive/suggest a transaction's category directly from the
    payee/email content instead of always requiring manual assignment (REQUIREMENTS.md EXT-2).
  - Budget tracking, richer analytics, export/backup.
  - Reconsidering vendor-level detail (e.g. itemized purchase contents) if the four-email
    bank/UPI approach ever proves insufficient (REQUIREMENTS.md §12).
  Exact sequencing to be decided closer to M5 completion.
- **Requirements covered:** Selected items from REQUIREMENTS.md §12, to be re-scoped at the
  time.
- **Success criteria:** TBD per selected feature.
- **Dependencies:** M5.

### M7: Mobile App
- **Status:** In Progress (2026-07-19)
- **Target:** TBD
- **Goal:** Ship "Ledger," an iOS app, as an additional client of the existing backend/API (per
  [DECISIONS.md](DECISIONS.md) ADR-0003), once the web dashboard and underlying pipeline are
  proven in real use.
- **Requirements covered:** REQUIREMENTS.md §15 (MOB-1 through MOB-6) — same functional
  requirements as the web dashboard, delivered on a new client surface, plus a new
  in-app-notification requirement (MOB-4) the web dashboard doesn't have in quite the same form.
- **Success criteria:** Core flows (review/correct transactions, search, view summaries, manual
  add) available on iOS without changes to ingestion/extraction; a new-transaction notification
  arrives while the app is open, per ADR-0024's accepted scope.
- **Dependencies:** M5 (done). **Decided 2026-07-19:** a visual design concept was reviewed and
  confirmed by the owner; native Swift + SwiftUI was chosen over a cross-platform framework
  (ADR-0023); push notifications will be in-app/foreground-only, not Apple Push and not a
  third-party relay, after both were presented and declined (ADR-0024). Detailed story breakdown
  in [BACKLOG.md](BACKLOG.md) Epics I–M. **Progress (2026-07-19):** Epics I (foundation), J
  (transaction list & correction, J1-J7), K (needs-review queue, K1-K4), and L (analytics, L1-L3)
  all done. Epic M (manual add & notifications) not started.

### M8: Multi-User Support
- **Status:** Planned
- **Target:** TBD
- **Goal:** Extend from a single owner-operator to multiple independent users, per the
  multi-user readiness constraint in REQUIREMENTS.md §9.
- **Requirements covered:** Authentication/authorization, per-user data isolation; no change
  expected to the shape of Transaction/Merchant/Category.
- **Success criteria:** A second user can connect their own Gmail account and get their own
  isolated history, dashboard, and analytics.
- **Dependencies:** M5; likely reopens the deployment-model decision (ADR-0002).

---
_This roadmap lists milestones only — no implementation tasks. Each milestone should be broken
into concrete work in whatever issue tracker is adopted once implementation begins._
