from datetime import datetime, timezone

import pytest

from app.application.ingest_gmail_messages import store_new_messages
from app.infrastructure import gmail_client
from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import Base, make_engine, make_session_factory
from app.infrastructure.models import EmailMessage, EmailMessageStatus, GmailConnection


@pytest.fixture()
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY_PATH", str(tmp_path / "secret.key"))
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    Session = make_session_factory(engine)
    yield Session()


@pytest.fixture()
def connection(session):
    user = ensure_default_user(session)
    conn = GmailConnection(
        user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}"
    )
    session.add(conn)
    session.commit()
    return conn


def _fake_message(message_id):
    return {"id": message_id, "threadId": f"thread-{message_id}", "internalDate": "1721318400000"}


def test_one_unreadable_message_is_counted_failed_without_blocking_the_rest(
    session, connection, monkeypatch
):
    # B5/ING-8: an oddly formatted email must not prevent the other, perfectly good emails in
    # the same sync run from being stored.
    monkeypatch.setattr(gmail_client, "get_message", lambda credentials, message_id: _fake_message(message_id))

    def fake_extract(message):
        if message["id"] == "msg-bad":
            raise gmail_client.GmailIngestionError("no readable body part")
        return f"content for {message['id']}"

    monkeypatch.setattr(gmail_client, "extract_message_content", fake_extract)

    matched, skipped, filtered_out, failed = store_new_messages(
        session, connection, credentials=None, message_ids=["msg-good-1", "msg-bad", "msg-good-2"]
    )

    assert matched == 2
    assert skipped == 0
    assert filtered_out == 0
    assert failed == 1

    stored_ids = {row.message_id for row in session.query(EmailMessage).all()}
    assert stored_ids == {"msg-good-1", "msg-good-2"}


def test_a_message_that_404s_on_fetch_is_counted_failed_without_blocking_the_rest(
    session, connection, monkeypatch
):
    # A message deleted from Gmail after being listed but before this fetch (real 2026-07-22
    # incident: an unrelated 404 during sync aborted the whole run, since the fetch call wasn't
    # wrapped the same way the parse step already was) must not block the other messages either.
    def fake_get_message(credentials, message_id):
        if message_id == "msg-deleted":
            raise gmail_client.GmailIngestionError("Message msg-deleted no longer exists in Gmail")
        return _fake_message(message_id)

    monkeypatch.setattr(gmail_client, "get_message", fake_get_message)
    monkeypatch.setattr(gmail_client, "extract_message_content", lambda message: f"content for {message['id']}")

    matched, skipped, filtered_out, failed = store_new_messages(
        session, connection, credentials=None, message_ids=["msg-good-1", "msg-deleted", "msg-good-2"]
    )

    assert matched == 2
    assert skipped == 0
    assert filtered_out == 0
    assert failed == 1

    stored_ids = {row.message_id for row in session.query(EmailMessage).all()}
    assert stored_ids == {"msg-good-1", "msg-good-2"}


def test_a_failed_message_is_not_recorded_so_it_will_be_retried_next_sync(
    session, connection, monkeypatch
):
    monkeypatch.setattr(gmail_client, "get_message", lambda credentials, message_id: _fake_message(message_id))
    monkeypatch.setattr(
        gmail_client,
        "extract_message_content",
        lambda message: (_ for _ in ()).throw(gmail_client.GmailIngestionError("broken")),
    )

    store_new_messages(session, connection, credentials=None, message_ids=["msg-1"])

    assert session.query(EmailMessage).count() == 0


def test_keep_if_filter_runs_after_the_dedup_check(session, connection, monkeypatch):
    session.add(
        EmailMessage(
            gmail_connection_id=connection.id,
            message_id="msg-existing",
            thread_id="thread-existing",
            received_at=datetime.now(timezone.utc),
            status=EmailMessageStatus.UNPROCESSED,
            content="already ingested",
        )
    )
    session.commit()

    fetch_calls = []
    monkeypatch.setattr(
        gmail_client,
        "get_message",
        lambda credentials, message_id: fetch_calls.append(message_id) or _fake_message(message_id),
    )

    matched, skipped, filtered_out, failed = store_new_messages(
        session,
        connection,
        credentials=None,
        message_ids=["msg-existing"],
        keep_if=lambda message: False,
    )

    assert skipped == 1
    assert filtered_out == 0
    assert fetch_calls == []  # never fetched -- the dedup check short-circuits before keep_if
