"""BACKLOG.md E1-E4: transactions API routes."""

from datetime import date, datetime, time, timezone
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


def _make_transaction(
    session,
    user,
    *,
    amount="120.00",
    payee_name="GOLKONDAS CAFE",
    payee_identifier="vyapar@hdfcbank",
    category_id=None,
    txn_date_=date(2026, 7, 18),
    txn_time_=None,
    received_at=None,
    txn_type=DebitOrCredit.DEBIT,
    payment_method=PaymentMethod.UPI,
    review_status=ReviewStatus.AUTO_ACCEPTED,
    dismissed=False,
    message_id=None,
):
    conn = session.query(GmailConnection).first()
    if conn is None:
        conn = GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}")
        session.add(conn)
        session.commit()

    message_id = message_id or f"msg-{payee_identifier}-{amount}"
    email = EmailMessage(
        gmail_connection_id=conn.id,
        message_id=message_id,
        thread_id=f"thread-{message_id}",
        received_at=received_at or datetime.now(timezone.utc),
        status=EmailMessageStatus.MATCHED,
        content="Dear Customer, ...",
    )
    session.add(email)
    session.flush()

    payee = session.query(Payee).filter_by(identifier=payee_identifier).one_or_none()
    if payee is None:
        payee = Payee(name=payee_name, identifier=payee_identifier)
        session.add(payee)
        session.flush()

    txn = Transaction(
        user_id=user.id,
        amount=Decimal(amount),
        currency="INR",
        txn_date=txn_date_,
        txn_time=txn_time_,
        payee_id=payee.id,
        instrument_last4="4958",
        category_id=category_id,
        payment_method=payment_method,
        txn_type=txn_type,
        reference_number="126479299557",
        confidence_score=1.0,
        review_status=review_status,
        email_message_id=email.id,
        dismissed=dismissed,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


class TestListTransactions:
    def test_lists_transactions_excluding_dismissed(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        _make_transaction(session, user, amount="120.00")
        _make_transaction(session, user, amount="50.00", dismissed=True)
        session.close()

        response = test_client.get("/transactions")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["amount"] == "120.00"

    def test_filters_by_payee_substring(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        _make_transaction(session, user, payee_name="GOLKONDAS CAFE", payee_identifier="a@x")
        _make_transaction(session, user, payee_name="ASSPL", payee_identifier="b@x")
        session.close()

        response = test_client.get("/transactions", params={"payee": "golkondas"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["payee"]["name"] == "GOLKONDAS CAFE"

    def test_filters_by_amount_range_and_type(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        _make_transaction(session, user, amount="10.00", txn_type=DebitOrCredit.CREDIT, payee_identifier="c1")
        _make_transaction(session, user, amount="500.00", txn_type=DebitOrCredit.DEBIT, payee_identifier="c2")
        session.close()

        response = test_client.get(
            "/transactions", params={"amount_min": "1", "amount_max": "100", "txn_type": "credit"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["amount"] == "10.00"

    def test_pagination(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        for i in range(5):
            _make_transaction(session, user, amount=f"{i + 1}.00", payee_identifier=f"payee-{i}")
        session.close()

        response = test_client.get("/transactions", params={"limit": 2, "offset": 0})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2


class TestGetRecentTransactions:
    def test_returns_only_transactions_created_after_since_id(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        first = _make_transaction(session, user, amount="10.00", payee_identifier="a@x")
        second = _make_transaction(session, user, amount="20.00", payee_identifier="b@x")
        first_id, second_id = first.id, second.id
        session.close()

        response = test_client.get("/transactions/recent", params={"since_id": first_id})

        assert response.status_code == 200
        body = response.json()
        assert [item["id"] for item in body["items"]] == [second_id]

    def test_since_id_zero_returns_everything(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        _make_transaction(session, user)
        session.close()

        response = test_client.get("/transactions/recent")

        assert len(response.json()["items"]) == 1

    def test_excludes_dismissed_transactions(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        _make_transaction(session, user, dismissed=True)
        session.close()

        response = test_client.get("/transactions/recent")

        assert response.json()["items"] == []

    def test_the_literal_path_recent_is_not_swallowed_by_the_transaction_id_route(self, client):
        # Regression guard: "/transactions/recent" must resolve to this endpoint, not be parsed
        # as GET /transactions/{transaction_id} with transaction_id="recent" (which would 422).
        test_client, _ = client
        response = test_client.get("/transactions/recent")
        assert response.status_code == 200


class TestGetTransaction:
    def test_returns_transaction_with_source_email(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        txn = _make_transaction(session, user)
        txn_id = txn.id
        session.close()

        response = test_client.get(f"/transactions/{txn_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == txn_id
        assert body["source_email"]["content"] == "Dear Customer, ..."

    def test_returns_404_for_unknown_id(self, client):
        test_client, _ = client
        response = test_client.get("/transactions/999")
        assert response.status_code == 404


class TestCorrectTransaction:
    def test_patch_updates_fields_and_logs_correction(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        category = Category(user_id=user.id, name="Food")
        session.add(category)
        session.commit()
        txn = _make_transaction(session, user, amount="120.00")
        txn_id, category_id, payee_id = txn.id, category.id, txn.payee_id
        session.close()

        response = test_client.patch(
            f"/transactions/{txn_id}", json={"amount": "150.00", "category_id": category_id}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["amount"] == "150.00"
        assert body["category_id"] == category_id
        assert body["review_status"] == "user_confirmed"

        session = session_factory()
        from app.infrastructure.models import CorrectionLog

        logs = session.query(CorrectionLog).filter_by(transaction_id=txn_id).all()
        fields_logged = {log.field_name for log in logs}
        assert "amount" in fields_logged
        assert "category_id" in fields_logged

        # COR-2: the payee's default category is now remembered.
        payee = session.get(Payee, payee_id)
        assert payee.default_category_id == category_id
        session.close()

    def test_returns_404_for_unknown_id(self, client):
        test_client, _ = client
        response = test_client.patch("/transactions/999", json={"amount": "1.00"})
        assert response.status_code == 404


class TestDismissTransaction:
    def test_dismiss_excludes_from_list_but_keeps_the_row(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        txn = _make_transaction(session, user)
        txn_id = txn.id
        session.close()

        response = test_client.post(f"/transactions/{txn_id}/dismiss")

        assert response.status_code == 200
        assert response.json()["dismissed"] is True

        list_response = test_client.get("/transactions")
        assert list_response.json()["total"] == 0

        session = session_factory()
        assert session.get(Transaction, txn_id) is not None  # row still exists
        session.close()

    def test_returns_404_for_unknown_id(self, client):
        test_client, _ = client
        response = test_client.post("/transactions/999/dismiss")
        assert response.status_code == 404


class TestSortByEffectiveTime:
    def test_same_day_transactions_are_ordered_by_effective_time_not_creation_order(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)

        # Inserted in a deliberately scrambled order so passing proves real time-based sorting,
        # not an accidental match with insertion/id order (the bug being fixed here).
        mid_id = _make_transaction(
            session, user, amount="2.00", payee_identifier="mid",
            txn_date_=date(2026, 7, 18), txn_time_=time(12, 0, 0),
        ).id
        late_id = _make_transaction(
            session, user, amount="3.00", payee_identifier="late",
            txn_date_=date(2026, 7, 18),
            received_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),  # 15:30 IST
        ).id
        early_id = _make_transaction(
            session, user, amount="1.00", payee_identifier="early",
            txn_date_=date(2026, 7, 18),
            received_at=datetime(2026, 7, 18, 3, 0, 0, tzinfo=timezone.utc),  # 08:30 IST
        ).id
        session.close()

        response = test_client.get(
            "/transactions", params={"date_from": "2026-07-18", "date_to": "2026-07-18"}
        )

        assert response.status_code == 200
        ids_in_order = [item["id"] for item in response.json()["items"]]
        assert ids_in_order == [late_id, mid_id, early_id]


class TestAddManualTransaction:
    def test_creates_a_transaction_with_no_source_email(self, client):
        test_client, _ = client

        response = test_client.post(
            "/transactions",
            json={
                "amount": "45.00",
                "txn_date": "2026-07-19",
                "payee_name": "Corner Store",
                "payment_method": "upi",
                "txn_type": "debit",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["amount"] == "45.00"
        assert body["email_message_id"] is None
        assert body["email_received_at"] is None
        assert body["review_status"] == "user_confirmed"

        get_response = test_client.get(f"/transactions/{body['id']}")
        assert get_response.json()["source_email"] is None

    def test_reuses_an_existing_payee_by_case_insensitive_name(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        existing = _make_transaction(session, user, payee_name="GOLKONDAS CAFE", payee_identifier="a@x")
        existing_payee_id = existing.payee_id
        session.close()

        response = test_client.post(
            "/transactions",
            json={
                "amount": "10.00",
                "txn_date": "2026-07-19",
                "payee_name": "golkondas cafe",
                "payment_method": "upi",
                "txn_type": "debit",
            },
        )

        assert response.status_code == 201
        assert response.json()["payee"]["id"] == existing_payee_id

    def test_assigning_a_category_remembers_it_as_the_payees_default(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        category = Category(user_id=user.id, name="Groceries")
        session.add(category)
        session.commit()
        category_id = category.id
        session.close()

        first = test_client.post(
            "/transactions",
            json={
                "amount": "20.00",
                "txn_date": "2026-07-19",
                "payee_name": "Corner Store 2",
                "payment_method": "upi",
                "txn_type": "debit",
                "category_id": category_id,
            },
        )
        assert first.json()["category_id"] == category_id

        # A second manual entry for the same payee, with no category given, should inherit it
        # (COR-2, same behavior as an auto-ingested transaction from an already-categorized payee).
        second = test_client.post(
            "/transactions",
            json={
                "amount": "30.00",
                "txn_date": "2026-07-19",
                "payee_name": "Corner Store 2",
                "payment_method": "upi",
                "txn_type": "debit",
            },
        )
        assert second.json()["category_id"] == category_id
