"""UTCDateTime (models/custom_types.py): always stores UTC, always returns aware UTC.

Tested on its own little table (not the project models), in this test's own SQLite file, and
looking at the RAW stored text to see what really reaches the database."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, insert, select, text

from models.custom_types import UTCDateTime

UTC_MINUS_3 = timezone(timedelta(hours=-3))


@pytest.fixture
def events(db_engine):
    metadata = MetaData()  # separate from the app's Base: this table exists only in this test
    table = Table("events", metadata, Column("id", Integer, primary_key=True), Column("at", UTCDateTime))
    metadata.create_all(db_engine)
    return table


def save(db_engine, table, value) -> int:
    with db_engine.begin() as connection:
        return connection.execute(insert(table).values(at=value)).inserted_primary_key[0]


def read(db_engine, table, row_id: int):
    with db_engine.connect() as connection:
        return connection.execute(select(table.c.at).where(table.c.id == row_id)).scalar_one()


def raw_text(db_engine, row_id: int) -> str | None:
    with db_engine.connect() as connection:
        return connection.execute(text("SELECT at FROM events WHERE id = :id"), {"id": row_id}).scalar_one()


def test_aware_utc_minus_3_is_stored_as_utc(db_engine, events):
    row_id = save(db_engine, events, datetime(2026, 1, 15, 9, 0, tzinfo=UTC_MINUS_3))

    # 09:00 in UTC-3 reaches the DB as 12:00 (a plain DateTime would store "09:00", 3 hours off)
    assert raw_text(db_engine, row_id).startswith("2026-01-15 12:00:00")


def test_value_is_read_back_as_aware_utc(db_engine, events):
    row_id = save(db_engine, events, datetime(2026, 1, 15, 9, 0, tzinfo=UTC_MINUS_3))

    value = read(db_engine, events, row_id)

    assert value == datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    assert value.tzinfo is not None and value.utcoffset() == timedelta(0)


def test_naive_value_is_interpreted_as_utc(db_engine, events):
    row_id = save(db_engine, events, datetime(2026, 1, 15, 12, 0))

    assert raw_text(db_engine, row_id).startswith("2026-01-15 12:00:00")  # not shifted
    assert read(db_engine, events, row_id) == datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)


def test_naive_text_written_by_hand_is_read_as_aware_utc(db_engine, events):
    # e.g. a row written by an old version or a manual script, without going through the type
    with db_engine.begin() as connection:
        connection.execute(text("INSERT INTO events (id, at) VALUES (1, '2026-01-15 12:00:00.000000')"))

    assert read(db_engine, events, 1) == datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)


def test_null_is_accepted_both_ways(db_engine, events):
    row_id = save(db_engine, events, None)

    assert raw_text(db_engine, row_id) is None
    assert read(db_engine, events, row_id) is None
