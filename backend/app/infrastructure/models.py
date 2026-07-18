import enum
from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.crypto import EncryptedText
from app.infrastructure.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TransactionType(str, enum.Enum):
    UPI_DEBIT = "upi_debit"
    UPI_CREDIT = "upi_credit"
    CREDIT_CARD_DEBIT = "credit_card_debit"
    CREDIT_CARD_CREDIT = "credit_card_credit"


class PaymentMethod(str, enum.Enum):
    UPI = "upi"
    CREDIT_CARD = "credit_card"


class DebitOrCredit(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class EmailMessageStatus(str, enum.Enum):
    UNPROCESSED = "unprocessed"
    MATCHED = "matched"
    NEEDS_REVIEW = "needs_review"
    IGNORED = "ignored"


class ReviewStatus(str, enum.Enum):
    AUTO_ACCEPTED = "auto_accepted"
    NEEDS_REVIEW = "needs_review"
    USER_CONFIRMED = "user_confirmed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    gmail_connections: Mapped[list["GmailConnection"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    categories: Mapped[list["Category"]] = relationship(back_populates="user")


class GmailConnection(Base):
    __tablename__ = "gmail_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    email_address: Mapped[str]
    tokens: Mapped[str] = mapped_column(EncryptedText)  # ADR-0015: encrypted at rest
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="gmail_connections")
    sync_state: Mapped[Optional["SyncState"]] = relationship(back_populates="gmail_connection")


class SenderRule(Base):
    __tablename__ = "sender_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_address: Mapped[str]
    content_pattern_id: Mapped[str]  # identifies which fixed parser rule applies (Appendix A)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    gmail_connection_id: Mapped[int] = mapped_column(ForeignKey("gmail_connections.id"))
    message_id: Mapped[str] = mapped_column(unique=True)  # Gmail's message ID (ING-6, DUP-1)
    thread_id: Mapped[str]
    received_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[EmailMessageStatus] = mapped_column(Enum(EmailMessageStatus))
    content: Mapped[str] = mapped_column(EncryptedText)  # ADR-0012/ADR-0015: cached, encrypted
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # One email produces at most one transaction (ADR-0009: one email = one transaction).
    # The foreign key lives on Transaction (email_message_id); this is a query-time back
    # reference, not a second stored column, to avoid a circular FK between the two tables.
    transaction: Mapped[Optional["Transaction"]] = relationship(
        back_populates="email_message", uselist=False
    )


class SyncState(Base):
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    gmail_connection_id: Mapped[int] = mapped_column(
        ForeignKey("gmail_connections.id"), unique=True
    )
    last_history_id: Mapped[Optional[str]]
    last_sync_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # B5, ING-8
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime)  # completion time
    last_error: Mapped[Optional[str]]
    # B5 (ING-8): counts from the most recent sync run (backfill or incremental) -- "matched"
    # means newly stored (relevant sender, not a duplicate); "skipped" covers both known
    # duplicates and, for incremental syncs, History API results from unconfigured senders.
    last_scanned: Mapped[Optional[int]]
    last_matched: Mapped[Optional[int]]
    last_skipped: Mapped[Optional[int]]
    last_failed: Mapped[Optional[int]]

    gmail_connection: Mapped[GmailConnection] = relationship(back_populates="sync_state")


class Payee(Base):
    __tablename__ = "payees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    identifier: Mapped[Optional[str]]  # VPA or card-merchant descriptor, as seen in the email
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_category_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="categories")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(default="INR")
    txn_date: Mapped[date] = mapped_column(Date)
    txn_time: Mapped[Optional[time]] = mapped_column(Time)  # nullable: UPI templates lack time
    payee_id: Mapped[int] = mapped_column(ForeignKey("payees.id"))
    instrument_last4: Mapped[Optional[str]]
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod))
    txn_type: Mapped[DebitOrCredit] = mapped_column(Enum(DebitOrCredit))
    reference_number: Mapped[Optional[str]]  # nullable: credit card debit template lacks one
    confidence_score: Mapped[float] = mapped_column(default=1.0)
    review_status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus))
    email_message_id: Mapped[int] = mapped_column(ForeignKey("email_messages.id"), unique=True)
    dismissed: Mapped[bool] = mapped_column(default=False)  # COR-4: "not a real expense"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="transactions")
    payee: Mapped[Payee] = relationship()
    category: Mapped[Optional[Category]] = relationship()
    correction_log: Mapped[list["CorrectionLog"]] = relationship(back_populates="transaction")
    email_message: Mapped[EmailMessage] = relationship(back_populates="transaction")


class CorrectionLog(Base):
    __tablename__ = "correction_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    field_name: Mapped[str]
    old_value: Mapped[Optional[str]]
    new_value: Mapped[Optional[str]]
    corrected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    transaction: Mapped[Transaction] = relationship(back_populates="correction_log")
