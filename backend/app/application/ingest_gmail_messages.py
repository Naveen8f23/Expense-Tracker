"""Shared message-storing step used by both RunInitialBackfill (B3) and RunIncrementalSync (B4).

Given a list of candidate Gmail message IDs, fetches and caches each one not already present as
an unprocessed EmailMessage row (ING-6/DUP-1: never process the same message twice).
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.infrastructure import gmail_client
from app.infrastructure.models import EmailMessage, EmailMessageStatus, GmailConnection


def store_new_messages(
    session: Session,
    connection: GmailConnection,
    credentials,
    message_ids: list[str],
    *,
    keep_if=None,
) -> tuple[int, int, int, int]:
    """Returns (stored_count, skipped_duplicate_count, filtered_out_count, failed_count).

    keep_if(message) -> bool: an optional post-fetch filter, checked after the dedup check so a
    message already on disk is never re-fetched just to filter it. Used by RunIncrementalSync
    (B4) to filter Gmail History API results down to the configured senders, since (unlike
    messages.list's `q=`) History API results aren't sender-scoped -- without this hook, that
    filtering would otherwise mean a second, redundant fetch per message.

    A message that fails to fetch or read (GmailIngestionError -- e.g. it was deleted from Gmail
    after being listed but before this fetch, or has no readable text/html or text/plain body
    part) is counted as failed and the loop continues (B5, ING-8): one bad message must not block
    every other message in the same sync run from being stored. It isn't recorded as an
    EmailMessage row, so it will be retried on the next sync (not on disk yet, so not in
    existing_ids) -- fine for a parse failure, and a harmless no-op retry for a message that's
    genuinely gone. Any other exception (network, auth) is a systemic problem, not a per-message
    one, and is left to propagate and abort the run as before.
    """
    existing_ids = (
        {
            row.message_id
            for row in session.query(EmailMessage.message_id).filter(
                EmailMessage.message_id.in_(message_ids)
            )
        }
        if message_ids
        else set()
    )

    stored = 0
    skipped = 0
    filtered_out = 0
    failed = 0
    for message_id in message_ids:
        if message_id in existing_ids:
            skipped += 1
            continue
        try:
            message = gmail_client.get_message(credentials, message_id)
        except gmail_client.GmailIngestionError:
            # e.g. the message was deleted from Gmail after being listed but before this fetch --
            # a per-message condition (B5/ING-8), not a reason to abort the whole sync run.
            failed += 1
            continue
        if keep_if is not None and not keep_if(message):
            filtered_out += 1
            continue
        try:
            content = gmail_client.extract_message_content(message)
        except gmail_client.GmailIngestionError:
            failed += 1
            continue
        received_at = datetime.fromtimestamp(int(message["internalDate"]) / 1000, tz=timezone.utc)
        session.add(
            EmailMessage(
                gmail_connection_id=connection.id,
                message_id=message_id,
                thread_id=message["threadId"],
                received_at=received_at,
                status=EmailMessageStatus.UNPROCESSED,
                content=content,
            )
        )
        stored += 1
    session.commit()
    return stored, skipped, filtered_out, failed
