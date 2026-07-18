from datetime import datetime, timedelta, timezone

import pytest
from google.oauth2.credentials import Credentials

from app.application.run_initial_backfill import BackfillSummary, run_initial_backfill
from app.infrastructure import gmail_client
from app.infrastructure.bootstrap import ensure_default_user, ensure_hdfc_sender_rules
from app.infrastructure.db import Base, make_engine, make_session_factory
from app.infrastructure.models import EmailMessage, EmailMessageStatus, GmailConnection, SyncState


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
    # expiry must be explicit and far-future: from_authorized_user_info (used when the backfill
    # step reloads these from storage) defaults expiry to "now" when absent from the JSON,
    # which makes .expired True and triggers a real refresh() network call in these tests.
    fake_credentials = Credentials(
        token="fake-token",  # noqa: S106
        refresh_token="fake-refresh-token",  # noqa: S106
        token_uri="https://oauth2.googleapis.com/token",
        client_id="fake-client-id",
        client_secret="fake-client-secret",  # noqa: S106
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        expiry=datetime.now() + timedelta(days=365),
    )
    conn = GmailConnection(
        user_id=user.id,
        email_address="naveen8f23@gmail.com",
        tokens=fake_credentials.to_json(),
        created_at=datetime(2026, 7, 15, tzinfo=timezone.utc),  # mid-July -> backfill from July 1
    )
    session.add(conn)
    session.commit()
    return conn


@pytest.fixture(autouse=True)
def _stub_current_history_id(monkeypatch):
    # B3 plants the starting checkpoint for RunIncrementalSync (B4) by fetching the mailbox's
    # current historyId -- stub it by default so tests don't need a real Gmail connection;
    # individual tests can still override this via monkeypatch if they care about the value.
    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.get_current_history_id",
        lambda credentials: "1000",
    )


def test_no_op_when_no_sender_rules_are_configured(session, connection):
    summary = run_initial_backfill(session, connection)
    assert summary.scanned == 0
    assert summary.matched == 0
    assert summary.skipped == 0


def test_plants_the_starting_history_id_checkpoint_for_b4(session, connection, monkeypatch):
    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.get_current_history_id",
        lambda credentials: "424242",
    )
    run_initial_backfill(session, connection)
    sync_state = session.query(SyncState).filter_by(gmail_connection_id=connection.id).one()
    assert sync_state.last_history_id == "424242"


def test_stores_new_messages_and_updates_sync_state(session, connection, monkeypatch):
    ensure_hdfc_sender_rules(session)

    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.build_search_query",
        lambda senders, after: f"query-from-{after.isoformat()}",
    )
    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.list_message_ids",
        lambda credentials, query: ["msg-1", "msg-2"],
    )

    def fake_get_message(credentials, message_id):
        return {"id": message_id, "threadId": f"thread-{message_id}", "internalDate": "1721318400000"}

    monkeypatch.setattr(
        "app.application.ingest_gmail_messages.gmail_client.get_message", fake_get_message
    )
    monkeypatch.setattr(
        "app.application.ingest_gmail_messages.gmail_client.extract_message_content",
        lambda message: f"content for {message['id']}",
    )

    summary = run_initial_backfill(session, connection)

    assert summary.scanned == 2
    assert summary.matched == 2
    assert summary.skipped == 0

    stored = {row.message_id: row for row in session.query(EmailMessage).all()}
    assert set(stored) == {"msg-1", "msg-2"}
    assert stored["msg-1"].content == "content for msg-1"
    assert stored["msg-1"].gmail_connection_id == connection.id

    sync_state = session.query(SyncState).filter_by(gmail_connection_id=connection.id).one()
    assert sync_state.last_sync_at is not None
    assert sync_state.last_error is None


def test_records_start_time_and_scan_counts_on_sync_state_b5(session, connection, monkeypatch):
    ensure_hdfc_sender_rules(session)
    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.list_message_ids",
        lambda credentials, query: ["msg-1", "msg-2"],
    )
    monkeypatch.setattr(
        "app.application.ingest_gmail_messages.gmail_client.get_message",
        lambda credentials, message_id: {
            "id": message_id,
            "threadId": "thread-1",
            "internalDate": "1721318400000",
        },
    )

    def fake_extract(message):
        if message["id"] == "msg-2":
            raise gmail_client.GmailIngestionError("bad")
        return "content"

    monkeypatch.setattr(
        "app.application.ingest_gmail_messages.gmail_client.extract_message_content", fake_extract
    )

    before = datetime.now(timezone.utc)
    summary = run_initial_backfill(session, connection)
    after = datetime.now(timezone.utc)

    assert summary == BackfillSummary(scanned=2, matched=1, skipped=0, failed=1)

    sync_state = session.query(SyncState).filter_by(gmail_connection_id=connection.id).one()
    assert before <= sync_state.last_sync_started_at.replace(tzinfo=timezone.utc) <= after
    assert sync_state.last_scanned == 2
    assert sync_state.last_matched == 1
    assert sync_state.last_skipped == 0
    assert sync_state.last_failed == 1


def test_uses_the_first_of_the_connection_setup_month_not_todays_date(
    session, connection, monkeypatch
):
    ensure_hdfc_sender_rules(session)
    captured = {}

    def fake_build_search_query(senders, after):
        captured["after"] = after
        return "some-query"

    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.build_search_query",
        fake_build_search_query,
    )
    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.list_message_ids",
        lambda credentials, query: [],
    )

    run_initial_backfill(session, connection)

    assert captured["after"].isoformat() == "2026-07-01"  # connection created 2026-07-15


def test_skips_messages_already_stored_ing6_dup1(session, connection, monkeypatch):
    ensure_hdfc_sender_rules(session)
    session.add(
        EmailMessage(
            gmail_connection_id=connection.id,
            message_id="msg-1",
            thread_id="thread-1",
            received_at=datetime.now(timezone.utc),
            status=EmailMessageStatus.UNPROCESSED,
            content="already ingested",
        )
    )
    session.commit()

    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.list_message_ids",
        lambda credentials, query: ["msg-1", "msg-2"],
    )
    monkeypatch.setattr(
        "app.application.ingest_gmail_messages.gmail_client.get_message",
        lambda credentials, message_id: {
            "id": message_id,
            "threadId": "thread-2",
            "internalDate": "1721318400000",
        },
    )
    monkeypatch.setattr(
        "app.application.ingest_gmail_messages.gmail_client.extract_message_content",
        lambda message: "new content",
    )

    summary = run_initial_backfill(session, connection)

    assert summary.scanned == 2
    assert summary.matched == 1
    assert summary.skipped == 1
    assert session.query(EmailMessage).count() == 2  # not duplicated, not re-fetched-and-added


def test_refreshed_tokens_are_written_back_to_the_connection(session, connection, monkeypatch):
    ensure_hdfc_sender_rules(session)

    def fake_get_valid_credentials(stored_json):
        return Credentials(token="refreshed-token"), '{"token": "refreshed-token-json"}'  # noqa: S106

    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_oauth.get_valid_credentials",
        fake_get_valid_credentials,
    )
    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.list_message_ids",
        lambda credentials, query: [],
    )

    run_initial_backfill(session, connection)

    session.refresh(connection)
    assert connection.tokens == '{"token": "refreshed-token-json"}'


def test_a_failure_surfaces_via_sync_state_last_error_and_re_raises(session, connection, monkeypatch):
    ensure_hdfc_sender_rules(session)
    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.list_message_ids",
        lambda credentials, query: (_ for _ in ()).throw(RuntimeError("Gmail API exploded")),
    )

    with pytest.raises(RuntimeError, match="Gmail API exploded"):
        run_initial_backfill(session, connection)

    sync_state = session.query(SyncState).filter_by(gmail_connection_id=connection.id).one()
    assert sync_state.last_error == "Gmail API exploded"


def test_a_failed_oauth_token_refresh_surfaces_via_sync_state_not_just_a_stack_trace(
    session, connection, monkeypatch
):
    # B5's literal acceptance criterion: "A failed OAuth refresh (from B1) shows up here, not
    # just in a stack trace." get_valid_credentials already raises GmailAuthError on a failed
    # refresh (B1) -- this confirms that specifically propagates into sync_state.last_error.
    from app.infrastructure.gmail_oauth import GmailAuthError

    def raise_auth_error(stored_json):
        raise GmailAuthError("Gmail token refresh failed: access revoked")

    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_oauth.get_valid_credentials", raise_auth_error
    )

    with pytest.raises(GmailAuthError, match="access revoked"):
        run_initial_backfill(session, connection)

    sync_state = session.query(SyncState).filter_by(gmail_connection_id=connection.id).one()
    assert sync_state.last_error == "Gmail token refresh failed: access revoked"
    assert sync_state.last_sync_started_at is not None
