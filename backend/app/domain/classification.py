"""Classification (BACKLOG.md C1-C3; REQUIREMENTS.md ING-3a; ADR-0010).

Given an email already known to come from a configured SenderRule sender address, decides which
(if any) of that sender's known content patterns the email body matches. Pure text matching --
no database, no Gmail API, no HTTP -- so it can run against any candidate string, cached content
or otherwise (ARCHITECTURE.md Layers table: Domain must not depend on infrastructure specifics).

Matching is done directly against the raw (possibly HTML) content via substring search, per the
confirmed edge case in REQUIREMENTS.md Edge Cases SS10: HDFC's alert emails are HTML, but the
transactional sentences are plain text within it, not broken up by inline markup or images.
"""

from typing import Callable, Optional

# REQUIREMENTS.md Appendix A -- each marker is the distinguishing phrase(s) ADR-0010 identified
# for that template. All three currently share one sender address (alerts@hdfcbank.bank.in) so
# these markers, not the sender, are what tells them apart.


def is_upi_debit(content: str) -> bool:
    """Appendix A.1: "...is debited from your account ending... towards VPA..."."""
    return "is debited from your account ending" in content and "towards VPA" in content


def is_upi_credit(content: str) -> bool:
    """Appendix A.2: "...has been successfully credited to your HDFC Bank account..."."""
    return "has been successfully credited to your HDFC Bank account" in content


def is_credit_card_debit(content: str) -> bool:
    """Appendix A.3: "...has been debited from your HDFC Bank Credit Card ending..."."""
    return "has been debited from your HDFC Bank Credit Card ending" in content


# content_pattern_id -> matcher, keyed to match SenderRule.content_pattern_id values seeded by
# app.infrastructure.bootstrap.HDFC_SENDER_RULES (BACKLOG.md B2). Adding a fourth pattern later
# (credit card credit, REQUIREMENTS.md SS8) is one more entry here, not a restructuring.
CONTENT_PATTERN_MATCHERS: dict[str, Callable[[str], bool]] = {
    "hdfc_upi_debit": is_upi_debit,
    "hdfc_upi_credit": is_upi_credit,
    "hdfc_credit_card_debit": is_credit_card_debit,
}


def classify(content: str, candidate_pattern_ids: list[str]) -> Optional[str]:
    """Return the one content_pattern_id whose marker matches `content`, or None if zero or more
    than one candidate matches.

    Candidates are restricted to what the caller already knows is possible for this email's
    sender (its configured SenderRule content_pattern_ids) rather than trying every known pattern
    unconditionally -- classification is sender-then-content, not content alone (ADR-0010).

    More than one match would mean the confirmed markers are no longer mutually exclusive (e.g.
    after a bank template change) -- returned as "no match" so the caller routes to needs-review
    (EXT-6) instead of guessing which one is right.
    """
    matches = [
        pattern_id
        for pattern_id in candidate_pattern_ids
        if pattern_id in CONTENT_PATTERN_MATCHERS and CONTENT_PATTERN_MATCHERS[pattern_id](content)
    ]
    if len(matches) == 1:
        return matches[0]
    return None
