"""IgnoreNeedsReviewEmail use case (BACKLOG.md F4 addendum).

An unmatched email (no known SenderRule content pattern -- EXT-6) has no linked Transaction, so
E3's correct/E4's dismiss (which both operate on a Transaction) don't apply to it. This reuses the
existing (previously unused) EmailMessageStatus.IGNORED value to give the needs-review dashboard
a real way to clear a genuinely irrelevant email from the queue, mirroring E4's dismiss pattern
for the Transaction half of the queue.
"""

from sqlalchemy.orm import Session

from app.infrastructure.models import EmailMessage, EmailMessageStatus


class EmailMessageNotFoundError(Exception):
    pass


class EmailMessageNotInReviewError(Exception):
    """Raised when trying to ignore an email that isn't currently needs-review -- e.g. one
    that's already MATCHED or already IGNORED."""


def ignore_needs_review_email(session: Session, email_id: int) -> EmailMessage:
    email = session.get(EmailMessage, email_id)
    if email is None:
        raise EmailMessageNotFoundError(f"No email message with id {email_id}")
    if email.status != EmailMessageStatus.NEEDS_REVIEW:
        raise EmailMessageNotInReviewError(
            f"Email message {email_id} is not currently needs-review (status={email.status.value})"
        )
    email.status = EmailMessageStatus.IGNORED
    session.commit()
    session.refresh(email)
    return email
