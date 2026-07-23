import base64

import pytest

from app.infrastructure import gmail_client


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def test_build_search_query_ors_senders_and_applies_after_date():
    import datetime

    query = gmail_client.build_search_query(
        ["alerts@hdfcbank.bank.in", "alerts@icicibank.com"], datetime.date(2026, 7, 1)
    )
    assert query == "(from:alerts@hdfcbank.bank.in OR from:alerts@icicibank.com) after:2026/07/01"


def test_list_message_ids_follows_pagination_to_completion(monkeypatch):
    pages = [
        {"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "page2"},
        {"messages": [{"id": "c"}]},
    ]

    class _Execution:
        def __init__(self, index):
            self.index = index

        def execute(self, num_retries=0):
            return pages[self.index]

    class _FakeMessages:
        def __init__(self):
            self.calls = 0

        def list(self, userId, q, pageToken=None):
            execution = _Execution(self.calls)
            self.calls += 1
            return execution

    fake_messages = _FakeMessages()

    class _FakeUsers:
        def messages(self):
            return fake_messages

    class _FakeService:
        def users(self):
            return _FakeUsers()

    monkeypatch.setattr(gmail_client, "build", lambda *a, **k: _FakeService())

    ids = gmail_client.list_message_ids(credentials=None, query="from:x")
    assert ids == ["a", "b", "c"]
    assert fake_messages.calls == 2


class _FakeHttpResponse:
    """Minimal stand-in for the `httplib2.Response`-like object `HttpError` wraps -- only
    `.status` is actually read by `get_message`'s own error-handling (`exc.resp.status`)."""

    def __init__(self, status):
        self.status = status
        self.reason = "error"


def _fake_http_error(status):
    from googleapiclient.errors import HttpError

    return HttpError(_FakeHttpResponse(status), b'{"error": {"message": "boom"}}')


def _fake_service_raising(exc):
    class _FakeExecution:
        def execute(self, num_retries=0):
            raise exc

    class _FakeMessages:
        def get(self, userId, id, format):
            return _FakeExecution()

    class _FakeUsers:
        def messages(self):
            return _FakeMessages()

    class _FakeService:
        def users(self):
            return _FakeUsers()

    return _FakeService()


def test_get_message_translates_a_404_into_gmail_ingestion_error(monkeypatch):
    # The real 2026-07-22 incident: a message deleted from Gmail between being listed and this
    # fetch -- a per-message condition (ING-8), not a reason to abort the whole sync run.
    monkeypatch.setattr(
        gmail_client, "build", lambda *a, **k: _fake_service_raising(_fake_http_error(404))
    )

    with pytest.raises(gmail_client.GmailIngestionError):
        gmail_client.get_message(credentials=None, message_id="msg-deleted")


def test_get_message_lets_a_non_404_error_propagate_unchanged(monkeypatch):
    # A 401/403/5xx is a systemic problem (auth, quota, Gmail outage), not a per-message one --
    # it must still abort the run rather than being silently absorbed as "just one bad message."
    from googleapiclient.errors import HttpError

    monkeypatch.setattr(
        gmail_client, "build", lambda *a, **k: _fake_service_raising(_fake_http_error(500))
    )

    with pytest.raises(HttpError):
        gmail_client.get_message(credentials=None, message_id="msg-x")


def test_extract_message_content_from_single_part_message():
    message = {"payload": {"body": {"data": _b64url("plain single-part body")}}}
    assert gmail_client.extract_message_content(message) == "plain single-part body"


def test_extract_message_content_prefers_html_over_plain_text():
    message = {
        "payload": {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url("plain version")}},
                {"mimeType": "text/html", "body": {"data": _b64url("<p>html version</p>")}},
            ],
        }
    }
    assert gmail_client.extract_message_content(message) == "<p>html version</p>"


def test_extract_message_content_falls_back_to_plain_text_when_no_html_part():
    message = {
        "payload": {
            "mimeType": "multipart/alternative",
            "parts": [{"mimeType": "text/plain", "body": {"data": _b64url("plain only")}}],
        }
    }
    assert gmail_client.extract_message_content(message) == "plain only"


def test_extract_message_content_finds_html_nested_inside_multipart_mixed():
    # Real emails can nest multipart/alternative inside multipart/mixed (e.g. alongside an
    # attachment) -- the search must recurse, not just look one level deep.
    message = {
        "payload": {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {"mimeType": "text/html", "body": {"data": _b64url("<p>nested</p>")}},
                    ],
                },
                {"mimeType": "application/pdf", "body": {"data": _b64url("not real pdf bytes")}},
            ],
        }
    }
    assert gmail_client.extract_message_content(message) == "<p>nested</p>"


def test_extract_message_content_raises_when_no_readable_body_part_exists():
    message = {
        "id": "msg-x",
        "payload": {
            "mimeType": "multipart/mixed",
            "parts": [{"mimeType": "application/pdf", "body": {"data": _b64url("pdf bytes")}}],
        },
    }
    with pytest.raises(gmail_client.GmailIngestionError, match="msg-x"):
        gmail_client.extract_message_content(message)
