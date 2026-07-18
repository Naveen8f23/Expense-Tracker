"""BACKLOG.md C4-C6: extractor tests against the real HDFC samples (REQUIREMENTS.md Appendix A)
plus the confirmed edge cases (missing payee name, missing reference number, Rs. spacing,
differing date/time formats)."""

from decimal import Decimal

import pytest

from app.domain.extraction import (
    ExtractionError,
    extract_credit_card_debit,
    extract_upi_credit,
    extract_upi_debit,
)
from app.infrastructure.models import DebitOrCredit, PaymentMethod

UPI_DEBIT_SAMPLE = """Dear Customer,

Greetings from HDFC Bank!

Rs.120.00 is debited from your account ending 4958 towards VPA vyapar.171813527289@hdfcbank (GOLKONDAS CAFE) on 18-07-26.

UPI transaction reference no.: 126479299557.

If you did not authorize this transaction, please report it immediately at: ..."""

UPI_DEBIT_SAMPLE_NO_DISPLAY_NAME = """Dear Customer,

Greetings from HDFC Bank!

Rs.120.00 is debited from your account ending 4958 towards VPA vyapar.171813527289@hdfcbank on 18-07-26.

UPI transaction reference no.: 126479299557."""

UPI_CREDIT_SAMPLE = """Dear Customer,

Greetings from HDFC Bank!

We're writing to inform you that Rs.10.00 has been successfully credited to your HDFC Bank account ending in 4958.

Transaction Details:
a. Date: 18-07-26
b. Sender: NAVEEN V (VPA: naveen8f23@oksbi)
c. UPI Reference No.: 619901283303

Need Help? ..."""

CREDIT_CARD_DEBIT_SAMPLE = """Dear Customer,

Greetings from HDFC Bank.

We would like to inform you that Rs. 554.00 has been debited from your HDFC Bank Credit Card ending 2174 towards ASSPL on 18 Jul, 2026 at 18:56:45.

To check your available balance ..."""


class TestExtractUpiDebit:
    def test_extracts_all_fields_from_the_real_sample(self):
        result = extract_upi_debit(UPI_DEBIT_SAMPLE)

        assert result.amount == Decimal("120.00")
        assert result.currency == "INR"
        assert result.txn_type == DebitOrCredit.DEBIT
        assert result.payment_method == PaymentMethod.UPI
        assert result.instrument_last4 == "4958"
        assert result.payee_identifier == "vyapar.171813527289@hdfcbank"
        assert result.payee_name == "GOLKONDAS CAFE"
        assert result.txn_date.isoformat() == "2026-07-18"
        assert result.txn_time is None
        assert result.reference_number == "126479299557"
        assert result.confidence_score == 1.0

    def test_falls_back_to_the_vpa_alone_when_the_display_name_is_absent(self):
        result = extract_upi_debit(UPI_DEBIT_SAMPLE_NO_DISPLAY_NAME)

        assert result.payee_identifier == "vyapar.171813527289@hdfcbank"
        assert result.payee_name is None

    def test_raises_extraction_error_when_a_required_field_is_missing(self):
        broken = "Rs.120.00 is debited from your account ending towards VPA on 18-07-26."
        with pytest.raises(ExtractionError):
            extract_upi_debit(broken)

    def test_extracts_correctly_when_real_html_wraps_values_in_tags(self):
        # Not yet observed in production for this template (the UPI templates only use <br>
        # between fields, per a real live email checked 2026-07-19), but the credit card debit
        # template *does* bold its values -- covering this here too guards against the same bug
        # class resurfacing if HDFC's UPI template formatting ever changes similarly.
        html = (
            "Rs.<b>77.00</b> is debited from your account ending <b>9999</b> towards VPA "
            "<b>fake.merchant@upi</b> (FAKE MERCHANT) on <b>05-01-27</b>.<br><br>"
            "UPI transaction reference no.: <b>111222333444</b>."
        )
        result = extract_upi_debit(html)

        assert result.amount == Decimal("77.00")
        assert result.instrument_last4 == "9999"
        assert result.payee_identifier == "fake.merchant@upi"
        assert result.payee_name == "FAKE MERCHANT"
        assert result.txn_date.isoformat() == "2027-01-05"
        assert result.reference_number == "111222333444"


class TestExtractUpiCredit:
    def test_extracts_all_fields_from_the_real_sample(self):
        result = extract_upi_credit(UPI_CREDIT_SAMPLE)

        assert result.amount == Decimal("10.00")
        assert result.currency == "INR"
        assert result.txn_type == DebitOrCredit.CREDIT
        assert result.payment_method == PaymentMethod.UPI
        assert result.instrument_last4 == "4958"
        assert result.payee_identifier == "naveen8f23@oksbi"
        assert result.payee_name == "NAVEEN V"
        assert result.txn_date.isoformat() == "2026-07-18"
        assert result.txn_time is None
        assert result.reference_number == "619901283303"

    def test_raises_extraction_error_when_a_required_field_is_missing(self):
        broken = "Rs.10.00 has been successfully credited to your HDFC Bank account."
        with pytest.raises(ExtractionError):
            extract_upi_credit(broken)


CREDIT_CARD_DEBIT_SAMPLE_HTML_BOLDED = """<!doctype html>
<html><body><p>Dear Customer,</p>
<p>We would like to inform you that <b>Rs. 999.00</b> has been debited from your HDFC Bank
Credit Card ending <b>1234</b> towards <b>FAKEMERCHANT</b> on <b>05 Jan, 2027 at 09:15:30</b>.</p>
<p>To check your available balance ...</p></body></html>"""


class TestExtractCreditCardDebit:
    def test_extracts_all_fields_from_the_real_sample(self):
        result = extract_credit_card_debit(CREDIT_CARD_DEBIT_SAMPLE)

        assert result.amount == Decimal("554.00")  # confirms the "Rs. " (with space) case
        assert result.currency == "INR"
        assert result.txn_type == DebitOrCredit.DEBIT
        assert result.payment_method == PaymentMethod.CREDIT_CARD
        assert result.instrument_last4 == "2174"
        assert result.payee_identifier == "ASSPL"
        assert result.payee_name is None
        assert result.txn_date.isoformat() == "2026-07-18"
        assert result.txn_time.isoformat() == "18:56:45"
        assert result.reference_number is None  # confirmed absent in this template (DUP-2)

    def test_no_space_after_rs_prefix_also_parses(self):
        # A.1/A.2 have no space after "Rs."; A.3 does. Parsing must not assume fixed spacing.
        variant = CREDIT_CARD_DEBIT_SAMPLE.replace("Rs. 554.00", "Rs.554.00")
        result = extract_credit_card_debit(variant)
        assert result.amount == Decimal("554.00")

    def test_raises_extraction_error_when_a_required_field_is_missing(self):
        broken = "Rs. 554.00 has been debited from your HDFC Bank Credit Card towards ASSPL."
        with pytest.raises(ExtractionError):
            extract_credit_card_debit(broken)

    def test_extracts_correctly_when_real_html_bolds_the_values(self):
        # Discovered against a real live HDFC email (2026-07-19): unlike the plain-text quotes
        # in REQUIREMENTS.md Appendix A, the actual HTML wraps the merchant/amount/card-ending/
        # date-time values in "<b>...</b>" tags. A plain "\s*"/"\s+" gap between anchor words and
        # the value doesn't tolerate that -- this fixture (fabricated values, not a real
        # transaction) reproduces the bug class without embedding real account data in the repo.
        result = extract_credit_card_debit(CREDIT_CARD_DEBIT_SAMPLE_HTML_BOLDED)

        assert result.amount == Decimal("999.00")
        assert result.instrument_last4 == "1234"
        assert result.payee_identifier == "FAKEMERCHANT"
        assert result.txn_date.isoformat() == "2027-01-05"
        assert result.txn_time.isoformat() == "09:15:30"
        assert result.reference_number is None
