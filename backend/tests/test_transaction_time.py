"""Unit tests for app/domain/transaction_time.py (sort-by-time follow-up to Epic G)."""

from datetime import date, datetime, time

from app.domain.transaction_time import effective_sort_datetime


def test_uses_txn_time_directly_when_present():
    result = effective_sort_datetime(
        date(2026, 7, 18), time(18, 56, 45), datetime(2026, 7, 18, 1, 0, 0)
    )
    assert result == datetime(2026, 7, 18, 18, 56, 45)


def test_falls_back_to_email_received_time_shifted_to_ist_when_txn_time_is_none():
    # 13:20 UTC -> 18:50 IST (UTC+5:30).
    result = effective_sort_datetime(date(2026, 7, 18), None, datetime(2026, 7, 18, 13, 20, 0))
    assert result == datetime(2026, 7, 18, 18, 50, 0)


def test_always_anchored_on_txn_date_even_if_the_ist_shift_crosses_midnight():
    # 19:00 UTC -> 00:30 IST the *next* calendar day, but txn_date must still win for the date.
    result = effective_sort_datetime(date(2026, 7, 18), None, datetime(2026, 7, 18, 19, 0, 0))
    assert result == datetime(2026, 7, 18, 0, 30, 0)
