"""RunIncrementalSync use case (B4).

Uses Gmail's History API to fetch only what's changed since the last checkpoint (ING-4, ING-5),
rather than re-scanning the whole original backfill window every time. Falls back to a bounded
re-scan -- from the last successful sync time, not the full original backfill window -- if the
stored checkpoint has fallen outside Gmail's History API retention window, rather than failing
silently (ING-4 edge case, REQUIREMENTS.md Edge Cases §10).
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.application.ingest_gmail_messages import store_new_messages
from app.infrastructure import gmail_client, gmail_oauth
from app.infrastructure.models import GmailConnection, SenderRule, SyncState


class NoSyncCheckpointError(Exception):
    """Raised when incremental sync is attempted before the initial backfill (B3) has run."""


@dataclass
class IncrementalSyncSummary:
    scanned: int
    matched: int
    skipped: int
    failed: int
    used_fallback_rescan: bool


def run_incremental_sync(session: Session, connection: GmailConnection) -> IncrementalSyncSummary:
    sync_state = (
        session.query(SyncState).filter_by(gmail_connection_id=connection.id).one_or_none()
    )
    if sync_state is None or not sync_state.last_history_id:
        raise NoSyncCheckpointError(
            "No sync checkpoint for this connection -- run the initial backfill (B3) first."
        )

    # B5/ING-8: recorded even if the run fails partway.
    sync_state.last_sync_started_at = datetime.now(timezone.utc)
    session.commit()

    try:
        summary = _do_incremental_sync(session, connection, sync_state)
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


def _do_incremental_sync(
    session: Session, connection: GmailConnection, sync_state: SyncState
) -> IncrementalSyncSummary:
    credentials, new_tokens_json = gmail_oauth.get_valid_credentials(connection.tokens)
    if new_tokens_json:
        connection.tokens = new_tokens_json
        session.commit()

    sender_addresses = {rule.sender_address for rule in session.query(SenderRule).all()}
    if not sender_addresses:
        sync_state.last_history_id = gmail_client.get_current_history_id(credentials)
        return IncrementalSyncSummary(
            scanned=0, matched=0, skipped=0, failed=0, used_fallback_rescan=False
        )

    used_fallback = False
    keep_if = None
    try:
        candidate_ids, latest_history_id = gmail_client.list_message_ids_since_history(
            credentials, sync_state.last_history_id
        )
        # History API isn't sender-scoped like messages.list's q= -- filter after the fact,
        # post-dedup (store_new_messages' keep_if), so an already-stored message is never
        # re-fetched just to check its sender.
        keep_if = lambda message: gmail_client.message_sender_matches(  # noqa: E731
            message, sender_addresses
        )
    except gmail_client.HistoryCheckpointExpiredError:
        used_fallback = True
        # Bounded re-scan: from the last known-good sync time, not the full original backfill
        # window -- a stale checkpoint doesn't mean starting over from ADR-0011's setup month.
        after = (sync_state.last_sync_at or connection.created_at).date()
        query = gmail_client.build_search_query(sorted(sender_addresses), after)
        candidate_ids = gmail_client.list_message_ids(credentials, query)
        latest_history_id = gmail_client.get_current_history_id(credentials)

    matched, skipped_duplicate, filtered_out, failed = store_new_messages(
        session, connection, credentials, candidate_ids, keep_if=keep_if
    )
    sync_state.last_history_id = latest_history_id

    return IncrementalSyncSummary(
        scanned=len(candidate_ids),
        matched=matched,
        # ING-8's 4-category model has no separate "not one of ours" bucket -- both known
        # duplicates and (B4-only) non-matching-sender History results count as "skipped".
        skipped=skipped_duplicate + filtered_out,
        failed=failed,
        used_fallback_rescan=used_fallback,
    )
