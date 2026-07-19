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


def test_a_dismissed_transaction_no_longer_appears_in_the_queue(client):
    # Found via live browser verification (Epic F, 2026-07-19): dismissing a low-confidence
    # transaction (E4, "not a real expense") didn't remove it from the needs-review queue,
    # because its review_status never actually changes from NEEDS_REVIEW -- only `dismissed`
    # does. The queue must still respect that decision.
    test_client, session_factory = client
    session = session_factory()
    user = ensure_default_user(session)
    conn = GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}")
    session.add(conn)
    session.commit()
    email = EmailMessage(
        gmail_connection_id=conn.id,
        message_id="msg-matched",
        thread_id="thread-matched",
        received_at=datetime.now(timezone.utc),
        status=EmailMessageStatus.MATCHED,
        content="Dear Customer, ...",
    )
    session.add(email)
    session.flush()
    payee = Payee(name="FAKE", identifier="fake@upi")
    session.add(payee)
    session.flush()
    txn = Transaction(
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
        email_message_id=email.id,
    )
    session.add(txn)
    session.commit()
    txn_id = txn.id
    session.close()

    dismiss_response = test_client.post(f"/transactions/{txn_id}/dismiss")
    assert dismiss_response.status_code == 200

    response = test_client.get("/needs-review")

    assert response.json()["low_confidence_transactions"] == []


def test_empty_queue_when_nothing_needs_review(client):
    test_client, session_factory = client
    session = session_factory()
    ensure_default_user(session)
    session.close()

    response = test_client.get("/needs-review")

    assert response.status_code == 200
    body = response.json()
    assert body == {"unmatched_emails": [], "low_confidence_transactions": []}


class TestIgnoreNeedsReviewEmail:
    def test_ignoring_an_unmatched_email_removes_it_from_the_queue(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        conn = GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}")
        session.add(conn)
        session.commit()
        email = EmailMessage(
            gmail_connection_id=conn.id,
            message_id="msg-unmatched",
            thread_id="thread-unmatched",
            received_at=datetime.now(timezone.utc),
            status=EmailMessageStatus.NEEDS_REVIEW,
            content="Some unrecognized HDFC email",
        )
        session.add(email)
        session.commit()
        email_id = email.id
        session.close()

        response = test_client.post(f"/needs-review/emails/{email_id}/ignore")

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
        assert test_client.get("/needs-review").json()["unmatched_emails"] == []

    def test_returns_404_for_unknown_email(self, client):
        test_client, _ = client
        response = test_client.post("/needs-review/emails/999/ignore")
        assert response.status_code == 404

    def test_returns_409_for_an_email_thats_not_needs_review(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        conn = GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}")
        session.add(conn)
        session.commit()
        email = EmailMessage(
            gmail_connection_id=conn.id,
            message_id="msg-matched",
            thread_id="thread-matched",
            received_at=datetime.now(timezone.utc),
            status=EmailMessageStatus.MATCHED,
            content="Dear Customer, ...",
        )
        session.add(email)
        session.commit()
        email_id = email.id
        session.close()

        response = test_client.post(f"/needs-review/emails/{email_id}/ignore")

        assert response.status_code == 409
