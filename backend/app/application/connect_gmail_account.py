"""ConnectGmailAccount use case (B1).

Orchestrates the OAuth callback into a persisted, encrypted GmailConnection row. Per
ARCHITECTURE.md #3, this Application layer owns the orchestration; Infrastructure
(app.infrastructure.gmail_oauth) owns the Gmail-specific OAuth mechanics.
"""

from sqlalchemy.orm import Session

from app.infrastructure import gmail_oauth
from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.models import GmailConnection


def complete_gmail_connection(session: Session, code: str, state: str) -> GmailConnection:
    credentials = gmail_oauth.exchange_code(code, state)
    email_address = gmail_oauth.fetch_connected_email(credentials)
    tokens_json = gmail_oauth.credentials_to_json(credentials)

    user = ensure_default_user(session)
    # REQUIREMENTS.md Assumption 1: a single Gmail account for v1 -- reconnecting updates the
    # existing connection's tokens rather than creating a duplicate row.
    connection = session.query(GmailConnection).filter_by(user_id=user.id).one_or_none()
    if connection is None:
        connection = GmailConnection(
            user_id=user.id, email_address=email_address, tokens=tokens_json
        )
        session.add(connection)
    else:
        connection.email_address = email_address
        connection.tokens = tokens_json
    session.commit()
    session.refresh(connection)
    return connection
