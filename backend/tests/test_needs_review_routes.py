"""BACKLOG.md E5: needs-review queue endpoint."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import Base, get_db, make_engine, make_session_factory
from app.infrastructure.models import (
    DebitOrCredit,
    EmailMessage,
    EmailMessageStatus,
    GmailConnection,
    Payee,
    PaymentMethod,
    ReviewStatus,
    Transaction,
)
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


def test_combines_unmatched_emails_and_low_confidence_transactions(client):
    test_client, session_factory = client
    session = session_factory()
    user = ensure_default_user(session)
    conn = GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}")
    session.add(conn)
    session.commit()

    unmatched_email = EmailMessage(
        gmail_connection_id=conn.id,
        message_id="msg-unmatched",
        thread_id="thread-unmatched",
        received_at=datetime.now(timezone.utc),
        status=EmailMessageStatus.NEEDS_REVIEW,
        content="Some unrecognized HDFC email",
        classified_pattern_id=None,
    )
    matched_email = EmailMessage(
        gmail_connection_id=conn.id,
        message_id="msg-matched",
        thread_id="thread-matched",
        received_at=datetime.now(timezone.utc),
        status=EmailMessageStatus.MATCHED,
        content="Dear Customer, ...",
    )
    session.add_all([unmatched_email, matched_email])
    session.flush()

    payee = Payee(name="FAKE", identifier="fake@upi")
    session.add(payee)
    session.flush()

    low_confidence_txn = Transaction(
        user_id=user.id,
        amount=Decimal("42.00"),
        currency="INR",
        txn_date=datetime.now(timezone.utc).date(),
        payee_id=payee.id,
        instrument_last4="0000",
        payment_method=PaymentMethod.UPI,
        txn_type=DebitOrCredit.DEBIT,
        confidence_score=0.4,
        review_status=ReviewStatus.NEEDS_REVIEW,
        email_message_id=matched_email.id,
    )
    session.add(low_confidence_txn)
    session.commit()
    session.close()

    response = test_client.get("/needs-review")

    assert response.status_code == 200
    body = response.json()
    assert [e["message_id"] for e in body["unmatched_emails"]] == ["msg-unmatched"]
    assert len(body["low_confidence_transactions"]) == 1
    assert body["low_confidence_transactions"][0]["confidence_score"] == 0.4


def test_empty_queue_when_nothing_needs_review(client):
    test_client, session_factory = client
    session = session_factory()
    ensure_default_user(session)
    session.close()

    response = test_client.get("/needs-review")

    assert response.status_code == 200
    body = response.json()
    assert body == {"unmatched_emails": [], "low_confidence_transactions": []}
