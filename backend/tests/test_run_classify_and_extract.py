"""BACKLOG.md C7: needs-review queue mechanics + the classify/extract orchestration."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.application.run_classify_and_extract import (
    get_needs_review_emails,
    run_classify_and_extract,
)
from app.domain.extraction import ExtractedTransaction
from app.infrastructure.bootstrap import ensure_default_user, ensure_hdfc_sender_rules
from app.infrastructure.db import Base, make_engine, make_session_factory
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

UPI_DEBIT_SAMPLE = """Dear Customer,

Greetings from HDFC Bank!

Rs.120.00 is debited from your account ending 4958 towards VPA vyapar.171813527289@hdfcbank (GOLKONDAS CAFE) on 18-07-26.

UPI transaction reference no.: 126479299557."""

UNRELATED_SAMPLE = """Dear Customer,

Your monthly HDFC Bank account statement is now available to view online."""

# Matches the UPI debit content pattern's markers but is missing the amount/date/reference --
# classifies fine, then fails extraction.
CLASSIFIES_BUT_UNPARSEABLE = (
    "Some amount is debited from your account ending towards VPA on some date."
)


@pytest.fixture()
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY_PATH", str(tmp_path / "secret.key"))
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    Session = make_session_factory(engine)
    yield Session()


@pytest.fixture()
def user(session):
    return ensure_default_user(session)


@pytest.fixture()
def connection(session, user):
    conn = GmailConnection(user_id=user.id, email_address="naveen8f23@gmail.com", tokens="{}")
    session.add(conn)
    session.commit()
    return conn


@pytest.fixture(autouse=True)
def sender_rules(session):
    ensure_hdfc_sender_rules(session)


def _make_email(session, connection, message_id, content, status=EmailMessageStatus.UNPROCESSED):
    email = EmailMessage(
        gmail_connection_id=connection.id,
        message_id=message_id,
        thread_id=f"thread-{message_id}",
        received_at=datetime.now(timezone.utc),
        status=status,
        content=content,
    )
    session.add(email)
    session.commit()
    return email


class TestUnrecognizedEmail:
    def test_is_marked_needs_review_not_ignored_or_deleted(self, session, user, connection):
        email = _make_email(session, connection, "msg-unrelated", UNRELATED_SAMPLE)

        created, flagged = run_classify_and_extract(session, user)

        session.refresh(email)
        assert created == 0
        assert flagged == 1
        assert email.status == EmailMessageStatus.NEEDS_REVIEW
        assert email.classified_pattern_id is None
        assert session.query(Transaction).count() == 0


class TestClassifiesButFailsExtraction:
    def test_is_marked_needs_review_with_classification_preserved(self, session, user, connection):
        email = _make_email(session, connection, "msg-broken", CLASSIFIES_BUT_UNPARSEABLE)

        created, flagged = run_classify_and_extract(session, user)

        session.refresh(email)
        assert created == 0
        assert flagged == 1
        assert email.status == EmailMessageStatus.NEEDS_REVIEW
        assert email.classified_pattern_id == "hdfc_upi_debit"
        assert session.query(Transaction).count() == 0


class TestSuccessfulExtraction:
    def test_creates_an_auto_accepted_transaction_and_marks_the_email_matched(
        self, session, user, connection
    ):
        email = _make_email(session, connection, "msg-good", UPI_DEBIT_SAMPLE)

        created, flagged = run_classify_and_extract(session, user)

        session.refresh(email)
        assert created == 1
        assert flagged == 0
        assert email.status == EmailMessageStatus.MATCHED
        assert email.classified_pattern_id == "hdfc_upi_debit"

        transaction = session.query(Transaction).one()
        assert transaction.amount == Decimal("120.00")
        assert transaction.txn_type == DebitOrCredit.DEBIT
        assert transaction.payment_method == PaymentMethod.UPI
        assert transaction.instrument_last4 == "4958"
        assert transaction.reference_number == "126479299557"
        assert transaction.review_status == ReviewStatus.AUTO_ACCEPTED
        assert transaction.category_id is None
        assert transaction.email_message_id == email.id

        payee = session.query(Payee).one()
        assert payee.identifier == "vyapar.171813527289@hdfcbank"
        assert payee.name == "GOLKONDAS CAFE"

    def test_reuses_the_existing_payee_for_the_same_identifier(self, session, user, connection):
        _make_email(session, connection, "msg-1", UPI_DEBIT_SAMPLE)
        second_sample = UPI_DEBIT_SAMPLE.replace("126479299557", "999999999999")
        _make_email(session, connection, "msg-2", second_sample)

        run_classify_and_extract(session, user)

        assert session.query(Payee).count() == 1
        assert session.query(Transaction).count() == 2

    def test_a_new_transaction_defaults_to_the_payees_remembered_category(
        self, session, user, connection
    ):
        # COR-2 (BACKLOG.md E3): once a user has assigned a category to this payee (e.g. via a
        # prior correction), a brand-new transaction from the same payee should default to it
        # rather than starting uncategorized again.
        from app.infrastructure.models import Category

        category = Category(user_id=user.id, name="Food")
        session.add(category)
        session.commit()
        payee = Payee(
            name="GOLKONDAS CAFE",
            identifier="vyapar.171813527289@hdfcbank",
            default_category_id=category.id,
        )
        session.add(payee)
        session.commit()

        _make_email(session, connection, "msg-good", UPI_DEBIT_SAMPLE)
        run_classify_and_extract(session, user)

        transaction = session.query(Transaction).one()
        assert transaction.category_id == category.id
        assert session.query(Payee).count() == 1  # reused, not duplicated


class TestAiFallback:
    def test_a_successful_fallback_extraction_still_creates_a_needs_review_transaction(
        self, session, user, connection
    ):
        email = _make_email(session, connection, "msg-broken", CLASSIFIES_BUT_UNPARSEABLE)

        class FakeFallback:
            def extract(self, content):
                return ExtractedTransaction(
                    amount=Decimal("42.00"),
                    currency="INR",
                    txn_date=email.received_at.date(),
                    txn_time=None,
                    payee_identifier="unknown@upi",
                    payee_name=None,
                    instrument_last4="0000",
                    payment_method=PaymentMethod.UPI,
                    txn_type=DebitOrCredit.DEBIT,
                    reference_number=None,
                    confidence_score=0.4,
                )

        created, flagged = run_classify_and_extract(session, user, ai_fallback=FakeFallback())

        session.refresh(email)
        assert created == 1
        assert flagged == 0
        assert email.status == EmailMessageStatus.MATCHED

        transaction = session.query(Transaction).one()
        assert transaction.review_status == ReviewStatus.NEEDS_REVIEW
        assert transaction.confidence_score == 0.4


class TestIdempotency:
    def test_running_twice_does_not_reprocess_already_handled_emails(self, session, user, connection):
        _make_email(session, connection, "msg-good", UPI_DEBIT_SAMPLE)
        _make_email(session, connection, "msg-bad", UNRELATED_SAMPLE)

        first = run_classify_and_extract(session, user)
        second = run_classify_and_extract(session, user)

        assert first == (1, 1)
        assert second == (0, 0)
        assert session.query(Transaction).count() == 1


class TestGetNeedsReviewEmails:
    def test_returns_only_needs_review_emails(self, session, user, connection):
        _make_email(session, connection, "msg-good", UPI_DEBIT_SAMPLE)
        _make_email(session, connection, "msg-bad", UNRELATED_SAMPLE)

        run_classify_and_extract(session, user)

        needs_review = get_needs_review_emails(session)
        assert [e.message_id for e in needs_review] == ["msg-bad"]
