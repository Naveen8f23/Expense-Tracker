"""Sync health status API (BACKLOG.md E7; REQUIREMENTS.md ING-8)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.get_sync_status import get_sync_status
from app.infrastructure.db import get_db
from app.infrastructure.models import GmailConnection

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status")
def sync_status_endpoint(session: Session = Depends(get_db)) -> dict:
    # Single Gmail account for now (REQUIREMENTS.md Assumption 1) -- same one-row assumption as
    # ensure_default_user.
    connection = session.query(GmailConnection).first()
    if connection is None:
        raise HTTPException(status_code=404, detail="No Gmail connection configured yet")

    sync_state = get_sync_status(session, connection)
    if sync_state is None:
        return {"connected": True, "email_address": connection.email_address, "synced": False}

    return {
        "connected": True,
        "email_address": connection.email_address,
        "synced": True,
        "last_sync_started_at": (
            sync_state.last_sync_started_at.isoformat()
            if sync_state.last_sync_started_at
            else None
        ),
        "last_sync_at": sync_state.last_sync_at.isoformat() if sync_state.last_sync_at else None,
        "last_error": sync_state.last_error,
        "last_scanned": sync_state.last_scanned,
        "last_matched": sync_state.last_matched,
        "last_skipped": sync_state.last_skipped,
        "last_failed": sync_state.last_failed,
    }
