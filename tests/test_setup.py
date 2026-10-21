import re
from datetime import timedelta

from fastapi.testclient import TestClient

from app import auth, db
from app.api.deps import COOKIE_NAME
from app.main import app
from tests.conftest import EVENING, PASSWORD, USER

SETUP = "/api/v1/auth/setup"
STATUS = "/api/v1/auth/status"
PASSPHRASE = "a long enough passphrase"


def code_file(tmp_path):
    return tmp_path / "setup-code.txt"


def read_code(tmp_path):
    return code_file(tmp_path).read_text(encoding="utf-8").strip()


def payload(code, name="Alice", password=PASSPHRASE):
    return {"code": code, "name": name, "password": password}


def test_a_fresh_install_asks_for_setup_and_writes_a_code(anon_client, tmp_path):
    assert anon_client.get(STATUS).json() == {"setup_required": True, "setup_code_required": True}
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", read_code(tmp_path))


def test_status_is_public_and_changes_once_a_user_exists(client):
    assert client.get(STATUS).json() == {"setup_required": False, "setup_code_required": True}


def test_setup_creates_the_account_and_signs_in(anon_client, tmp_path):
    response = anon_client.post(SETUP, json=payload(read_code(tmp_path)))
    assert response.status_code == 200
    assert response.json() == {"name": "Alice"}
    assert COOKIE_NAME in response.headers["set-cookie"]
    assert anon_client.get("/api/v1/auth/me").json() == {"name": "Alice"}
    assert anon_client.get(STATUS).json() == {"setup_required": False, "setup_code_required": True}


def test_the_used_code_is_replaced_and_setup_cannot_run_twice(anon_client, tmp_path):
    code = read_code(tmp_path)
    anon_client.post(SETUP, json=payload(code))
    assert read_code(tmp_path) != code
    again = anon_client.post(SETUP, json=payload(code, name="Mallory"))
    assert (again.status_code, again.json()["error"]["code"]) == (409, "setup_done")


def test_the_code_is_accepted_in_any_case_and_without_the_dash(anon_client, tmp_path):
    code = read_code(tmp_path).replace("-", "").lower()
    assert anon_client.post(SETUP, json=payload(code)).status_code == 200


def test_a_wrong_code_is_refused(anon_client):
    response = anon_client.post(SETUP, json=payload("WRONG-CODE"))
    assert (response.status_code, response.json()["error"]["code"]) == (401, "invalid_setup_code")
    assert anon_client.get(STATUS).json() == {"setup_required": True, "setup_code_required": True}


def test_too_many_wrong_codes_lock_setup_for_fifteen_minutes(anon_client, tmp_path, clock):
    code = read_code(tmp_path)
    for _ in range(4):
        assert anon_client.post(SETUP, json=payload("WRONG-CODE")).status_code == 401
    fifth = anon_client.post(SETUP, json=payload("WRONG-CODE"))
    assert (fifth.status_code, fifth.headers["retry-after"]) == (429, "900")
    assert anon_client.post(SETUP, json=payload(code)).status_code == 429
    clock.now = EVENING + timedelta(minutes=15)
    assert anon_client.post(SETUP, json=payload(code)).status_code == 200


def test_a_weak_password_keeps_the_code_so_the_user_can_retry(anon_client, tmp_path):
    code = read_code(tmp_path)
    weak = anon_client.post(SETUP, json=payload(code, password="short"))
    assert (weak.status_code, weak.json()["error"]["code"]) == (422, "weak_password")
    assert code_file(tmp_path).exists()
    assert anon_client.post(SETUP, json=payload(code)).status_code == 200


def test_a_foreign_origin_cannot_run_setup(anon_client, tmp_path):
    response = anon_client.post(
        SETUP, json=payload(read_code(tmp_path)), headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403


def test_setup_works_after_the_placeholder_user_of_an_old_version(anon_client, tmp_path):
    conn = db.connect(tmp_path / "personal_os.db")
    conn.execute("INSERT INTO users (name, password_hash) VALUES ('owner', '!')")
    conn.commit()
    conn.close()
    assert anon_client.get(STATUS).json() == {"setup_required": True, "setup_code_required": True}
    assert anon_client.post(SETUP, json=payload(read_code(tmp_path))).status_code == 200
    conn = db.connect(tmp_path / "personal_os.db")
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    conn.close()


def test_a_new_code_is_written_at_every_start_until_an_account_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with TestClient(app):
        first = read_code(tmp_path)
    with TestClient(app):
        second = read_code(tmp_path)
    assert first != second


def test_a_code_is_written_at_start_even_when_an_account_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with TestClient(app):
        pass
    conn = db.connect(tmp_path / "personal_os.db")
    auth.create_user(conn, USER, PASSWORD)
    conn.close()
    before = read_code(tmp_path)
    with TestClient(app):
        assert read_code(tmp_path) != before


def test_the_code_can_be_switched_off_for_setup_only(anon_client, tmp_path, monkeypatch):
    monkeypatch.setenv("SETUP_CODE_REQUIRED", "0")
    assert anon_client.get(STATUS).json() == {"setup_required": True, "setup_code_required": False}
    response = anon_client.post(SETUP, json={"name": "Alice", "password": PASSPHRASE})
    assert response.status_code == 200
    assert anon_client.get("/api/v1/auth/me").json() == {"name": "Alice"}
    assert anon_client.post(SETUP, json={"name": "Mallory", "password": PASSPHRASE}).status_code == 409
    reset = anon_client.post("/api/v1/auth/reset", json={"code": "WRONG-CODE"})
    assert (reset.status_code, reset.json()["error"]["code"]) == (401, "invalid_setup_code")
    assert anon_client.post("/api/v1/auth/reset", json={"code": read_code(tmp_path)}).status_code == 200
