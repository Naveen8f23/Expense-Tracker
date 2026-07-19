"""Transactions API (BACKLOG.md E1-E4; REQUIREMENTS.md SRCH-1/2, TRC-1/2, COR-1..4).

The only door the dashboard has into transaction data -- it never queries the database directly
(ARCHITECTURE.md #3).
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.correct_transaction import TransactionCorrection, correct_transaction
from app.application.dismiss_transaction import dismiss_transaction
from app.application.list_transactions import (
    TransactionFilters,
    get_transactions_since,
    list_transactions,
)
from app.application.transaction_errors import TransactionNotFoundError
from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import get_db
from app.infrastructure.models import DebitOrCredit, PaymentMethod, Transaction
from app.presentation.serializers import serialize_email_message, serialize_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransactionCorrectionRequest(BaseModel):
    amount: Optional[Decimal] = None
    txn_date: Optional[date] = None
    payee_name: Optional[str] = None
    category_id: Optional[int] = None
    payment_method: Optional[PaymentMethod] = None
    txn_type: Optional[DebitOrCredit] = None


@router.get("")
def list_transactions_endpoint(
    payee: Optional[str] = Query(default=None),
    category_id: Optional[int] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    amount_min: Optional[Decimal] = Query(default=None),
    amount_max: Optional[Decimal] = Query(default=None),
    payment_method: Optional[PaymentMethod] = Query(default=None),
    txn_type: Optional[DebitOrCredit] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Free-text: matches payee or category"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> dict:
    user = ensure_default_user(session)
    filters = TransactionFilters(
        payee=payee,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        payment_method=payment_method,
        txn_type=txn_type,
        query=q,
    )
    items, total = list_transactions(session, user, filters, limit=limit, offset=offset)
    return {
        "items": [serialize_transaction(t) for t in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/recent")
def get_recent_transactions_endpoint(
    since_id: int = Query(default=0, ge=0), session: Session = Depends(get_db)
) -> dict:
    """For the dashboard to poll (alongside the SyncScheduler background thread) and detect
    newly-arrived transactions to notify about -- registered before "/{transaction_id}" so
    "recent" is never mistaken for a transaction id."""
    user = ensure_default_user(session)
    items = get_transactions_since(session, user, since_id)
    return {"items": [serialize_transaction(t) for t in items]}


@router.get("/{transaction_id}")
def get_transaction_endpoint(transaction_id: int, session: Session = Depends(get_db)) -> dict:
    user = ensure_default_user(session)
    txn = session.get(Transaction, transaction_id)
    if txn is None or txn.user_id != user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    data = serialize_transaction(txn)
    data["source_email"] = serialize_email_message(txn.email_message)
    return data


@router.patch("/{transaction_id}")
def correct_transaction_endpoint(
    transaction_id: int, body: TransactionCorrectionRequest, session: Session = Depends(get_db)
) -> dict:
    user = ensure_default_user(session)
    try:
        txn = correct_transaction(
            session,
            user.id,
            transaction_id,
            TransactionCorrection(
                amount=body.amount,
                txn_date=body.txn_date,
                payee_name=body.payee_name,
                category_id=body.category_id,
                payment_method=body.payment_method,
                txn_type=body.txn_type,
            ),
        )
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_transaction(txn)


@router.post("/{transaction_id}/dismiss")
def dismiss_transaction_endpoint(transaction_id: int, session: Session = Depends(get_db)) -> dict:
    user = ensure_default_user(session)
    try:
        txn = dismiss_transaction(session, user.id, transaction_id)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_transaction(txn)
