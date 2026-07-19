"""GetNeedsReviewQueue use case (BACKLOG.md E5; REQUIREMENTS.md EXT-5, EXT-6).

Combines the two distinct needs-review concepts in this system: an `EmailMessage` that never
became a transaction at all (no known pattern matched, or a matched pattern failed to extract --
C7), and a `Transaction` that a low-confidence AI fallback produced but that was never
auto-accepted (EXT-4/EXT-5). The dashboard (Epic F) needs both to build one review screen.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.application.run_classify_and_extract import get_needs_review_emails
from app.infrastructure.models import EmailMessage, ReviewStatus, Transaction, User


@dataclass
class NeedsReviewQueue:
    unmatched_emails: list[EmailMessage]
    low_confidence_transactions: list[Transaction]


def get_needs_review_queue(session: Session, user: User) -> NeedsReviewQueue:
    unmatched_emails = get_needs_review_emails(session)
    low_confidence_transactions = (
        session.query(Transaction)
        .filter(
            Transaction.user_id == user.id,
            Transaction.review_status == ReviewStatus.NEEDS_REVIEW,
            # Found via live browser verification (Epic F): once the user has dismissed a
            # transaction (E4, "not a real expense"), it must stop nagging for review -- the
            # user has already made the decision that matters, even though its review_status
            # technically never changes from NEEDS_REVIEW.
            Transaction.dismissed.is_(False),
        )
        .all()
    )
    return NeedsReviewQueue(
        unmatched_emails=unmatched_emails, low_confidence_transactions=low_confidence_transactions
    )
