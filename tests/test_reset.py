from datetime import timedelta

from app import db
from app.api.deps import COOKIE_NAME
from tests.conftest import EVENING, PASSWORD, USER
from tests.test_setup import PASSPHRASE, SETUP, STATUS, payload, read_code

RESET = "/api/v1/auth/reset"


def query(tmp_path, sql, params=()):
    conn = db.connect(tmp_path / "personal_os.db")
    try:
        return [dict(row) for row in conn.execute(sql, params)]
    finally:
        conn.close()


def fill(client):
    assert client.post("/api/v1/reports", json={"day": "2026-10-20"}).status_code in (200, 201)
    first = client.get("/api/v1/activities").json()["activities"][0]
    done = client.put(f"/api/v1/reports/2026-10-20/completions/{first['id']}", json={"done": True})
    assert done.status_code == 200
    created = client.post("/api/v1/activities", json={"area": "mindset", "name": "A personal habit", "weight": 2})
    assert created.status_code == 201
    assert client.put("/api/v1/profile", json={"display_name": "Sam"}).status_code == 200


def test_a_wrong_code_does_not_touch_anything(client, tmp_path):
    fill(client)
    response = client.post(RESET, json={"code": "WRONG-CODE"})
    assert (response.status_code, response.json()["error"]["code"]) == (401, "invalid_setup_code")
    assert query(tmp_path, "SELECT COUNT(*) AS n FROM reports")[0]["n"] == 1
    assert query(tmp_path, "SELECT name FROM users") == [{"name": USER}]


def test_the_code_wipes_everything_and_the_app_starts_again_from_the_beginning(client, tmp_path):
    fill(client)
    code = read_code(tmp_path)
    response = client.post(RESET, json={"code": code})
    assert response.status_code == 200
    assert response.json() == {"setup_required": True}
    assert client.get(STATUS).json() == {"setup_required": True, "setup_code_required": True}
    assert client.get("/api/v1/auth/me").status_code == 401
    assert query(tmp_path, "SELECT COUNT(*) AS n FROM users")[0]["n"] == 0
    assert query(tmp_path, "SELECT COUNT(*) AS n FROM reports")[0]["n"] == 0
    assert query(tmp_path, "SELECT COUNT(*) AS n FROM profile")[0]["n"] == 0
    names = {row["name"] for row in query(tmp_path, "SELECT name FROM activities")}
    assert "A personal habit" not in names
    assert names


def test_the_user_then_creates_a_new_account_with_the_same_code(client, tmp_path):
    code = read_code(tmp_path)
    client.post(RESET, json={"code": code})
    created = client.post(SETUP, json=payload(code, name="Fresh"))
    assert created.status_code == 200
    assert COOKIE_NAME in created.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").json() == {"name": "Fresh"}
    assert read_code(tmp_path) != code
    client.post("/api/v1/auth/logout")
    assert client.post("/api/v1/auth/login", json={"name": USER, "password": PASSWORD}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"name": "Fresh", "password": PASSPHRASE}).status_code == 200


def test_plugin_data_is_wiped_and_the_calendar_comes_back_on(client, tmp_path):
    created = client.post("/api/v1/plugins/calendar/events", json={"title": "Dentist", "day": "2026-10-22"})
    assert created.status_code == 201
    code = read_code(tmp_path)
    client.post(RESET, json={"code": code})
    client.post(SETUP, json=payload(code))
    plugins = {item["id"]: item for item in client.get("/api/v1/plugins").json()["plugins"]}
    assert plugins["calendar"]["state"] == "active"
    events = client.get(
        "/api/v1/plugins/calendar/events", params={"start": "2026-10-01", "end": "2026-10-31"}
    ).json()
    assert events["occurrences"] == []


def test_too_many_wrong_codes_lock_the_reset(client, tmp_path, clock):
    code = read_code(tmp_path)
    for _ in range(4):
        assert client.post(RESET, json={"code": "WRONG-CODE"}).status_code == 401
    assert client.post(RESET, json={"code": "WRONG-CODE"}).status_code == 429
    assert client.post(RESET, json={"code": code}).status_code == 429
    clock.now = EVENING + timedelta(minutes=15)
    assert client.post(RESET, json={"code": code}).status_code == 200


def test_a_foreign_origin_cannot_reset(client, tmp_path):
    response = client.post(RESET, json={"code": read_code(tmp_path)}, headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert client.get(STATUS).json() == {"setup_required": False, "setup_code_required": True}


def test_the_reset_is_recorded_in_the_audit_log(client, tmp_path):
    client.post(RESET, json={"code": read_code(tmp_path)})
    actions = [row["action"] for row in query(tmp_path, "SELECT action FROM audit_log")]
    assert "data.reset" in actions


def test_it_works_without_any_account_too(anon_client, tmp_path):
    assert anon_client.post(RESET, json={"code": read_code(tmp_path)}).status_code == 200
    assert anon_client.get(STATUS).json()["setup_required"] is True


def test_the_reset_always_needs_the_code_even_when_setup_does_not(client, monkeypatch):
    monkeypatch.setenv("SETUP_CODE_REQUIRED", "0")
    assert client.post(RESET, json={"code": "WRONG-CODE"}).status_code == 401
