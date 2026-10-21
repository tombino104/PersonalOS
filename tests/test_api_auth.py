from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import auth, db
from app.api.deps import COOKIE_NAME
from app.main import app
from tests.conftest import EVENING, PASSWORD, USER

LOGIN = "/api/v1/auth/login"

PROTECTED = [
    ("GET", "/api/v1/info"),
    ("GET", "/api/v1/areas"),
    ("GET", "/api/v1/activities"),
    ("POST", "/api/v1/activities"),
    ("PATCH", "/api/v1/activities/1"),
    ("GET", "/api/v1/reports"),
    ("POST", "/api/v1/reports"),
    ("GET", "/api/v1/reports/2026-10-20"),
    ("PUT", "/api/v1/reports/2026-10-20/completions/1"),
    ("PUT", "/api/v1/reports/2026-10-20/reflection"),
    ("POST", "/api/v1/reports/2026-10-20/sync"),
    ("POST", "/api/v1/reports/2026-10-20/complete"),
    ("GET", "/api/v1/scores"),
    ("GET", "/api/v1/today"),
    ("GET", "/api/v1/stats/areas"),
    ("GET", "/api/v1/stats/activities"),
    ("GET", "/api/v1/settings"),
    ("PATCH", "/api/v1/settings"),
    ("GET", "/api/v1/auth/me"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/password"),
    ("GET", "/api/v1/backups"),
    ("GET", "/api/v1/profile"),
    ("PUT", "/api/v1/profile"),
    ("PUT", "/api/v1/profile/photo"),
    ("DELETE", "/api/v1/profile/photo"),
    ("GET", "/api/v1/profile/photo"),
    ("POST", "/api/v1/backups"),
    ("GET", "/api/v1/backups/personal-os-manual-20261020-200000.zip"),
    ("POST", "/api/v1/backups/restore?confirm=restore"),
    ("POST", "/api/v1/backups/personal-os-manual-20261020-200000.zip/restore?confirm=restore"),
]


@pytest.fixture
def seeded(anon_client, tmp_path):
    conn = db.connect(tmp_path / "personal_os.db")
    auth.create_user(conn, USER, PASSWORD)
    conn.close()
    return anon_client


@pytest.mark.parametrize("method,path", PROTECTED)
def test_everything_but_login_and_health_needs_a_session(anon_client, method, path):
    response = anon_client.request(method, path, json={})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_health_stays_public(anon_client):
    assert anon_client.get("/health").status_code == 200


def test_docs_are_disabled_by_default(anon_client):
    for path in ("/docs", "/openapi.json", "/redoc"):
        body = anon_client.get(path).text.lower()
        assert "swagger" not in body
        assert '"openapi"' not in body


def test_login_sets_a_hardened_cookie(seeded):
    response = seeded.post(LOGIN, json={"name": USER, "password": PASSWORD})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert COOKIE_NAME in cookie
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert "secure" not in cookie
    assert "max-age=2592000" in cookie


def test_cookie_is_secure_behind_https_proxy(seeded):
    response = seeded.post(
        LOGIN,
        json={"name": USER, "password": PASSWORD},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert "secure" in response.headers["set-cookie"].lower()


def test_cookie_secure_can_be_forced_off(seeded, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "0")
    response = seeded.post(
        LOGIN,
        json={"name": USER, "password": PASSWORD},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert "secure" not in response.headers["set-cookie"].lower()


def test_wrong_credentials_give_the_same_401(seeded):
    wrong = seeded.post(LOGIN, json={"name": USER, "password": "wrong password!"})
    unknown = seeded.post(LOGIN, json={"name": "nobody", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["error"]["code"] == "invalid_credentials"
    assert COOKIE_NAME not in wrong.headers.get("set-cookie", "")


def test_lockout_returns_429_with_retry_after(seeded, clock):
    for _ in range(4):
        assert seeded.post(LOGIN, json={"name": USER, "password": "wrong password!"}).status_code == 401
    fifth = seeded.post(LOGIN, json={"name": USER, "password": "wrong password!"})
    assert fifth.status_code == 429
    assert fifth.headers["retry-after"] == "900"
    assert fifth.json()["error"]["code"] == "locked_out"
    assert seeded.post(LOGIN, json={"name": USER, "password": PASSWORD}).status_code == 429
    clock.now = EVENING + timedelta(minutes=15)
    assert seeded.post(LOGIN, json={"name": USER, "password": PASSWORD}).status_code == 200


def test_me_and_logout(client):
    assert client.get("/api/v1/auth/me").json() == {"name": USER}
    assert client.post("/api/v1/auth/logout").json() == {"ok": True}
    assert client.get("/api/v1/auth/me").status_code == 401


def test_session_stops_working_after_expiry(client, clock):
    assert client.get("/api/v1/areas").status_code == 200
    clock.now = EVENING + timedelta(days=31)
    assert client.get("/api/v1/areas").status_code == 401


def test_change_password_flow(client):
    with TestClient(app) as other:
        assert other.post(LOGIN, json={"name": USER, "password": PASSWORD}).status_code == 200

        wrong = client.post(
            "/api/v1/auth/password",
            json={"current_password": "not it at all", "new_password": "another long password"},
        )
        assert (wrong.status_code, wrong.json()["error"]["code"]) == (401, "invalid_credentials")

        weak = client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "short"},
        )
        assert (weak.status_code, weak.json()["error"]["code"]) == (422, "weak_password")

        ok = client.post(
            "/api/v1/auth/password",
            json={"current_password": PASSWORD, "new_password": "another long password"},
        )
        assert ok.status_code == 200
        assert client.get("/api/v1/areas").status_code == 200
        assert other.get("/api/v1/areas").status_code == 401
        assert client.post(LOGIN, json={"name": USER, "password": PASSWORD}).status_code == 401
        relog = client.post(LOGIN, json={"name": USER, "password": "another long password"})
        assert relog.status_code == 200


def test_foreign_origin_is_refused_on_writes_only(client):
    foreign = {"Origin": "https://evil.example"}
    blocked = client.post("/api/v1/reports", json={"day": "2026-10-20"}, headers=foreign)
    assert (blocked.status_code, blocked.json()["error"]["code"]) == (403, "bad_origin")
    assert client.get("/api/v1/areas", headers=foreign).status_code == 200
    login = client.post(LOGIN, json={"name": USER, "password": PASSWORD}, headers=foreign)
    assert login.status_code == 403


def test_same_origin_and_missing_origin_are_allowed(client):
    same = client.post(
        "/api/v1/reports", json={"day": "2026-10-20"}, headers={"Origin": "http://testserver"}
    )
    assert same.status_code == 201
    assert client.post("/api/v1/reports", json={"day": "2026-10-20"}).status_code == 200


def test_allowed_origins_setting(client, monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "machine.example.ts.net")
    response = client.post(
        "/api/v1/reports",
        json={"day": "2026-10-20"},
        headers={"Origin": "https://machine.example.ts.net"},
    )
    assert response.status_code == 201


@pytest.mark.parametrize("site", ["cross-site", "same-site"])
def test_browsers_marking_a_request_as_not_same_origin_are_refused(client, site):
    response = client.post("/api/v1/reports", json={"day": "2026-10-20"}, headers={"Sec-Fetch-Site": site})
    assert (response.status_code, response.json()["error"]["code"]) == (403, "bad_origin")


@pytest.mark.parametrize("site", ["same-origin", "none"])
def test_same_origin_requests_work_behind_a_proxy_that_rewrites_the_host(client, site):
    headers = {"Sec-Fetch-Site": site, "Origin": "https://machine.example.ts.net", "Host": "internal:3000"}
    response = client.post("/api/v1/reports", json={"day": "2026-10-20"}, headers=headers)
    assert response.status_code == 201


def test_a_cross_site_login_is_refused_too(anon_client):
    response = anon_client.post(
        LOGIN, json={"name": USER, "password": PASSWORD}, headers={"Sec-Fetch-Site": "cross-site"}
    )
    assert response.status_code == 403
