"""BACKLOG.md E6: category CRUD endpoints."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.bootstrap import ensure_default_user
from app.infrastructure.db import Base, get_db, make_engine, make_session_factory
from app.infrastructure.models import (
    Category,
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


class TestListAndCreate:
    def test_no_categories_seeded_by_default(self, client):
        test_client, session_factory = client
        session = session_factory()
        ensure_default_user(session)
        session.close()

        response = test_client.get("/categories")
        assert response.json() == {"items": []}

    def test_create_then_list(self, client):
        test_client, session_factory = client
        session = session_factory()
        ensure_default_user(session)
        session.close()

        create_response = test_client.post("/categories", json={"name": "Food"})
        assert create_response.status_code == 201
        assert create_response.json()["name"] == "Food"

        list_response = test_client.get("/categories")
        assert [c["name"] for c in list_response.json()["items"]] == ["Food"]

    def test_duplicate_name_for_the_same_user_is_rejected(self, client):
        test_client, _ = client
        test_client.post("/categories", json={"name": "Food"})

        response = test_client.post("/categories", json={"name": "Food"})

        assert response.status_code == 409


class TestRename:
    def test_renames_an_existing_category(self, client):
        test_client, _ = client
        category_id = test_client.post("/categories", json={"name": "Food"}).json()["id"]

        response = test_client.patch(f"/categories/{category_id}", json={"name": "Dining"})

        assert response.status_code == 200
        assert response.json()["name"] == "Dining"

    def test_returns_404_for_unknown_category(self, client):
        test_client, _ = client
        response = test_client.patch("/categories/999", json={"name": "Whatever"})
        assert response.status_code == 404


class TestDelete:
    def test_deletes_an_unused_category(self, client):
        test_client, _ = client
        category_id = test_client.post("/categories", json={"name": "Food"}).json()["id"]

        response = test_client.delete(f"/categories/{category_id}")

        assert response.status_code == 204
        assert test_client.get("/categories").json() == {"items": []}

    def test_deleting_a_category_in_use_without_reassignment_is_rejected(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        category = Category(user_id=user.id, name="Food")
        session.add(category)
        session.commit()
        category_id = category.id

        conn = GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}")
        session.add(conn)
        session.commit()
        email = EmailMessage(
            gmail_connection_id=conn.id,
            message_id="msg-1",
            thread_id="thread-1",
            received_at=datetime.now(timezone.utc),
            status=EmailMessageStatus.MATCHED,
            content="...",
        )
        session.add(email)
        session.flush()
        payee = Payee(name="GOLKONDAS CAFE", identifier="vyapar@hdfcbank")
        session.add(payee)
        session.flush()
        txn = Transaction(
            user_id=user.id,
            amount=Decimal("120.00"),
            currency="INR",
            txn_date=date(2026, 7, 18),
            payee_id=payee.id,
            instrument_last4="4958",
            category_id=category_id,
            payment_method=PaymentMethod.UPI,
            txn_type=DebitOrCredit.DEBIT,
            confidence_score=1.0,
            review_status=ReviewStatus.AUTO_ACCEPTED,
            email_message_id=email.id,
        )
        session.add(txn)
        session.commit()
        session.close()

        response = test_client.delete(f"/categories/{category_id}")

        assert response.status_code == 409
        assert response.json()["detail"]["transaction_count"] == 1

    def test_deleting_a_category_in_use_with_reassignment_moves_transactions(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        old_category = Category(user_id=user.id, name="Food")
        new_category = Category(user_id=user.id, name="Dining")
        session.add_all([old_category, new_category])
        session.commit()
        old_id, new_id = old_category.id, new_category.id

        conn = GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}")
        session.add(conn)
        session.commit()
        email = EmailMessage(
            gmail_connection_id=conn.id,
            message_id="msg-1",
            thread_id="thread-1",
            received_at=datetime.now(timezone.utc),
            status=EmailMessageStatus.MATCHED,
            content="...",
        )
        session.add(email)
        session.flush()
        payee = Payee(name="GOLKONDAS CAFE", identifier="vyapar@hdfcbank", default_category_id=old_id)
        session.add(payee)
        session.flush()
        txn = Transaction(
            user_id=user.id,
            amount=Decimal("120.00"),
            currency="INR",
            txn_date=date(2026, 7, 18),
            payee_id=payee.id,
            instrument_last4="4958",
            category_id=old_id,
            payment_method=PaymentMethod.UPI,
            txn_type=DebitOrCredit.DEBIT,
            confidence_score=1.0,
            review_status=ReviewStatus.AUTO_ACCEPTED,
            email_message_id=email.id,
        )
        session.add(txn)
        session.commit()
        txn_id, payee_id = txn.id, payee.id
        session.close()

        response = test_client.delete(f"/categories/{old_id}", params={"reassign_to": new_id})

        assert response.status_code == 204

        session = session_factory()
        assert session.get(Transaction, txn_id).category_id == new_id
        assert session.get(Payee, payee_id).default_category_id == new_id
        assert session.get(Category, old_id) is None
        session.close()
