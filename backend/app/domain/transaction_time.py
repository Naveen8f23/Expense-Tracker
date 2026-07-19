"""Effective sort/display time for a transaction (follow-up to Epic G, requested 2026-07-19).

Not every source template captures a real transaction time -- the UPI templates are date-only
(REQUIREMENTS.md Appendix A). The dashboard shows the source email's received time instead for
those rows, clearly marked as an approximation (`frontend/src/utils/transactionTime.tsx`). Sorting
must use the same effective time the dashboard displays, or the list would look unsorted even
though each individual row's own time is technically correct.
"""

from datetime import date, datetime, time, timedelta
from typing import Optional

# Every extracted `txn_time` value is copied verbatim from the bank's own email text with no
# timezone conversion -- i.e. it's already implicitly India Standard Time, since HDFC (the only
# configured bank, REQUIREMENTS.md Assumption 10) operates there. `email_received_at` is stored as
# a naive UTC instant, so it's shifted by this fixed offset (India has no DST) to be comparable.
_IST_OFFSET = timedelta(hours=5, minutes=30)


def effective_sort_datetime(
    txn_date: date, txn_time: Optional[time], email_received_at: datetime
) -> datetime:
    """The date/time a transaction should be sorted (and is displayed) by.

    Always anchored on `txn_date` (the authoritative transaction date, never the email's own
    date) -- only the *time* component is ever borrowed from `email_received_at`, and only when
    `txn_time` itself is unavailable.
    """
    if txn_time is not None:
        return datetime.combine(txn_date, txn_time)
    ist_received = email_received_at + _IST_OFFSET
    return datetime.combine(txn_date, ist_received.time())
