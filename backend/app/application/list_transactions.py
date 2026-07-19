"""ListTransactions use case (BACKLOG.md E1; REQUIREMENTS.md SRCH-1, SRCH-2).

The API layer's search/filter surface -- the dashboard never queries the database directly
(ARCHITECTURE.md #3).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.domain.transaction_time import effective_sort_datetime
from app.infrastructure.models import Category, DebitOrCredit, Payee, PaymentMethod, Transaction, User


@dataclass
class TransactionFilters:
    payee: Optional[str] = None  # substring match against payee name or identifier (VPA/merchant)
    category_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    payment_method: Optional[PaymentMethod] = None
    txn_type: Optional[DebitOrCredit] = None
    # Free-text (SRCH-1): matches payee name/identifier or category name -- the human-readable
    # text fields on a transaction. Doesn't match amount/date/reference number; those have their
    # own dedicated filters above.
    query: Optional[str] = None


def list_transactions(
    session: Session, user: User, filters: TransactionFilters, *, limit: int = 50, offset: int = 0
) -> tuple[list[Transaction], int]:
    """Returns (page_of_transactions, total_matching_count).

    Dismissed transactions (COR-4) are excluded by default -- SRCH-1 never surfaces them unless a
    future story explicitly asks to include them (e.g. a "show dismissed" toggle).
    """
    stmt = (
        session.query(Transaction)
        .join(Payee, Transaction.payee_id == Payee.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.user_id == user.id, Transaction.dismissed.is_(False))
    )

    if filters.payee:
        like = f"%{filters.payee}%"
        stmt = stmt.filter(or_(Payee.name.ilike(like), Payee.identifier.ilike(like)))
    if filters.category_id is not None:
        stmt = stmt.filter(Transaction.category_id == filters.category_id)
    if filters.date_from is not None:
        stmt = stmt.filter(Transaction.txn_date >= filters.date_from)
    if filters.date_to is not None:
        stmt = stmt.filter(Transaction.txn_date <= filters.date_to)
    if filters.amount_min is not None:
        stmt = stmt.filter(Transaction.amount >= filters.amount_min)
    if filters.amount_max is not None:
        stmt = stmt.filter(Transaction.amount <= filters.amount_max)
    if filters.payment_method is not None:
        stmt = stmt.filter(Transaction.payment_method == filters.payment_method)
    if filters.txn_type is not None:
        stmt = stmt.filter(Transaction.txn_type == filters.txn_type)
    if filters.query:
        like = f"%{filters.query}%"
        stmt = stmt.filter(
            or_(Payee.name.ilike(like), Payee.identifier.ilike(like), Category.name.ilike(like))
        )

    # Sorted by effective time (real txn_time, or the source email's received time as a fallback
    # for the date-only UPI templates -- app/domain/transaction_time.py), matching what the
    # dashboard displays. This can't be expressed as a single SQL ORDER BY across two different
    # source columns/tables, so it's done in Python after fetching every matching row; acceptable
    # at this product's scale (REQUIREMENTS.md Performance NFR: "up to tens of thousands of
    # transactions", well within what an in-memory sort handles instantly) -- revisit only if a
    # real performance problem is ever measured (Constitution principle 16).
    all_matching = stmt.options(joinedload(Transaction.email_message)).all()
    all_matching.sort(
        key=lambda t: effective_sort_datetime(t.txn_date, t.txn_time, t.email_message.received_at),
        reverse=True,
    )
    total = len(all_matching)
    items = all_matching[offset : offset + limit]
    return items, total


def get_transactions_since(session: Session, user: User, since_id: int) -> list[Transaction]:
    """Transactions created after `since_id`, in creation order -- for the dashboard to poll and
    detect newly-arrived transactions (from the SyncScheduler) to notify about. Ordered by `id`
    ascending (creation order), unlike `list_transactions`' txn_date ordering: a backfilled older
    transaction can be inserted after a newer one, so `id` is the only reliable "just arrived"
    signal. Dismissed transactions are excluded -- nothing to notify about there.
    """
    return (
        session.query(Transaction)
        .join(Payee, Transaction.payee_id == Payee.id)
        .options(joinedload(Transaction.email_message))
        .filter(
            Transaction.user_id == user.id,
            Transaction.id > since_id,
            Transaction.dismissed.is_(False),
        )
        .order_by(Transaction.id.asc())
        .all()
    )
