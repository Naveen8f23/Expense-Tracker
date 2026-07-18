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
- **Status:** Planned
- **Target:** TBD
- **Goal:** Reliably and securely connect to Gmail and pull in exactly the four configured
  bank/UPI notification email types, without processing anything twice.
- **Requirements covered:** REQUIREMENTS.md §3.1 (Gmail Ingestion, incl. `SenderRule`
  configuration per ADR-0009), relevant NFRs (security — credentials, reliability/idempotency).
- **Success criteria:** A connected Gmail account can be backfilled and then kept in sync
  incrementally against the four configured senders, with sync health visible to the user
  (ING-8).
- **Dependencies:** M1. Needs the four sample emails and sender addresses from the user before
  the `SenderRule` parsing logic can be designed in detail.

### M3: Extraction & Deduplication
- **Status:** Planned
- **Target:** TBD
- **Goal:** Turn the four matched email types into accurate, deduplicated, structured
  transactions using fixed per-type parsing rules.
- **Requirements covered:** REQUIREMENTS.md §3.2 (Extraction), §3.3 (Deduplication).
- **Success criteria:** Each of the four email types extracts correctly via its fixed rule, or
  is flagged for review rather than silently wrong (EXT-6); no duplicate or double-counted
  transactions (DUP-1, DUP-2).
- **Dependencies:** M2.

### M4: Review, Correction & Traceability
- **Status:** Planned
- **Target:** TBD
- **Goal:** Let the user see, correct, and trust the extracted data, with every transaction
  traceable to its source email.
- **Requirements covered:** REQUIREMENTS.md §3.4 (Correction & Feedback), §3.5 (Traceability).
- **Success criteria:** Corrections are one-time (don't recur for the same merchant); every
  transaction links back to its source email(s).
- **Dependencies:** M3.

### M5: Search, History & Core Analytics (MVP Complete)
- **Status:** Planned
- **Target:** TBD
- **Goal:** Deliver the searchable expense history and the baseline summaries/analytics that
  complete the MVP as defined in REQUIREMENTS.md §13.
- **Requirements covered:** REQUIREMENTS.md §3.6 (Search & History), §3.7 (Analytics &
  Summaries).
- **Success criteria:** MVP definition (REQUIREMENTS.md §13) fully met end-to-end for one
  Gmail account.
- **Dependencies:** M2–M4.

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
- **Status:** Planned
- **Target:** TBD
- **Goal:** Ship a mobile app as an additional client of the existing backend/API (per
  [DECISIONS.md](DECISIONS.md) ADR-0003), once the web dashboard and underlying pipeline are
  proven in real use.
- **Requirements covered:** Same functional requirements as the web dashboard, delivered on a
  new client surface.
- **Success criteria:** Core flows (review/correct transactions, search, view summaries)
  available on mobile without changes to ingestion/extraction.
- **Dependencies:** M5, and in practice some real-world usage time on the web dashboard first.

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
