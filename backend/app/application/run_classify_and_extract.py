"""ClassifyAndExtractEmail use case (BACKLOG.md C7; REQUIREMENTS.md EXT-5, EXT-6).

Processes every UNPROCESSED EmailMessage: classify its content against the configured
SenderRule patterns (app.domain.classification), then run the matching fixed-rule extractor
(app.domain.extraction). A cleanly extracted email becomes a Transaction (status MATCHED). An
email that classifies but fails extraction, or that matches no known pattern at all, is never
silently dropped -- it's marked NEEDS_REVIEW instead, with whatever classification result was
reached preserved for context (EXT-6).

Nothing calls this automatically yet -- same explicit-deferral pattern as B4's sync scheduler
(BACKLOG.md B4): a scheduler is a cross-cutting concern to add once there's a reason to run this
unattended, not before.
"""

from sqlalchemy.orm import Session

from app.domain import classification, extraction
from app.domain.ai_fallback import AIFallbackClient, StubAIFallbackClient
from app.domain.extraction import ExtractedTransaction, ExtractionError
from app.infrastructure.models import (
    EmailMessage,
    EmailMessageStatus,
    Payee,
    ReviewStatus,
    SenderRule,
    Transaction,
    User,
)

# content_pattern_id -> extractor, keyed to match SenderRule.content_pattern_id values seeded by
# app.infrastructure.bootstrap.HDFC_SENDER_RULES. Adding a fourth pattern later (credit card
# credit, REQUIREMENTS.md SS8) means one more entry here, not a restructuring.
_EXTRACTORS = {
    "hdfc_upi_debit": extraction.extract_upi_debit,
    "hdfc_upi_credit": extraction.extract_upi_credit,
    "hdfc_credit_card_debit": extraction.extract_credit_card_debit,
}


def _get_or_create_payee(session: Session, identifier: str, name: str | None) -> Payee:
    """Keyed on identifier (VPA or card merchant descriptor) -- the same payee/VPA reusing a
    display name once and omitting it another time (Edge Cases SS10) should still resolve to one
    Payee row, not two."""
    payee = session.query(Payee).filter(Payee.identifier == identifier).one_or_none()
    if payee is not None:
        return payee
    payee = Payee(identifier=identifier, name=name or identifier)
    session.add(payee)
    session.flush()
    return payee


def _create_transaction(
    session: Session,
    user: User,
    email: EmailMessage,
    extracted: ExtractedTransaction,
    *,
    review_status: ReviewStatus,
) -> Transaction:
    payee = _get_or_create_payee(session, extracted.payee_identifier, extracted.payee_name)
    transaction = Transaction(
        user_id=user.id,
        amount=extracted.amount,
        currency=extracted.currency,
        txn_date=extracted.txn_date,
        txn_time=extracted.txn_time,
        payee_id=payee.id,
        instrument_last4=extracted.instrument_last4,
        # EXT-2: never auto-inferred from content -- but COR-2 (BACKLOG.md E3) says a category
        # the user already assigned to this payee should carry forward to their *new*
        # transactions, so this is a lookup of a prior human decision, not new inference.
        category_id=payee.default_category_id,
        payment_method=extracted.payment_method,
        txn_type=extracted.txn_type,
        reference_number=extracted.reference_number,
        confidence_score=extracted.confidence_score,
        review_status=review_status,
        email_message_id=email.id,
    )
    session.add(transaction)
    return transaction


def run_classify_and_extract(
    session: Session, user: User, ai_fallback: AIFallbackClient | None = None
) -> tuple[int, int]:
    """Returns (transactions_created, flagged_needs_review)."""
    ai_fallback = ai_fallback if ai_fallback is not None else StubAIFallbackClient()
    candidate_pattern_ids = [rule.content_pattern_id for rule in session.query(SenderRule).all()]

    created = 0
    flagged = 0
    pending = (
        session.query(EmailMessage)
        .filter(EmailMessage.status == EmailMessageStatus.UNPROCESSED)
        .all()
    )
    for email in pending:
        pattern_id = classification.classify(email.content, candidate_pattern_ids)
        if pattern_id is None:
            # Matches no known content pattern for this (already sender-filtered, per B3/B4)
            # email -- flagged for review rather than ignored or dropped (EXT-6).
            email.status = EmailMessageStatus.NEEDS_REVIEW
            flagged += 1
            continue

        email.classified_pattern_id = pattern_id
        extractor = _EXTRACTORS[pattern_id]
        try:
            extracted = extractor(email.content)
        except ExtractionError:
            fallback_result = ai_fallback.extract(email.content)
            if fallback_result is None:
                # C8: the stub (and any future model that declines to guess) means this email
                # is flagged for review with its classification preserved, not silently dropped.
                email.status = EmailMessageStatus.NEEDS_REVIEW
                flagged += 1
                continue
            # A real AI fallback's output is never trusted outright (EXT-4/EXT-5): it still
            # becomes a Transaction, but always flagged for the user to confirm.
            _create_transaction(
                session, user, email, fallback_result, review_status=ReviewStatus.NEEDS_REVIEW
            )
            email.status = EmailMessageStatus.MATCHED
            created += 1
            continue

        _create_transaction(
            session, user, email, extracted, review_status=ReviewStatus.AUTO_ACCEPTED
        )
        email.status = EmailMessageStatus.MATCHED
        created += 1

    session.commit()
    return created, flagged


def get_needs_review_emails(session: Session) -> list[EmailMessage]:
    """A queryable list of everything currently flagged for review (BACKLOG.md C7's third
    acceptance criterion) -- surfaced properly via an API endpoint in Epic E (E5)."""
    return (
        session.query(EmailMessage)
        .filter(EmailMessage.status == EmailMessageStatus.NEEDS_REVIEW)
        .all()
    )
