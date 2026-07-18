"""GetSyncStatus use case (BACKLOG.md E7; REQUIREMENTS.md ING-8)."""

from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.models import GmailConnection, SyncState


def get_sync_status(session: Session, connection: GmailConnection) -> Optional[SyncState]:
    return session.query(SyncState).filter_by(gmail_connection_id=connection.id).one_or_none()
