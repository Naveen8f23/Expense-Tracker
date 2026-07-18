from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from google.oauth2.credentials import Credentials

from app.infrastructure import gmail_oauth
from app.infrastructure.db import Base, get_db, make_engine, make_session_factory
from app.infrastructure.models import GmailConnection
from app.presentation.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Isolated DB + encryption key per test, matching test_schema.py's pattern -- never touch
    # the real app database (ARCHITECTURE.md #7).
    monkeypatch.setenv("ENCRYPTION_KEY_PATH", str(tmp_path / "secret.key"))
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)

    def _override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app), session_factory
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_pending_state(monkeypatch):
    gmail_oauth._last_issued_state = None
    gmail_oauth._pending_code_verifier = None
    # B3's backfill (chained into /gmail/callback) always fetches the mailbox's current
    # historyId to plant B4's starting checkpoint -- stub it so these route tests never need a
    # real Gmail connection just to exercise the OAuth callback itself.
    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.get_current_history_id",
        lambda credentials: "1000",
    )
    yield
    gmail_oauth._last_issued_state = None
    gmail_oauth._pending_code_verifier = None


def _fake_credentials(token="fake-token"):
    # A real exchanged credential always carries these fields (see B1's PKCE bugfix commit --
    # a bare Credentials(token=...) is missing refresh_token/client_id/client_secret, which
    # get_valid_credentials correctly rejects when the backfill step tries to load it back).
    # expiry must be explicit and far-future: Credentials.from_authorized_user_info (used when
    # the backfill step reloads these from storage) defaults expiry to "now" when it's absent
    # from the JSON, which makes .expired True and triggers a real refresh() network call.
    return Credentials(
        token=token,
        refresh_token="fake-refresh-token",  # noqa: S106
        token_uri="https://oauth2.googleapis.com/token",
        client_id="fake-client-id",
        client_secret="fake-client-secret",  # noqa: S106
        scopes=gmail_oauth.SCOPES,
        expiry=datetime.now() + timedelta(days=365),
    )


def test_connect_redirects_to_google_with_client_secrets_configured(client, tmp_path, monkeypatch):
    import json

    secrets_path = tmp_path / "gmail_client_secret.json"
    secrets_path.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "fake-client-id.apps.googleusercontent.com",
                    "client_secret": "fake-client-secret",  # noqa: S105
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8000/gmail/callback"],
                }
            }
        )
    )
    monkeypatch.setenv("GMAIL_CLIENT_SECRET_PATH", str(secrets_path))

    test_client, _ = client
    response = test_client.get("/gmail/connect", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"].startswith("https://accounts.google.com/o/oauth2/auth")


def test_connect_surfaces_missing_client_secrets_as_an_error_not_a_crash(
    client, tmp_path, monkeypatch
):
    monkeypatch.setenv("GMAIL_CLIENT_SECRET_PATH", str(tmp_path / "missing.json"))
    test_client, _ = client

    response = test_client.get("/gmail/connect", follow_redirects=False)

    assert response.status_code == 500
    assert "not found" in response.json()["detail"]


def test_callback_surfaces_denied_consent_as_a_client_error(client):
    test_client, _ = client
    response = test_client.get("/gmail/callback", params={"error": "access_denied"})
    assert response.status_code == 400
    assert "access_denied" in response.json()["detail"]


def test_callback_rejects_missing_code_or_state(client):
    test_client, _ = client
    response = test_client.get("/gmail/callback")
    assert response.status_code == 400


def test_callback_creates_an_encrypted_gmail_connection_on_success(client, monkeypatch):
    test_client, session_factory = client

    monkeypatch.setattr(gmail_oauth, "exchange_code", lambda code, state: _fake_credentials())
    monkeypatch.setattr(gmail_oauth, "fetch_connected_email", lambda credentials: "naveen@gmail.com")

    response = test_client.get("/gmail/callback", params={"code": "abc", "state": "xyz"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["email_address"] == "naveen@gmail.com"
    # No SenderRules seeded in this isolated test DB -- a real no-op, not skipped/errored.
    assert body["backfill"] == {"scanned": 0, "matched": 0, "skipped": 0, "failed": 0}

    session = session_factory()
    connection = session.query(GmailConnection).one()
    assert connection.email_address == "naveen@gmail.com"
    assert connection.tokens  # decrypted transparently by the ORM (ADR-0015)
    session.close()


def test_reconnecting_updates_the_existing_connection_rather_than_duplicating_it(
    client, monkeypatch
):
    test_client, session_factory = client
    monkeypatch.setattr(gmail_oauth, "exchange_code", lambda code, state: _fake_credentials("t1"))
    monkeypatch.setattr(gmail_oauth, "fetch_connected_email", lambda credentials: "naveen@gmail.com")
    test_client.get("/gmail/callback", params={"code": "abc", "state": "xyz"})

    monkeypatch.setattr(gmail_oauth, "exchange_code", lambda code, state: _fake_credentials("t2"))
    test_client.get("/gmail/callback", params={"code": "def", "state": "uvw"})

    session = session_factory()
    assert session.query(GmailConnection).count() == 1
    session.close()


def test_callback_runs_the_initial_backfill_and_includes_it_in_the_response(client, monkeypatch):
    from app.infrastructure.models import EmailMessage, SenderRule, TransactionType

    test_client, session_factory = client
    seed_session = session_factory()
    seed_session.add(
        SenderRule(
            sender_address="alerts@hdfcbank.bank.in",
            content_pattern_id="hdfc_upi_debit",
            transaction_type=TransactionType.UPI_DEBIT,
        )
    )
    seed_session.commit()
    seed_session.close()

    monkeypatch.setattr(gmail_oauth, "exchange_code", lambda code, state: _fake_credentials())
    monkeypatch.setattr(gmail_oauth, "fetch_connected_email", lambda credentials: "naveen@gmail.com")
    monkeypatch.setattr(
        "app.application.run_initial_backfill.gmail_client.list_message_ids",
        lambda credentials, query: ["msg-1"],
    )
    monkeypatch.setattr(
        "app.application.ingest_gmail_messages.gmail_client.get_message",
        lambda credentials, message_id: {
            "id": message_id,
            "threadId": "thread-1",
            "internalDate": "1721318400000",
        },
    )
    monkeypatch.setattr(
        "app.application.ingest_gmail_messages.gmail_client.extract_message_content",
        lambda message: "Rs.120.00 is debited from your account ending 4958",
    )

    response = test_client.get("/gmail/callback", params={"code": "abc", "state": "xyz"})

    assert response.status_code == 200
    assert response.json()["backfill"] == {"scanned": 1, "matched": 1, "skipped": 0, "failed": 0}

    session = session_factory()
    stored = session.query(EmailMessage).one()
    assert stored.message_id == "msg-1"
    assert stored.content == "Rs.120.00 is debited from your account ending 4958"
    session.close()


def test_callback_surfaces_exchange_failure_as_a_client_error_not_a_crash(client, monkeypatch):
    test_client, _ = client

    def _raise(*args, **kwargs):
        raise gmail_oauth.GmailAuthError("state mismatch -- possible CSRF")

    monkeypatch.setattr(gmail_oauth, "exchange_code", _raise)

    response = test_client.get("/gmail/callback", params={"code": "abc", "state": "wrong"})

    assert response.status_code == 400
    assert "state mismatch" in response.json()["detail"]
