"""BACKLOG.md C1-C3: classifier tests against the real HDFC samples (REQUIREMENTS.md Appendix A).

Fixture content below is quoted verbatim from Appendix A -- these are the confirmed real-sample
fixtures the Definition of Done (BACKLOG.md) requires testing against, not synthetic stand-ins.
"""

from app.domain import classification

UPI_DEBIT_SAMPLE = """Dear Customer,

Greetings from HDFC Bank!

Rs.120.00 is debited from your account ending 4958 towards VPA vyapar.171813527289@hdfcbank (GOLKONDAS CAFE) on 18-07-26.

UPI transaction reference no.: 126479299557.

If you did not authorize this transaction, please report it immediately at: ..."""

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

UNRELATED_SAMPLE = """Dear Customer,

Your monthly HDFC Bank account statement is now available to view online. This is a routine
notification and does not relate to any specific transaction."""

ALL_HDFC_PATTERN_IDS = ["hdfc_upi_debit", "hdfc_upi_credit", "hdfc_credit_card_debit"]


class TestIsUpiDebit:
    def test_matches_the_real_upi_debit_sample(self):
        assert classification.is_upi_debit(UPI_DEBIT_SAMPLE) is True

    def test_does_not_match_upi_credit(self):
        assert classification.is_upi_debit(UPI_CREDIT_SAMPLE) is False

    def test_does_not_match_credit_card_debit(self):
        assert classification.is_upi_debit(CREDIT_CARD_DEBIT_SAMPLE) is False

    def test_does_not_match_an_unrelated_email_from_the_same_sender(self):
        assert classification.is_upi_debit(UNRELATED_SAMPLE) is False


class TestIsUpiCredit:
    def test_matches_the_real_upi_credit_sample(self):
        assert classification.is_upi_credit(UPI_CREDIT_SAMPLE) is True

    def test_does_not_match_upi_debit(self):
        assert classification.is_upi_credit(UPI_DEBIT_SAMPLE) is False

    def test_does_not_match_credit_card_debit(self):
        assert classification.is_upi_credit(CREDIT_CARD_DEBIT_SAMPLE) is False

    def test_does_not_match_an_unrelated_email_from_the_same_sender(self):
        assert classification.is_upi_credit(UNRELATED_SAMPLE) is False


class TestIsCreditCardDebit:
    def test_matches_the_real_credit_card_debit_sample(self):
        assert classification.is_credit_card_debit(CREDIT_CARD_DEBIT_SAMPLE) is True

    def test_does_not_match_upi_debit(self):
        assert classification.is_credit_card_debit(UPI_DEBIT_SAMPLE) is False

    def test_does_not_match_upi_credit(self):
        assert classification.is_credit_card_debit(UPI_CREDIT_SAMPLE) is False

    def test_does_not_match_an_unrelated_email_from_the_same_sender(self):
        assert classification.is_credit_card_debit(UNRELATED_SAMPLE) is False


class TestClassify:
    def test_classifies_upi_debit_sample_correctly(self):
        assert classification.classify(UPI_DEBIT_SAMPLE, ALL_HDFC_PATTERN_IDS) == "hdfc_upi_debit"

    def test_classifies_upi_credit_sample_correctly(self):
        assert (
            classification.classify(UPI_CREDIT_SAMPLE, ALL_HDFC_PATTERN_IDS) == "hdfc_upi_credit"
        )

    def test_classifies_credit_card_debit_sample_correctly(self):
        assert (
            classification.classify(CREDIT_CARD_DEBIT_SAMPLE, ALL_HDFC_PATTERN_IDS)
            == "hdfc_credit_card_debit"
        )

    def test_returns_none_for_an_unrecognized_email(self):
        assert classification.classify(UNRELATED_SAMPLE, ALL_HDFC_PATTERN_IDS) is None

    def test_content_pattern_matching_survives_surrounding_html_markup(self):
        # Edge Cases SS10: HDFC's real emails are HTML with the transactional sentence as plain
        # text within it -- classification must not depend on the content being plain text.
        html_wrapped = (
            "<html><body><p>Dear Customer,</p>"
            "<p>Rs.120.00 is debited from your account ending 4958 towards VPA "
            "vyapar.171813527289@hdfcbank (GOLKONDAS CAFE) on 18-07-26.</p>"
            "<p>UPI transaction reference no.: 126479299557.</p></body></html>"
        )
        assert classification.classify(html_wrapped, ALL_HDFC_PATTERN_IDS) == "hdfc_upi_debit"

    def test_only_considers_candidate_pattern_ids_passed_in(self):
        # A sender configured for only one pattern should never classify against the others.
        assert classification.classify(UPI_DEBIT_SAMPLE, ["hdfc_upi_credit"]) is None
