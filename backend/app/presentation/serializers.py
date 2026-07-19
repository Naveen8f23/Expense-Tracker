"""Shared response serialization for the API Layer (BACKLOG.md Epic E).

Kept separate from any one router since E1/E2/E5 all need to render a Transaction the same way.
"""

from app.infrastructure.models import EmailMessage, Transaction


def serialize_transaction(txn: Transaction) -> dict:
    return {
        "id": txn.id,
        "amount": str(txn.amount),
        "currency": txn.currency,
        "txn_date": txn.txn_date.isoformat(),
        "txn_time": txn.txn_time.isoformat() if txn.txn_time else None,
        # Not every template provides a time (the UPI templates are date-only, REQUIREMENTS.md
        # Appendix A) -- the email's received time is exposed separately so the dashboard can
        # show a clearly-marked approximate time for those rows rather than fabricating one.
        # Null for a manually-added transaction (H2, COR-5), which has no source email at all --
        # the dashboard falls back to `created_at` in that case.
        "email_received_at": txn.email_message.received_at.isoformat() if txn.email_message else None,
        "payee": {"id": txn.payee.id, "name": txn.payee.name, "identifier": txn.payee.identifier},
        "instrument_last4": txn.instrument_last4,
        "category_id": txn.category_id,
        "category_name": txn.category.name if txn.category else None,
        "payment_method": txn.payment_method.value,
        "txn_type": txn.txn_type.value,
        "reference_number": txn.reference_number,
        "confidence_score": txn.confidence_score,
        "review_status": txn.review_status.value,
        "email_message_id": txn.email_message_id,
        "dismissed": txn.dismissed,
        "created_at": txn.created_at.isoformat(),
    }


def serialize_email_message(email: EmailMessage) -> dict:
    return {
        "id": email.id,
        "message_id": email.message_id,
        "received_at": email.received_at.isoformat(),
        "status": email.status.value,
        "classified_pattern_id": email.classified_pattern_id,
        "content": email.content,
    }
