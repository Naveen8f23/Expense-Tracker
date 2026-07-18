"""CorrectTransaction use case (BACKLOG.md E3; REQUIREMENTS.md COR-1, COR-2, COR-3).

**Design note on the "payee" field (COR-1):** correcting a transaction's payee renames the
shared `Payee` row (by `name`) rather than reassigning the transaction to a different `Payee`
entity. REQUIREMENTS.md's data model explicitly defers "alias normalization" (treating two
slightly different payee strings as the same real-world entity) as a post-MVP idea -- a full
reassign-to-a-different-payee flow would be building that early. A naming correction (e.g. the
extracted display name is odd) is the scenario COR-1 is meant to cover for MVP.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.application.transaction_errors import TransactionNotFoundError
from app.infrastructure.models import (
    CorrectionLog,
    DebitOrCredit,
    PaymentMethod,
    ReviewStatus,
    Transaction,
)


@dataclass
class TransactionCorrection:
    """Only fields that are not None are applied -- omitting a field leaves it unchanged.
    Explicitly clearing a field back to null (e.g. un-categorizing) isn't a stated MVP need
    (COR-1 lists correcting values, not blanking them) and isn't supported here."""

    amount: Optional[Decimal] = None
    txn_date: Optional[date] = None
    payee_name: Optional[str] = None
    category_id: Optional[int] = None
    payment_method: Optional[PaymentMethod] = None
    txn_type: Optional[DebitOrCredit] = None


def correct_transaction(
    session: Session, user_id: int, transaction_id: int, correction: TransactionCorrection
) -> Transaction:
    txn = session.get(Transaction, transaction_id)
    if txn is None or txn.user_id != user_id:
        raise TransactionNotFoundError(f"No transaction with id {transaction_id}")

    def _log(field_name: str, old_value, new_value) -> None:
        if old_value == new_value:
            return
        session.add(
            CorrectionLog(
                transaction_id=txn.id,
                field_name=field_name,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
        )

    if correction.amount is not None:
        _log("amount", txn.amount, correction.amount)
        txn.amount = correction.amount
    if correction.txn_date is not None:
        _log("txn_date", txn.txn_date, correction.txn_date)
        txn.txn_date = correction.txn_date
    if correction.payee_name is not None:
        _log("payee_name", txn.payee.name, correction.payee_name)
        txn.payee.name = correction.payee_name
    if correction.category_id is not None:
        _log("category_id", txn.category_id, correction.category_id)
        txn.category_id = correction.category_id
        # COR-2: remembered so this payee's *future* transactions default to it -- the
        # categorization module's only real logic for MVP (EXT-2: never auto-inferred).
        txn.payee.default_category_id = correction.category_id
    if correction.payment_method is not None:
        _log("payment_method", txn.payment_method.value, correction.payment_method.value)
        txn.payment_method = correction.payment_method
    if correction.txn_type is not None:
        _log("txn_type", txn.txn_type.value, correction.txn_type.value)
        txn.txn_type = correction.txn_type

    # The user has now reviewed this transaction, whether or not anything actually changed --
    # this is the only place ReviewStatus.USER_CONFIRMED is ever set.
    txn.review_status = ReviewStatus.USER_CONFIRMED

    session.commit()
    session.refresh(txn)
    return txn
