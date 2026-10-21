from datetime import timedelta

from app import db
from app.api.deps import COOKIE_NAME
from tests.conftest import EVENING, PASSWORD, USER
from tests.test_setup import PASSPHRASE, STATUS, payload, read_code

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


def test_a_wrong_code_does_not_touch_anything(client, tmp_path):
    fill(client)
    response = client.post(RESET, json=payload("WRONG-CODE"))
    assert (response.status_code, response.json()["error"]["code"]) == (401, "invalid_setup_code")
    assert query(tmp_path, "SELECT COUNT(*) AS n FROM reports")[0]["n"] == 1
    assert query(tmp_path, "SELECT name FROM users") == [{"name": USER}]


def test_the_code_wipes_everything_and_creates_a_fresh_account(client, tmp_path):
    fill(client)
    old_code = read_code(tmp_path)
    response = client.post(RESET, json=payload(old_code, name="Fresh", password=PASSPHRASE))
    assert response.status_code == 200
    assert response.json() == {"name": "Fresh"}
    assert COOKIE_NAME in response.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").json() == {"name": "Fresh"}
    assert query(tmp_path, "SELECT name FROM users") == [{"name": "Fresh"}]
    assert query(tmp_path, "SELECT COUNT(*) AS n FROM reports")[0]["n"] == 0
    names = {row["name"] for row in query(tmp_path, "SELECT name FROM activities")}
    assert "A personal habit" not in names
    assert names
    assert read_code(tmp_path) != old_code


def test_the_old_password_stops_working_and_old_sessions_are_gone(client, tmp_path):
    other = client
    assert client.post(RESET, json=payload(read_code(tmp_path), name="Fresh")).status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.post("/api/v1/auth/login", json={"name": USER, "password": PASSWORD}).status_code == 401
    assert other.post("/api/v1/auth/login", json={"name": "Fresh", "password": PASSPHRASE}).status_code == 200


def test_plugin_data_is_wiped_and_the_calendar_comes_back_on(client, tmp_path):
    assert client.get("/api/v1/plugins").status_code == 200
    created = client.post(
        "/api/v1/plugins/calendar/events", json={"title": "Dentist", "day": "2026-10-22"}
    )
    assert created.status_code == 201
    assert client.post(RESET, json=payload(read_code(tmp_path))).status_code == 200
    plugins = {item["id"]: item for item in client.get("/api/v1/plugins").json()["plugins"]}
    assert plugins["calendar"]["state"] == "active"
    events = client.get(
        "/api/v1/plugins/calendar/events", params={"start": "2026-10-01", "end": "2026-10-31"}
    ).json()
    assert events["occurrences"] == []


def test_a_weak_password_keeps_the_data(client, tmp_path):
    fill(client)
    response = client.post(RESET, json=payload(read_code(tmp_path), password="short"))
    assert (response.status_code, response.json()["error"]["code"]) == (422, "weak_password")
    assert query(tmp_path, "SELECT COUNT(*) AS n FROM reports")[0]["n"] == 1


def test_too_many_wrong_codes_lock_the_reset(client, tmp_path, clock):
    code = read_code(tmp_path)
    for _ in range(4):
        assert client.post(RESET, json=payload("WRONG-CODE")).status_code == 401
    assert client.post(RESET, json=payload("WRONG-CODE")).status_code == 429
    assert client.post(RESET, json=payload(code)).status_code == 429
    clock.now = EVENING + timedelta(minutes=15)
    assert client.post(RESET, json=payload(code)).status_code == 200


def test_a_foreign_origin_cannot_reset(client, tmp_path):
    response = client.post(
        RESET, json=payload(read_code(tmp_path)), headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403
    assert client.get(STATUS).json() == {"setup_required": False, "setup_code_required": True}


def test_the_reset_is_recorded_in_the_audit_log(client, tmp_path):
    client.post(RESET, json=payload(read_code(tmp_path)))
    actions = [row["action"] for row in query(tmp_path, "SELECT action FROM audit_log")]
    assert "data.reset" in actions


def test_it_works_without_any_account_too(anon_client, tmp_path):
    assert anon_client.post(RESET, json=payload(read_code(tmp_path))).status_code == 200
    assert anon_client.get(STATUS).json() == {"setup_required": False, "setup_code_required": True}
