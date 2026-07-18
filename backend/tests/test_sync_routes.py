"""BACKLOG.md E7: sync health status endpoint."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import Base, get_db, make_engine, make_session_factory
from app.infrastructure.models import GmailConnection, SyncState
from app.presentation.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
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


def test_returns_404_when_no_gmail_connection_exists(client):
    test_client, session_factory = client
    session = session_factory()
    ensure_default_user(session)
    session.close()

    response = test_client.get("/sync/status")

    assert response.status_code == 404


def test_returns_connected_but_not_synced_before_the_first_backfill(client):
    test_client, session_factory = client
    session = session_factory()
    user = ensure_default_user(session)
    session.add(GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}"))
    session.commit()
    session.close()

    response = test_client.get("/sync/status")

    assert response.status_code == 200
    body = response.json()
    assert body == {"connected": True, "email_address": "naveen8f23@gmail.com", "synced": False}


def test_returns_full_sync_health_after_a_sync_run(client):
    test_client, session_factory = client
    session = session_factory()
    user = ensure_default_user(session)
    conn = GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}")
    session.add(conn)
    session.commit()
    now = datetime.now(timezone.utc)
    session.add(
        SyncState(
            gmail_connection_id=conn.id,
            last_history_id="12345",
            last_sync_started_at=now,
            last_sync_at=now,
            last_error=None,
            last_scanned=6,
            last_matched=0,
            last_skipped=6,
            last_failed=0,
        )
    )
    session.commit()
    session.close()

    response = test_client.get("/sync/status")

    assert response.status_code == 200
    body = response.json()
    assert body["synced"] is True
    assert body["last_scanned"] == 6
    assert body["last_skipped"] == 6
    assert body["last_error"] is None
