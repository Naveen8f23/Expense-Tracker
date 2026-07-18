"""Needs-review queue API (BACKLOG.md E5; REQUIREMENTS.md EXT-5, EXT-6)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application.get_needs_review_queue import get_needs_review_queue
from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import get_db
from app.presentation.serializers import serialize_email_message, serialize_transaction

router = APIRouter(tags=["needs-review"])


@router.get("/needs-review")
def get_needs_review_endpoint(session: Session = Depends(get_db)) -> dict:
    user = ensure_default_user(session)
    queue = get_needs_review_queue(session, user)
    return {
        "unmatched_emails": [serialize_email_message(e) for e in queue.unmatched_emails],
        "low_confidence_transactions": [
            serialize_transaction(t) for t in queue.low_confidence_transactions
        ],
    }
