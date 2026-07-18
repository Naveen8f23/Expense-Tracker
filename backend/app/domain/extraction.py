"""Extraction (BACKLOG.md C4-C6; REQUIREMENTS.md EXT-1..EXT-6).

Fixed, per-type parsers that turn a *classified* email's content into structured transaction
fields (EXT-3: deterministic-first). Pure text parsing -- no database, no Gmail API -- so each
extractor can be tested directly against the real sample fixtures (REQUIREMENTS.md Appendix A).

An extractor never guesses past its template: if an expected field can't be found, it raises
ExtractionError rather than returning a partial/fabricated result, so the caller (BACKLOG.md C7)
routes the email to the needs-review queue instead of silently storing wrong data (EXT-5, EXT-6).
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from app.infrastructure.models import DebitOrCredit, PaymentMethod


class ExtractionError(Exception):
    """Raised when a classified email doesn't match its own template's fixed structure closely
    enough to extract a required field (format drift, unexpected content)."""


@dataclass(frozen=True)
class ExtractedTransaction:
    amount: Decimal
    currency: str
    txn_date: date
    txn_time: Optional[time]  # nullable: UPI templates give a date only, no time (Appendix A)
    payee_identifier: str  # VPA, or the card's merchant descriptor
    payee_name: Optional[str]  # display name, when the template provides one
    instrument_last4: str  # EXT-1: last 4 digits only, not the full "account ending ..." phrase
    payment_method: PaymentMethod
    txn_type: DebitOrCredit
    reference_number: Optional[str]  # nullable: the credit card debit template lacks one (DUP-2)
    confidence_score: float = 1.0  # EXT-5: high confidence -- a known template, cleanly parsed


# Any run of whitespace and/or HTML tags between two anchor words -- confirmed necessary against
# real HDFC email HTML (not just the plain-text Appendix A quotes): the credit card debit
# template wraps its values in "<b>...</b>" (e.g. "Credit Card ending <b>2174</b>"), which a
# plain "\s*"/"\s+" gap does not tolerate. The UPI templates use "<br>" only between whole
# sentences/fields, never around a single value, so this only ever widens what already matched.
_GAP = r"(?:\s|<[^>]*>)*"

_AMOUNT_RE = re.compile(r"Rs\." + _GAP + r"([\d,]+\.\d{2})")  # "Rs.120.00" and "Rs. 554.00" alike


def _parse_amount(content: str) -> Decimal:
    match = _AMOUNT_RE.search(content)
    if match is None:
        raise ExtractionError("Could not find a 'Rs.<amount>' figure in the email content")
    return Decimal(match.group(1).replace(",", ""))


def extract_upi_debit(content: str) -> ExtractedTransaction:
    """Appendix A.1. Handles the parenthetical payee display name being absent (Edge Cases SS10)
    by falling back to the VPA alone."""
    amount = _parse_amount(content)
    instrument_match = re.search(r"account ending" + _GAP + r"(\d{4})", content)
    vpa_match = re.search(
        r"towards VPA" + _GAP + r"([\w.\-]+@[\w.\-]+)(?:" + _GAP + r"\(([^)]+)\))?" + _GAP + r"on",
        content,
    )
    date_match = re.search(r"\bon" + _GAP + r"(\d{2}-\d{2}-\d{2})" + _GAP + r"\.", content)
    ref_match = re.search(r"reference no\.?:?" + _GAP + r"(\d+)", content, re.IGNORECASE)

    if instrument_match is None or vpa_match is None or date_match is None:
        raise ExtractionError("UPI debit email is missing an expected field")

    return ExtractedTransaction(
        amount=amount,
        currency="INR",
        txn_date=datetime.strptime(date_match.group(1), "%d-%m-%y").date(),
        txn_time=None,
        payee_identifier=vpa_match.group(1),
        payee_name=vpa_match.group(2),  # None if the parenthetical name is absent
        instrument_last4=instrument_match.group(1),
        payment_method=PaymentMethod.UPI,
        txn_type=DebitOrCredit.DEBIT,
        reference_number=ref_match.group(1) if ref_match else None,
    )


def extract_upi_credit(content: str) -> ExtractedTransaction:
    """Appendix A.2 -- same UPI shape as A.1, but a lettered "Transaction Details" layout
    ("account ending in", not "account ending") and a sender name + VPA instead of a payee VPA."""
    amount = _parse_amount(content)
    instrument_match = re.search(r"account ending in" + _GAP + r"(\d{4})", content)
    sender_match = re.search(
        r"Sender:" + _GAP + r"([^(]+?)" + _GAP + r"\(VPA:" + _GAP + r"([\w.\-]+@[\w.\-]+)\)",
        content,
    )
    date_match = re.search(r"Date:" + _GAP + r"(\d{2}-\d{2}-\d{2})", content)
    ref_match = re.search(r"Reference No\.?:?" + _GAP + r"(\d+)", content, re.IGNORECASE)

    if instrument_match is None or sender_match is None or date_match is None:
        raise ExtractionError("UPI credit email is missing an expected field")

    return ExtractedTransaction(
        amount=amount,
        currency="INR",
        txn_date=datetime.strptime(date_match.group(1), "%d-%m-%y").date(),
        txn_time=None,
        payee_identifier=sender_match.group(2),
        payee_name=sender_match.group(1).strip(),
        instrument_last4=instrument_match.group(1),
        payment_method=PaymentMethod.UPI,
        txn_type=DebitOrCredit.CREDIT,
        reference_number=ref_match.group(1) if ref_match else None,
    )


def extract_credit_card_debit(content: str) -> ExtractedTransaction:
    """Appendix A.3. Distinct date/time format (with seconds) from the UPI templates, a cryptic
    merchant descriptor instead of a friendly payee name, and confirmed no reference number at
    all in this template -- dedup falls back to the full timestamp instead (DUP-2)."""
    amount = _parse_amount(content)
    instrument_match = re.search(r"Credit Card ending" + _GAP + r"(\d{4})", content)
    payee_match = re.search(r"towards" + _GAP + r"([A-Za-z0-9]+)" + _GAP + r"on", content)
    datetime_match = re.search(
        r"\bon" + _GAP + r"(\d{1,2} \w{3}, \d{4} at \d{2}:\d{2}:\d{2})", content
    )

    if instrument_match is None or payee_match is None or datetime_match is None:
        raise ExtractionError("Credit card debit email is missing an expected field")

    parsed_dt = datetime.strptime(datetime_match.group(1), "%d %b, %Y at %H:%M:%S")

    return ExtractedTransaction(
        amount=amount,
        currency="INR",
        txn_date=parsed_dt.date(),
        txn_time=parsed_dt.time(),
        payee_identifier=payee_match.group(1),
        payee_name=None,  # cryptic descriptor only, e.g. "ASSPL" -- Edge Cases SS10
        instrument_last4=instrument_match.group(1),
        payment_method=PaymentMethod.CREDIT_CARD,
        txn_type=DebitOrCredit.DEBIT,
        reference_number=None,  # confirmed absent in this template
    )
