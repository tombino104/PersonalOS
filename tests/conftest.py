from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import auth, db
from app.api.deps import get_now
from app.logical_day import DayRules
from app.main import app

USER = "tester"
PASSWORD = "correct horse battery"
EVENING = datetime(2026, 10, 20, 20, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self):
        self.now = EVENING


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def anon_client(tmp_path, monkeypatch, clock):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    app.dependency_overrides[get_now] = lambda: clock.now
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client, tmp_path):
    conn = db.connect(tmp_path / "personal_os.db")
    auth.create_user(conn, USER, PASSWORD)
    conn.close()
    response = anon_client.post("/api/v1/auth/login", json={"name": USER, "password": PASSWORD})
    assert response.status_code == 200
    return anon_client


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
