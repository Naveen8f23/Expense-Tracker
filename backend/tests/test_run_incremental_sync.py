from datetime import datetime, timedelta, timezone

import pytest
from google.oauth2.credentials import Credentials

from app.application.run_incremental_sync import (
    NoSyncCheckpointError,
    run_incremental_sync,
)
from app.infrastructure import gmail_client
from app.infrastructure.bootstrap import ensure_default_user, ensure_hdfc_sender_rules
from app.infrastructure.db import Base, make_engine, make_session_factory
from app.infrastructure.models import EmailMessage, GmailConnection, SyncState


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
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    session.add(conn)
    session.commit()
    return conn


@pytest.fixture()
def synced_state(session, connection):
    """A connection that's already been through its initial backfill (B3) -- has a checkpoint."""
    state = SyncState(gmail_connection_id=connection.id, last_history_id="1000")
    session.add(state)
    session.commit()
    return state


def test_raises_if_no_prior_backfill_checkpoint_exists(session, connection):
    with pytest.raises(NoSyncCheckpointError):
        run_incremental_sync(session, connection)


def test_stores_new_messages_since_the_checkpoint_and_advances_it(
    session, connection, synced_state, monkeypatch
):
    ensure_hdfc_sender_rules(session)

    monkeypatch.setattr(
        gmail_client,
        "list_message_ids_since_history",
        lambda credentials, start_history_id: (["msg-1"], "2000"),
    )
    monkeypatch.setattr(
        gmail_client,
        "get_message",
        lambda credentials, message_id: {
            "id": message_id,
            "threadId": "thread-1",
            "internalDate": "1721318400000",
            "payload": {"headers": [{"name": "From", "value": "HDFC <alerts@hdfcbank.bank.in>"}]},
        },
    )
    monkeypatch.setattr(gmail_client, "extract_message_content", lambda message: "new alert")

    summary = run_incremental_sync(session, connection)

    assert summary.scanned == 1
    assert summary.matched == 1
    assert summary.skipped == 0
    assert summary.used_fallback_rescan is False

    session.refresh(synced_state)
    assert synced_state.last_history_id == "2000"
    assert session.query(EmailMessage).count() == 1


def test_a_repeat_sync_with_no_new_mail_stores_nothing_idempotent(
    session, connection, synced_state, monkeypatch
):
    ensure_hdfc_sender_rules(session)
    monkeypatch.setattr(
        gmail_client, "list_message_ids_since_history", lambda credentials, start_history_id: ([], "1500")
    )

    summary = run_incremental_sync(session, connection)

    assert summary.scanned == 0
    assert summary.matched == 0
    assert session.query(EmailMessage).count() == 0


def test_filters_out_history_results_from_unconfigured_senders(
    session, connection, synced_state, monkeypatch
):
    ensure_hdfc_sender_rules(session)
    monkeypatch.setattr(
        gmail_client,
        "list_message_ids_since_history",
        lambda credentials, start_history_id: (["msg-unrelated"], "2000"),
    )
    monkeypatch.setattr(
        gmail_client,
        "get_message",
        lambda credentials, message_id: {
            "id": message_id,
            "threadId": "thread-x",
            "internalDate": "1721318400000",
            "payload": {"headers": [{"name": "From", "value": "Newsletter <hello@example.com>"}]},
        },
    )

    summary = run_incremental_sync(session, connection)

    assert summary.matched == 0
    assert session.query(EmailMessage).count() == 0
    # the checkpoint still advances even though nothing matched -- otherwise the next sync
    # would re-scan the same irrelevant history forever
    session.refresh(synced_state)
    assert synced_state.last_history_id == "2000"


def test_falls_back_to_a_bounded_rescan_when_the_checkpoint_has_expired(
    session, connection, synced_state, monkeypatch
):
    ensure_hdfc_sender_rules(session)
    synced_state.last_sync_at = datetime(2026, 7, 10, tzinfo=timezone.utc)
    session.commit()

    def raise_expired(credentials, start_history_id):
        raise gmail_client.HistoryCheckpointExpiredError("checkpoint too old")

    monkeypatch.setattr(gmail_client, "list_message_ids_since_history", raise_expired)

    captured_after = {}

    def fake_build_search_query(senders, after):
        captured_after["after"] = after
        return "fallback-query"

    monkeypatch.setattr(gmail_client, "build_search_query", fake_build_search_query)
    monkeypatch.setattr(gmail_client, "list_message_ids", lambda credentials, query: ["msg-2"])
    monkeypatch.setattr(gmail_client, "get_current_history_id", lambda credentials: "9999")
    monkeypatch.setattr(
        gmail_client,
        "get_message",
        lambda credentials, message_id: {
            "id": message_id,
            "threadId": "thread-2",
            "internalDate": "1721318400000",
        },
    )
    monkeypatch.setattr(gmail_client, "extract_message_content", lambda message: "rescanned content")

    original_last_sync_at = synced_state.last_sync_at  # captured before the call overwrites it

    summary = run_incremental_sync(session, connection)

    assert summary.used_fallback_rescan is True
    assert summary.matched == 1
    # bounded re-scan uses the *previous* sync time, not ADR-0011's original backfill-month window
    assert captured_after["after"] == original_last_sync_at.date()

    session.refresh(synced_state)
    assert synced_state.last_history_id == "9999"


def test_a_failure_surfaces_via_sync_state_last_error_and_re_raises(
    session, connection, synced_state, monkeypatch
):
    ensure_hdfc_sender_rules(session)

    def raise_runtime_error(credentials, start_history_id):
        raise RuntimeError("Gmail API exploded")

    monkeypatch.setattr(gmail_client, "list_message_ids_since_history", raise_runtime_error)

    with pytest.raises(RuntimeError, match="Gmail API exploded"):
        run_incremental_sync(session, connection)

    session.refresh(synced_state)
    assert synced_state.last_error == "Gmail API exploded"
