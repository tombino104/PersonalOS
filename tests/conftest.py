from datetime import datetime, timezone

import pytest

from app import db
from app.logical_day import DayRules


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    db.migrate(connection)
    connection.execute("INSERT INTO users (name, password_hash) VALUES ('tester', 'x')")
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def rules():
    return DayRules()


@pytest.fixture
def user_id(conn):
    return conn.execute("SELECT id FROM users WHERE name = 'tester'").fetchone()["id"]


@pytest.fixture
def add_activity(conn):
    def _add(area_slug: str, name: str, weight: int) -> int:
        area_id = conn.execute("SELECT id FROM areas WHERE slug = ?", (area_slug,)).fetchone()["id"]
        cursor = conn.execute(
            "INSERT INTO activities (area_id, name, weight) VALUES (?, ?, ?)",
            (area_id, name, weight),
        )
        conn.commit()
        return cursor.lastrowid

    return _add


def utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
