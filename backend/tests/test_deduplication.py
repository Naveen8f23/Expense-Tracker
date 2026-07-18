"""BACKLOG.md Epic D (Deduplication): DUP-1 (message-ID based duplicate detection) and DUP-2
(reference-number/timestamp disambiguation of genuinely repeated transactions).

Both are already structurally guaranteed by existing constraints rather than a separate runtime
"Deduplicator" component -- see ARCHITECTURE.md SS3 for the full reasoning. These tests confirm
that guarantee holds end-to-end through the real pipeline, per Constitution principle 18 (test
important business logic -- money handling), rather than trusting the architecture on faith.
"""

from datetime import datetime, timezone

import pytest

from app.application.ingest_gmail_messages import store_new_messages
from app.application.run_classify_and_extract import run_classify_and_extract
from app.infrastructure import gmail_client
from app.infrastructure.bootstrap import ensure_default_user, ensure_hdfc_sender_rules
from app.infrastructure.db import Base, make_engine, make_session_factory
from app.infrastructure.models import EmailMessage, GmailConnection, Transaction


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


def _upi_debit_content(*, amount="120.00", reference, date="18-07-26"):
    return (
        f"Rs.{amount} is debited from your account ending 4958 towards VPA "
        f"vyapar.171813527289@hdfcbank (GOLKONDAS CAFE) on {date}.\n\n"
        f"UPI transaction reference no.: {reference}."
    )


def _credit_card_debit_content(*, amount="554.00", time="18:56:45", date="18 Jul, 2026"):
    return (
        f"We would like to inform you that Rs. {amount} has been debited from your HDFC Bank "
        f"Credit Card ending 2174 towards ASSPL on {date} at {time}."
    )


def _fake_gmail_message(message_id):
    return {"id": message_id, "threadId": f"thread-{message_id}", "internalDate": "1721318400000"}


def _ingest(session, connection, monkeypatch, message_id, content):
    """Simulates a real sync run storing one message (B3/B4's shared step)."""
    monkeypatch.setattr(gmail_client, "get_message", lambda credentials, mid: _fake_gmail_message(mid))
    monkeypatch.setattr(gmail_client, "extract_message_content", lambda message: content)
    return store_new_messages(session, connection, credentials=None, message_ids=[message_id])


class TestDup1MessageIdDeduplication:
    def test_re_ingesting_the_same_message_id_creates_no_second_transaction(
        self, session, user, connection, monkeypatch
    ):
        content = _upi_debit_content(reference="126479299557")

        # First sync run: message is stored and then classified/extracted.
        _ingest(session, connection, monkeypatch, "msg-1", content)
        created, flagged = run_classify_and_extract(session, user)
        assert (created, flagged) == (1, 0)
        assert session.query(Transaction).count() == 1

        # A retried/duplicate sync run fetches the same Gmail message ID again.
        stored, skipped, filtered_out, failed = _ingest(
            session, connection, monkeypatch, "msg-1", content
        )
        assert (stored, skipped) == (0, 1)  # ING-6/DUP-1: recognized as an existing message ID
        assert session.query(EmailMessage).count() == 1  # no second EmailMessage row

        # Even if classify/extract were re-run, the email is already MATCHED, not UNPROCESSED.
        created_again, flagged_again = run_classify_and_extract(session, user)
        assert (created_again, flagged_again) == (0, 0)
        assert session.query(Transaction).count() == 1  # still exactly one transaction


class TestDup2ReferenceNumberAndTimestampDisambiguation:
    def test_two_upi_transactions_same_amount_payee_day_different_reference_are_both_recorded(
        self, session, user, connection, monkeypatch
    ):
        # Same amount, same payee, same day -- but two genuinely separate real payments.
        _ingest(
            session, connection, monkeypatch, "msg-a",
            _upi_debit_content(reference="126479299557"),
        )
        _ingest(
            session, connection, monkeypatch, "msg-b",
            _upi_debit_content(reference="999999999999"),
        )

        created, flagged = run_classify_and_extract(session, user)

        assert (created, flagged) == (2, 0)
        transactions = session.query(Transaction).all()
        assert len(transactions) == 2  # not merged into one
        assert {t.reference_number for t in transactions} == {"126479299557", "999999999999"}
        assert len({t.payee_id for t in transactions}) == 1  # correctly the same payee, reused

    def test_credit_card_debit_same_amount_payee_day_different_time_are_both_recorded(
        self, session, user, connection, monkeypatch
    ):
        # This template has no reference number at all (confirmed gap, Appendix A.3) -- dedup
        # must fall back to the full timestamp instead.
        _ingest(
            session, connection, monkeypatch, "msg-c",
            _credit_card_debit_content(time="18:56:45"),
        )
        _ingest(
            session, connection, monkeypatch, "msg-d",
            _credit_card_debit_content(time="18:57:12"),
        )

        created, flagged = run_classify_and_extract(session, user)

        assert (created, flagged) == (2, 0)
        transactions = session.query(Transaction).all()
        assert len(transactions) == 2
        assert {t.txn_time.isoformat() for t in transactions} == {"18:56:45", "18:57:12"}
        assert all(t.reference_number is None for t in transactions)

    def test_credit_card_debit_same_amount_payee_day_and_time_are_still_both_recorded(
        self, session, user, connection, monkeypatch
    ):
        # An exact coincidental duplicate (same amount/payee/day/time-to-the-second) is
        # vanishingly unlikely for two genuinely different real charges, but this architecture
        # never attempts content-based merging at all (ADR-0009) -- two distinct Gmail messages
        # always produce two distinct Transactions, keyed by message ID (DUP-1), not by content.
        content = _credit_card_debit_content(time="18:56:45")
        _ingest(session, connection, monkeypatch, "msg-e", content)
        _ingest(session, connection, monkeypatch, "msg-f", content)

        created, flagged = run_classify_and_extract(session, user)

        assert (created, flagged) == (2, 0)
        assert session.query(Transaction).count() == 2
