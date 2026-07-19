"""BACKLOG.md Epic G: analytics API routes (ANL-1..4)."""

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

    message_id = message_id or f"msg-{payee_identifier}-{amount}-{txn_date_}-{txn_type}"
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


class TestMonthlySummary:
    def test_totals_debit_and_credit_for_the_month(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        _make_transaction(
            session, user, amount="100.00", txn_type=DebitOrCredit.DEBIT,
            txn_date_=date(2026, 7, 5), payee_identifier="a@x",
        )
        _make_transaction(
            session, user, amount="30.00", txn_type=DebitOrCredit.CREDIT,
            txn_date_=date(2026, 7, 20), payee_identifier="b@x",
        )
        session.close()

        response = test_client.get("/analytics/monthly", params={"month": "2026-07"})

        assert response.status_code == 200
        body = response.json()
        assert body["month"] == "2026-07"
        assert body["total_debit"] == "100.00"
        assert body["total_credit"] == "30.00"
        assert body["net"] == "70.00"
        assert body["transaction_count"] == 2

    def test_excludes_transactions_outside_the_month_and_dismissed(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        _make_transaction(
            session, user, amount="100.00", txn_date_=date(2026, 7, 1), payee_identifier="a@x",
        )
        _make_transaction(
            session, user, amount="500.00", txn_date_=date(2026, 6, 30), payee_identifier="b@x",
        )
        _make_transaction(
            session, user, amount="500.00", txn_date_=date(2026, 8, 1), payee_identifier="c@x",
        )
        _make_transaction(
            session, user, amount="999.00", txn_date_=date(2026, 7, 15), payee_identifier="d@x",
            dismissed=True,
        )
        session.close()

        response = test_client.get("/analytics/monthly", params={"month": "2026-07"})

        body = response.json()
        assert body["total_debit"] == "100.00"
        assert body["transaction_count"] == 1

    def test_defaults_to_current_month_when_omitted(self, client):
        test_client, _ = client
        response = test_client.get("/analytics/monthly")
        assert response.status_code == 200
        assert "month" in response.json()

    def test_invalid_month_format_is_rejected(self, client):
        test_client, _ = client
        response = test_client.get("/analytics/monthly", params={"month": "not-a-month"})
        assert response.status_code == 422


class TestCategoryBreakdown:
    def test_groups_debits_by_category_and_excludes_credits(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        food = Category(user_id=user.id, name="Food")
        transport = Category(user_id=user.id, name="Transport")
        session.add_all([food, transport])
        session.commit()

        _make_transaction(
            session, user, amount="100.00", category_id=food.id,
            txn_date_=date(2026, 7, 5), payee_identifier="a@x",
        )
        _make_transaction(
            session, user, amount="50.00", category_id=food.id,
            txn_date_=date(2026, 7, 6), payee_identifier="b@x",
        )
        _make_transaction(
            session, user, amount="200.00", category_id=transport.id,
            txn_date_=date(2026, 7, 7), payee_identifier="c@x",
        )
        _make_transaction(
            session, user, amount="1000.00", category_id=food.id, txn_type=DebitOrCredit.CREDIT,
            txn_date_=date(2026, 7, 8), payee_identifier="d@x",
        )
        _make_transaction(
            session, user, amount="20.00", category_id=None,
            txn_date_=date(2026, 7, 9), payee_identifier="e@x",
        )
        session.close()

        response = test_client.get("/analytics/by-category", params={"month": "2026-07"})

        assert response.status_code == 200
        by_name = {c["category_name"]: c for c in response.json()["categories"]}
        assert by_name["Transport"]["total"] == "200.00"
        assert by_name["Food"]["total"] == "150.00"
        assert by_name["Food"]["transaction_count"] == 2
        assert by_name["Uncategorized"]["total"] == "20.00"
        assert by_name["Uncategorized"]["category_id"] is None
        # Ordered by total desc.
        names = [c["category_name"] for c in response.json()["categories"]]
        assert names.index("Transport") < names.index("Food")


class TestPayeeHistory:
    def test_matches_case_insensitively_and_returns_totals_and_items(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        _make_transaction(
            session, user, amount="100.00", payee_name="GOLKONDAS CAFE",
            payee_identifier="a@x", txn_date_=date(2026, 7, 1),
        )
        _make_transaction(
            session, user, amount="20.00", payee_name="GOLKONDAS CAFE",
            payee_identifier="a@x", txn_type=DebitOrCredit.CREDIT,
            txn_date_=date(2026, 6, 1), message_id="refund-1",
        )
        _make_transaction(
            session, user, amount="500.00", payee_name="ASSPL", payee_identifier="b@x",
        )
        session.close()

        response = test_client.get("/analytics/by-payee/golkondas cafe")

        assert response.status_code == 200
        body = response.json()
        assert body["payee_name"] == "golkondas cafe"
        assert body["total_debit"] == "100.00"
        assert body["total_credit"] == "20.00"
        assert body["net"] == "80.00"
        assert body["transaction_count"] == 2
        assert len(body["items"]) == 2

    def test_excludes_dismissed(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)
        _make_transaction(
            session, user, amount="100.00", payee_name="GOLKONDAS CAFE",
            payee_identifier="a@x", dismissed=True,
        )
        session.close()

        response = test_client.get("/analytics/by-payee/GOLKONDAS CAFE")

        assert response.status_code == 404

    def test_returns_404_for_unknown_payee(self, client):
        test_client, _ = client
        response = test_client.get("/analytics/by-payee/nobody")
        assert response.status_code == 404

    def test_items_are_ordered_by_effective_time_not_creation_order(self, client):
        test_client, session_factory = client
        session = session_factory()
        user = ensure_default_user(session)

        mid_id = _make_transaction(
            session, user, amount="2.00", payee_name="NAVEEN V", payee_identifier="mid",
            txn_date_=date(2026, 7, 18), txn_time_=time(12, 0, 0),
        ).id
        late_id = _make_transaction(
            session, user, amount="3.00", payee_name="NAVEEN V", payee_identifier="late",
            txn_date_=date(2026, 7, 18),
            received_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),  # 15:30 IST
        ).id
        early_id = _make_transaction(
            session, user, amount="1.00", payee_name="NAVEEN V", payee_identifier="early",
            txn_date_=date(2026, 7, 18),
            received_at=datetime(2026, 7, 18, 3, 0, 0, tzinfo=timezone.utc),  # 08:30 IST
        ).id
        session.close()

        response = test_client.get("/analytics/by-payee/NAVEEN V")

        assert response.status_code == 200
        ids_in_order = [item["id"] for item in response.json()["items"]]
        assert ids_in_order == [late_id, mid_id, early_id]
