from datetime import datetime, timedelta, timezone

from utils.datetime_utils import to_utc, utc_now

UTC_MINUS_3 = timezone(timedelta(hours=-3))


def test_utc_now_is_aware_and_in_utc():
    now = utc_now()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)
    assert abs(now - datetime.now(timezone.utc)) < timedelta(seconds=1)


def test_to_utc_marks_a_naive_datetime_as_utc_without_moving_it():
    # Naive values come from SQLite and were written in UTC: same clock time, now labelled UTC
    naive = datetime(2026, 1, 15, 12, 0)

    assert to_utc(naive) == datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)


def test_to_utc_converts_an_aware_datetime_in_utc_minus_3():
    # 09:00 in Argentina is 12:00 in UTC: the clock time CHANGES, the instant does not
    buenos_aires = datetime(2026, 1, 15, 9, 0, tzinfo=UTC_MINUS_3)

    result = to_utc(buenos_aires)

    assert result == datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    assert (result.hour, result.utcoffset()) == (12, timedelta(0))


def test_to_utc_keeps_an_aware_utc_datetime_unchanged():
    value = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

    assert to_utc(value) == value
    assert to_utc(value).utcoffset() == timedelta(0)


def test_to_utc_makes_naive_and_aware_comparable():
    # Comparing naive with aware raises TypeError in Python; after to_utc on both sides it works
    naive = datetime(2026, 1, 15, 12, 0)
    aware = datetime(2026, 1, 15, 9, 30, tzinfo=UTC_MINUS_3)  # 12:30 UTC

    assert to_utc(naive) < to_utc(aware)
