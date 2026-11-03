"""Safety checks: the suite must never use (nor modify) the real businesses.db.

The "real file stays intact" check runs around the WHOLE session in the real_db_untouched
fixture (conftest.py), because only after the last test can we know nothing touched it.
"""
from pathlib import Path

import database
from models.user_models import User_db
from tests.conftest import REAL_DB_PATH


def test_app_engine_is_not_the_real_database():
    # The engine created at import time (main.py's create_all) is in memory, not businesses.db
    assert database.engine.url.database in (None, "", ":memory:")
    assert "businesses.db" not in str(database.engine.url)


def test_test_database_is_a_temporary_file_outside_the_project(db_engine):
    test_db = Path(db_engine.url.database).resolve()

    assert test_db != REAL_DB_PATH.resolve()
    assert REAL_DB_PATH.parent.resolve() not in test_db.parents


def test_api_writes_go_to_the_test_database(client, db_session, user_a):
    # A user registered through the API must appear in THIS test's own database
    assert db_session.query(User_db).filter(User_db.email == user_a.email).count() == 1


def test_each_test_starts_with_an_empty_database(db_session):
    # Even though other tests registered users, this test's database is brand new
    assert db_session.query(User_db).count() == 0


def test_real_db_fingerprint_was_recorded(real_db_untouched):
    # The session guard captured the starting state (None only if the file did not exist)
    assert real_db_untouched is None or len(real_db_untouched) == 3
