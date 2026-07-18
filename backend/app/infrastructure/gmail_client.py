"""Gmail message search/fetch (B3, REQUIREMENTS.md ING-3/ING-4/ING-7).

Uses Google's official client libraries (ADR-0018), same as gmail_oauth.py -- kept in a
separate module since OAuth/credential concerns and message-fetch concerns are conceptually
distinct (ARCHITECTURE.md #3 Ingestion module).
"""

import base64
from datetime import date

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# google-api-python-client's built-in exponential backoff/retry for transient errors (429/5xx) --
# this, not hand-rolled retry logic, is exactly what ADR-0018 chose these libraries for (ING-7).
_NUM_RETRIES = 5


class GmailIngestionError(Exception):
    """Raised when a fetched message can't be read at all (e.g. no text body part found).

    Always surfaced (ING-8), never silently skipped or guessed at.
    """


class HistoryCheckpointExpiredError(Exception):
    """Raised when a stored historyId falls outside Gmail's History API retention window.

    The caller (B4) should fall back to a bounded re-scan rather than fail silently (ING-4).
    """


def _build_service(credentials):
    return build(
        "gmail", "v1", credentials=credentials, cache_discovery=False, static_discovery=True
    )


def build_search_query(sender_addresses: list[str], after: date) -> str:
    senders = " OR ".join(f"from:{address}" for address in sender_addresses)
    return f"({senders}) after:{after.strftime('%Y/%m/%d')}"


def list_message_ids(credentials, query: str) -> list[str]:
    """Return every matching message ID, following Gmail's pagination (ING-7) to completion."""
    service = _build_service(credentials)
    message_ids: list[str] = []
    page_token = None
    while True:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=page_token)
            .execute(num_retries=_NUM_RETRIES)
        )
        message_ids.extend(message["id"] for message in response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return message_ids


def get_message(credentials, message_id: str) -> dict:
    service = _build_service(credentials)
    return (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute(num_retries=_NUM_RETRIES)
    )


def get_current_history_id(credentials) -> str:
    service = _build_service(credentials)
    profile = service.users().getProfile(userId="me").execute(num_retries=_NUM_RETRIES)
    return profile["historyId"]


def list_message_ids_since_history(credentials, start_history_id: str) -> tuple[list[str], str]:
    """Return (new_message_ids, latest_history_id) since start_history_id (ING-4/ING-5).

    Only covers messages *added* to the mailbox -- deletions/label changes are irrelevant here,
    since this system only ever reads, never modifies or deletes (ING-2). Raises
    HistoryCheckpointExpiredError if Gmail rejects the checkpoint as too old (a 404), so the
    caller can fall back to a bounded re-scan instead of failing silently.
    """
    service = _build_service(credentials)
    message_ids: list[str] = []
    page_token = None
    latest_history_id = start_history_id
    try:
        while True:
            response = (
                service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=start_history_id,
                    historyTypes=["messageAdded"],
                    pageToken=page_token,
                )
                .execute(num_retries=_NUM_RETRIES)
            )
            for record in response.get("history", []):
                message_ids.extend(
                    added["message"]["id"] for added in record.get("messagesAdded", [])
                )
            latest_history_id = response.get("historyId", latest_history_id)
            page_token = response.get("nextPageToken")
            if not page_token:
                return message_ids, latest_history_id
    except HttpError as exc:
        if exc.resp.status == 404:
            raise HistoryCheckpointExpiredError(str(exc)) from exc
        raise


def message_sender_matches(message: dict, sender_addresses: set[str]) -> bool:
    """History API results aren't scoped to a sender query like messages.list is -- this checks
    the fetched message's From header against the configured SenderRule addresses (ING-3a)."""
    headers = message.get("payload", {}).get("headers", [])
    from_header = next((h["value"] for h in headers if h.get("name", "").lower() == "from"), "")
    return any(address in from_header for address in sender_addresses)


def _decode_body_data(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)  # Gmail's base64url omits padding; restore it
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _find_best_body_part(payload: dict) -> dict | None:
    """Depth-first search for the best MIME part to cache.

    Prefers text/html: HDFC's real templates (Appendix A) are HTML with the transactional
    details as plain text within it -- keeping the HTML preserves the original formatting for
    later source-email viewing (TRC-2/F3), and content-pattern matching (Epic C) still works
    fine via substring search regardless of the surrounding markup. Falls back to text/plain
    only if no HTML part exists at all.
    """
    stack = [payload]
    html_part = None
    plain_part = None
    while stack:
        part = stack.pop()
        mime_type = part.get("mimeType", "")
        has_data = bool(part.get("body", {}).get("data"))
        if mime_type == "text/html" and has_data and html_part is None:
            html_part = part
        elif mime_type == "text/plain" and has_data and plain_part is None:
            plain_part = part
        stack.extend(part.get("parts", []))
    return html_part or plain_part


def extract_message_content(message: dict) -> str:
    payload = message.get("payload", {})
    if not payload.get("parts") and payload.get("body", {}).get("data"):
        return _decode_body_data(payload["body"]["data"])
    part = _find_best_body_part(payload)
    if part is None:
        raise GmailIngestionError(
            f"Message {message.get('id')} has no readable text/html or text/plain body part"
        )
    return _decode_body_data(part["body"]["data"])
