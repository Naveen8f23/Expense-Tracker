from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.application.connect_gmail_account import complete_gmail_connection
from app.application.run_initial_backfill import run_initial_backfill
from app.infrastructure import gmail_oauth
from app.infrastructure.db import get_db

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.get("/connect")
def connect() -> RedirectResponse:
    try:
        authorization_url = gmail_oauth.build_authorization_url()
    except gmail_oauth.GmailAuthError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse(authorization_url)


@router.get("/callback")
def callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: Session = Depends(get_db),
) -> dict:
    if error:
        raise HTTPException(status_code=400, detail=f"Gmail consent was not granted: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing 'code' or 'state' in Gmail callback.")
    try:
        connection = complete_gmail_connection(session, code, state)
    except gmail_oauth.GmailAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = {"status": "connected", "email_address": connection.email_address}
    # The connection itself is valid even if the backfill hits a snag (e.g. a transient Gmail
    # API error) -- surface that separately (ING-8) rather than making a working connection
    # look like it failed entirely.
    try:
        summary = run_initial_backfill(session, connection)
        response["backfill"] = {
            "scanned": summary.scanned,
            "matched": summary.matched,
            "skipped": summary.skipped,
            "failed": summary.failed,
        }
    except Exception as exc:  # noqa: BLE001 -- surfaced in the response, never swallowed
        response["backfill_error"] = str(exc)
    return response
