from datetime import datetime, timezone

import pytest

from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import Base, make_engine, make_session_factory
from app.infrastructure.models import EmailMessage, EmailMessageStatus, GmailConnection, Payee, User


@pytest.fixture()
def session_factory(tmp_path, monkeypatch):
    # Isolated per-test SQLite file (not :memory:, so we can inspect the raw bytes below)
    # and an isolated encryption key, so tests never touch the real app database/key.
    monkeypatch.setenv("ENCRYPTION_KEY_PATH", str(tmp_path / "secret.key"))
    db_path = tmp_path / "test.db"
    engine = make_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    yield make_session_factory(engine), db_path


def test_all_core_tables_exist(session_factory):
    _, db_path = session_factory
    import sqlite3

    con = sqlite3.connect(db_path)
    tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    expected = {
        "users",
        "gmail_connections",
        "sender_rules",
        "email_messages",
        "sync_state",
        "transactions",
        "payees",
        "categories",
        "correction_log",
    }
    assert expected.issubset(tables)


def test_ensure_default_user_is_idempotent(session_factory):
    Session, _ = session_factory
    session = Session()
    first = ensure_default_user(session)
    second = ensure_default_user(session)
    assert first.id == second.id
    assert session.query(User).count() == 1


def test_sensitive_fields_are_encrypted_at_rest(session_factory):
    """ADR-0015: gmail_connections.tokens and email_messages.content must not be
    human-readable in the raw database file, while ordinary columns (e.g. a payee name)
    remain plain — this is a field-level guarantee, not whole-file encryption."""
    Session, db_path = session_factory
    session = Session()

    user = ensure_default_user(session)
    secret_token = "ya29.super-secret-oauth-token"  # noqa: S105 (test fixture value)
    conn = GmailConnection(user_id=user.id, email_address="me@gmail.com", tokens=secret_token)
    session.add(conn)

    secret_email_body = "Rs.120.00 is debited from your account ending 4958"
    plain_payee_name = "GOLKONDAS CAFE"
    payee = Payee(name=plain_payee_name)
    session.add(payee)
    session.flush()

    msg = EmailMessage(
        gmail_connection_id=conn.id,
        message_id="msg-1",
        thread_id="thread-1",
        received_at=datetime.now(timezone.utc),
        status=EmailMessageStatus.MATCHED,
        content=secret_email_body,
    )
    session.add(msg)
    session.commit()

    raw_bytes = db_path.read_bytes()

    assert secret_token.encode() not in raw_bytes
    assert secret_email_body.encode() not in raw_bytes
    # Sanity check the test itself: an unencrypted column's value SHOULD be found as
    # plaintext, proving this is field-level (not whole-file) encryption as designed.
    assert plain_payee_name.encode() in raw_bytes

    # And the ORM must transparently decrypt on read.
    session.expire_all()
    reloaded_conn = session.get(GmailConnection, conn.id)
    reloaded_msg = session.get(EmailMessage, msg.id)
    assert reloaded_conn.tokens == secret_token
    assert reloaded_msg.content == secret_email_body
