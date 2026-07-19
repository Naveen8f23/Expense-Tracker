"""AddManualTransaction use case (BACKLOG.md H2; REQUIREMENTS.md COR-5).

An escape hatch for the rare transaction with no corresponding source email (e.g. a cash
purchase) -- expected to stay rare, not become the norm. Distinguished from every other
transaction purely by `email_message_id IS NULL` -- no separate boolean flag, one source of
truth per fact (Constitution principle 26).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.models import (
    DebitOrCredit,
    Payee,
    PaymentMethod,
    ReviewStatus,
    Transaction,
    User,
)


@dataclass
class ManualTransactionInput:
    amount: Decimal
    txn_date: date
    payee_name: str
    payment_method: PaymentMethod
    txn_type: DebitOrCredit
    category_id: Optional[int] = None


def _get_or_create_payee_by_name(session: Session, name: str) -> Payee:
    """Manual entries have no VPA/merchant identifier to key on (unlike
    run_classify_and_extract's `_get_or_create_payee`) -- matched case-insensitively by name
    instead, so a manual entry for an already-known payee (e.g. "Golkondas Cafe" vs. the
    extracted "GOLKONDAS CAFE") reuses the same Payee row rather than fragmenting history
    (ANL-3, G4)."""
    payee = session.query(Payee).filter(func.lower(Payee.name) == name.lower()).one_or_none()
    if payee is not None:
        return payee
    payee = Payee(name=name, identifier=None)
    session.add(payee)
    session.flush()
    return payee


def add_manual_transaction(
    session: Session, user: User, data: ManualTransactionInput
) -> Transaction:
    payee = _get_or_create_payee_by_name(session, data.payee_name)

    # COR-2, same as correct_transaction: an explicit category is remembered on the payee for
    # next time; otherwise fall back to whatever this payee's remembered default already is (if
    # any), the same lookup run_classify_and_extract does for auto-ingested transactions.
    if data.category_id is not None:
        payee.default_category_id = data.category_id
        category_id = data.category_id
    else:
        category_id = payee.default_category_id

    txn = Transaction(
        user_id=user.id,
        amount=data.amount,
        currency="INR",  # ADR-0004: INR-only for MVP
        txn_date=data.txn_date,
        txn_time=None,  # no time field on the manual form, matches TransactionDetailPanel's shape
        payee_id=payee.id,
        instrument_last4=None,
        category_id=category_id,
        payment_method=data.payment_method,
        txn_type=data.txn_type,
        reference_number=None,
        confidence_score=1.0,
        review_status=ReviewStatus.USER_CONFIRMED,
        email_message_id=None,
        dismissed=False,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn
