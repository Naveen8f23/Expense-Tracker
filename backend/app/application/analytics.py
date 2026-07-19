"""Analytics use cases (BACKLOG.md Epic G; REQUIREMENTS.md ANL-1..4).

Same idiom as app/application/list_transactions.py: plain functions over a sync SQLAlchemy
Session, with a mandatory `Transaction.user_id == user.id` + `Transaction.dismissed.is_(False)`
base filter on every query (COR-4 -- dismissed rows never contribute to analytics).

Sign convention (ADR-0021): every summary reports total_debit, total_credit, and
`net = total_debit - total_credit` (positive net means money spent, not received) -- the
"expense tracker" framing this whole product is built around.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.domain.transaction_time import effective_sort_datetime
from app.infrastructure.models import Category, DebitOrCredit, Payee, Transaction, User
from app.presentation.serializers import serialize_transaction


def month_bounds(month: date) -> tuple[date, date]:
    """Given any date, returns (first_of_month, first_of_next_month) -- a half-open range
    [start, end) suitable for `Transaction.txn_date >= start, Transaction.txn_date < end`."""
    start = month.replace(day=1)
    days_in_month = monthrange(start.year, start.month)[1]
    end = start.replace(day=days_in_month) + timedelta(days=1)
    return start, end


@dataclass
class MonthlySummary:
    month: str
    total_debit: Decimal
    total_credit: Decimal
    net: Decimal
    transaction_count: int


def get_monthly_summary(session: Session, user: User, month: date) -> MonthlySummary:
    start, end = month_bounds(month)
    rows = (
        session.query(
            Transaction.txn_type,
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        )
        .filter(
            Transaction.user_id == user.id,
            Transaction.dismissed.is_(False),
            Transaction.txn_date >= start,
            Transaction.txn_date < end,
        )
        .group_by(Transaction.txn_type)
        .all()
    )
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    transaction_count = 0
    for txn_type, total, count in rows:
        total = Decimal(str(total))
        transaction_count += count
        if txn_type == DebitOrCredit.DEBIT:
            total_debit = total
        else:
            total_credit = total

    return MonthlySummary(
        month=start.strftime("%Y-%m"),
        total_debit=total_debit,
        total_credit=total_credit,
        net=total_debit - total_credit,
        transaction_count=transaction_count,
    )


@dataclass
class CategoryBreakdownItem:
    category_id: Optional[int]
    category_name: str
    total: Decimal
    transaction_count: int


@dataclass
class CategoryBreakdown:
    month: str
    categories: list[CategoryBreakdownItem]


def get_category_breakdown(session: Session, user: User, month: date) -> CategoryBreakdown:
    """"Spend by category" (ANL-2) -- debits only (ADR-0021): a refund/credit isn't spend, so
    including it here would understate what was actually spent in a category."""
    start, end = month_bounds(month)
    rows = (
        session.query(
            Category.id,
            Category.name,
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        )
        .select_from(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user.id,
            Transaction.dismissed.is_(False),
            Transaction.txn_type == DebitOrCredit.DEBIT,
            Transaction.txn_date >= start,
            Transaction.txn_date < end,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    categories = [
        CategoryBreakdownItem(
            category_id=category_id,
            category_name=category_name if category_name is not None else "Uncategorized",
            total=Decimal(str(total)),
            transaction_count=count,
        )
        for category_id, category_name, total, count in rows
    ]
    return CategoryBreakdown(month=start.strftime("%Y-%m"), categories=categories)


def get_payee_history(
    session: Session, user: User, payee_name: str, *, limit: int = 50, offset: int = 0
) -> Optional[dict]:
    """All transactions with a given payee, plus totals (ANL-3) -- full history, not scoped to a
    period. Matches by case-insensitive exact name (ADR-0021): the user clicks one exact name in
    the transactions table, so a substring match would silently pull in unrelated payees.

    Returns None if no (non-dismissed) transaction with this payee name exists for the user --
    the router treats that as a 404, since an unknown payee name is a real error, not an empty
    result.
    """
    base = (
        session.query(Transaction)
        .join(Payee, Transaction.payee_id == Payee.id)
        .filter(
            Transaction.user_id == user.id,
            Transaction.dismissed.is_(False),
            func.lower(Payee.name) == payee_name.lower(),
        )
    )

    totals_row = base.with_entities(
        Transaction.txn_type,
        func.coalesce(func.sum(Transaction.amount), 0),
        func.count(Transaction.id),
    ).group_by(Transaction.txn_type).all()

    total_debit = Decimal("0")
    total_credit = Decimal("0")
    transaction_count = 0
    for txn_type, total, count in totals_row:
        total = Decimal(str(total))
        transaction_count += count
        if txn_type == DebitOrCredit.DEBIT:
            total_debit = total
        else:
            total_credit = total

    if transaction_count == 0:
        return None

    # Sorted by effective time, same as list_transactions -- see app/domain/transaction_time.py
    # for why this can't be a single SQL ORDER BY.
    all_matching = base.options(joinedload(Transaction.email_message)).all()
    all_matching.sort(
        key=lambda t: effective_sort_datetime(t.txn_date, t.txn_time, t.email_message.received_at),
        reverse=True,
    )
    items = all_matching[offset : offset + limit]

    return {
        "payee_name": payee_name,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "net": total_debit - total_credit,
        "transaction_count": transaction_count,
        "limit": limit,
        "offset": offset,
        "items": [serialize_transaction(t) for t in items],
    }
