"""Analytics API (BACKLOG.md Epic G; REQUIREMENTS.md ANL-1..4).

Same idiom as transactions_router.py: the dashboard's only door into aggregated transaction
data -- it never queries the database directly (ARCHITECTURE.md #3).
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.application.analytics import (
    get_category_breakdown,
    get_monthly_summary,
    get_payee_history,
    get_period_category_breakdown,
    get_period_summary,
)
from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])

_VALID_PERIODS = {"day", "week", "month", "year"}


def _parse_month(month: Optional[str]) -> date:
    """Parses "YYYY-MM" into a first-of-month date; defaults to the current month. Validated at
    the boundary (Constitution principle 22) -- an invalid format is a 422, not a guess."""
    if month is None:
        today = date.today()
        return today.replace(day=1)
    try:
        parsed = datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="Invalid month, expected YYYY-MM"
        ) from exc
    return date(parsed.year, parsed.month, 1)


def _parse_period(period: str) -> str:
    if period not in _VALID_PERIODS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period, expected one of {sorted(_VALID_PERIODS)}",
        )
    return period


def _parse_date(date_str: Optional[str]) -> date:
    """Parses "YYYY-MM-DD"; defaults to today. Same validate-at-the-boundary shape as
    `_parse_month` -- an invalid format is a 422, not a guess."""
    if date_str is None:
        return date.today()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="Invalid date, expected YYYY-MM-DD"
        ) from exc


@router.get("/monthly")
def get_monthly_summary_endpoint(
    month: Optional[str] = Query(default=None, description="YYYY-MM, defaults to current month"),
    session: Session = Depends(get_db),
) -> dict:
    user = ensure_default_user(session)
    summary = get_monthly_summary(session, user, _parse_month(month))
    return {
        "month": summary.month,
        "total_debit": str(summary.total_debit),
        "total_credit": str(summary.total_credit),
        "net": str(summary.net),
        "transaction_count": summary.transaction_count,
    }


@router.get("/by-category")
def get_category_breakdown_endpoint(
    month: Optional[str] = Query(default=None, description="YYYY-MM, defaults to current month"),
    session: Session = Depends(get_db),
) -> dict:
    user = ensure_default_user(session)
    breakdown = get_category_breakdown(session, user, _parse_month(month))
    return {
        "month": breakdown.month,
        "categories": [
            {
                "category_id": item.category_id,
                "category_name": item.category_name,
                "total": str(item.total),
                "transaction_count": item.transaction_count,
            }
            for item in breakdown.categories
        ],
    }


@router.get("/summary")
def get_period_summary_endpoint(
    period: str = Query(..., description="One of: day, week, month, year"),
    date_param: Optional[str] = Query(
        default=None, alias="date", description="YYYY-MM-DD, defaults to today"
    ),
    session: Session = Depends(get_db),
) -> dict:
    """Flexible-period summary (day/week/month/year), a new endpoint alongside `/monthly` rather
    than a change to it -- the web dashboard keeps calling `/monthly` with `month=` unmodified; only
    Ledger uses this one (see DECISIONS.md)."""
    user = ensure_default_user(session)
    summary = get_period_summary(session, user, _parse_period(period), _parse_date(date_param))
    return {
        "period": summary.period,
        "start_date": summary.start_date.isoformat(),
        "end_date": summary.end_date.isoformat(),
        "total_debit": str(summary.total_debit),
        "total_credit": str(summary.total_credit),
        "net": str(summary.net),
        "transaction_count": summary.transaction_count,
    }


@router.get("/category-breakdown")
def get_period_category_breakdown_endpoint(
    period: str = Query(..., description="One of: day, week, month, year"),
    date_param: Optional[str] = Query(
        default=None, alias="date", description="YYYY-MM-DD, defaults to today"
    ),
    session: Session = Depends(get_db),
) -> dict:
    """Flexible-period category breakdown, mirrors `/summary` above -- `/by-category` (month-only)
    is untouched, still used by the web dashboard."""
    user = ensure_default_user(session)
    breakdown = get_period_category_breakdown(
        session, user, _parse_period(period), _parse_date(date_param)
    )
    return {
        "period": breakdown.period,
        "start_date": breakdown.start_date.isoformat(),
        "end_date": breakdown.end_date.isoformat(),
        "categories": [
            {
                "category_id": item.category_id,
                "category_name": item.category_name,
                "total": str(item.total),
                "transaction_count": item.transaction_count,
            }
            for item in breakdown.categories
        ],
    }


@router.get("/by-payee/{payee}")
def get_payee_history_endpoint(
    payee: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> dict:
    user = ensure_default_user(session)
    result = get_payee_history(session, user, payee, limit=limit, offset=offset)
    if result is None:
        raise HTTPException(status_code=404, detail="No transactions found for this payee")
    return {
        **result,
        "total_debit": str(result["total_debit"]),
        "total_credit": str(result["total_credit"]),
        "net": str(result["net"]),
    }
