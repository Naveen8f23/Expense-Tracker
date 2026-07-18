"""RunInitialBackfill use case (B3).

One-time backfill: fetch every Gmail message from the configured SenderRule senders, dated from
the first day of the connection's setup month (ADR-0011) through now, and cache each as an
unprocessed EmailMessage row. Classification/extraction happens later (Epic C) -- this story
only proves ingestion, never creates a Transaction.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.application.ingest_gmail_messages import store_new_messages
from app.infrastructure import gmail_client, gmail_oauth
from app.infrastructure.models import GmailConnection, SenderRule, SyncState


@dataclass
class BackfillSummary:
    scanned: int
    matched: int
    skipped: int
    failed: int


def run_initial_backfill(session: Session, connection: GmailConnection) -> BackfillSummary:
    sync_state = (
        session.query(SyncState).filter_by(gmail_connection_id=connection.id).one_or_none()
    )
    if sync_state is None:
        sync_state = SyncState(gmail_connection_id=connection.id)
        session.add(sync_state)

    # B5/ING-8: recorded even if the run fails partway, so "did it even start" is never a
    # question left to a stack trace.
    sync_state.last_sync_started_at = datetime.now(timezone.utc)
    session.commit()

    try:
        summary = _do_backfill(session, connection, sync_state)
    except Exception as exc:  # noqa: BLE001 -- always surfaced (ING-8), never swallowed
        sync_state.last_error = str(exc)
        session.commit()
        raise

    sync_state.last_sync_at = datetime.now(timezone.utc)
    sync_state.last_error = None
    sync_state.last_scanned = summary.scanned
    sync_state.last_matched = summary.matched
    sync_state.last_skipped = summary.skipped
    sync_state.last_failed = summary.failed
    session.commit()
    return summary


def _do_backfill(
    session: Session, connection: GmailConnection, sync_state: SyncState
) -> BackfillSummary:
    credentials, new_tokens_json = gmail_oauth.get_valid_credentials(connection.tokens)
    if new_tokens_json:
        connection.tokens = new_tokens_json
        session.commit()

    # Plant the starting checkpoint for RunIncrementalSync (B4) regardless of whether there's
    # anything to backfill right now -- B4 has nothing to start from otherwise.
    sync_state.last_history_id = gmail_client.get_current_history_id(credentials)

    sender_addresses = sorted({rule.sender_address for rule in session.query(SenderRule).all()})
    if not sender_addresses:
        return BackfillSummary(scanned=0, matched=0, skipped=0, failed=0)

    # ADR-0011: backfill starts from the 1st of the calendar month the connection was first set
    # up in, not a rolling window -- connection.created_at reflects that original connect time
    # even across a later reconnect (B1 updates tokens/email in place, not created_at).
    after = connection.created_at.date().replace(day=1)
    query = gmail_client.build_search_query(sender_addresses, after)
    message_ids = gmail_client.list_message_ids(credentials, query)

    matched, skipped, _filtered_out, failed = store_new_messages(
        session, connection, credentials, message_ids
    )

    return BackfillSummary(scanned=len(message_ids), matched=matched, skipped=skipped, failed=failed)
