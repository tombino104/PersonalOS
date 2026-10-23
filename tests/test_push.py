import base64
import json
from datetime import date

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from app import push, reports, settings
from app.logical_day import DayRules
from tests.conftest import utc

ENDPOINT = "https://web.push.apple.com/abc123"


def decode(part):
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


@pytest.fixture
def sent(monkeypatch):
    calls = []

    def fake(endpoint, authorization):
        calls.append((endpoint, authorization))
        return 201

    monkeypatch.setattr(push, "_post", fake)
    return calls


@pytest.fixture
def armed(conn):
    settings.put(conn, "timezone", "UTC")
    settings.put(conn, "reminder_enabled", True)
    settings.put(conn, "reminder_time", "21:00")
    push.subscribe(conn, ENDPOINT, utc(2026, 10, 20, 12))
    return conn


def test_the_vapid_key_is_created_once_and_kept(conn):
    first = push.public_key(conn)
    assert push.public_key(conn) == first
    assert len(decode(first)) == 65


def test_the_authorization_is_a_valid_signed_token(conn):
    now = utc(2026, 10, 20, 12)
    header = push._authorization(conn, ENDPOINT, now)
    token, key = header.removeprefix("vapid t=").split(", k=")
    assert key == push.public_key(conn)
    head, claims, signature = token.split(".")
    assert json.loads(decode(head)) == {"typ": "JWT", "alg": "ES256"}
    body = json.loads(decode(claims))
    assert body["aud"] == "https://web.push.apple.com"
    assert body["sub"].startswith("https://")
    assert body["exp"] > now.timestamp()
    raw = decode(signature)
    public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), decode(key))
    public.verify(
        encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
        f"{head}.{claims}".encode(),
        ec.ECDSA(hashes.SHA256()),
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://web.push.apple.com/abc",
        "https://localhost/abc",
        "https://127.0.0.1/abc",
        "https://192.168.1.3/abc",
        "https://user:pass@web.push.apple.com/abc",
        "not a url",
        "https://web.push.apple.com/" + "a" * 3000,
    ],
)
def test_only_public_https_endpoints_are_accepted(conn, endpoint):
    with pytest.raises(push.InvalidEndpoint):
        push.subscribe(conn, endpoint, utc(2026, 10, 20, 12))
    assert push.device_count(conn) == 0


def test_subscribing_twice_keeps_one_device(conn):
    push.subscribe(conn, ENDPOINT, utc(2026, 10, 20, 12))
    push.subscribe(conn, ENDPOINT, utc(2026, 10, 21, 12))
    assert push.device_count(conn) == 1
    push.unsubscribe(conn, ENDPOINT)
    assert push.device_count(conn) == 0


def test_nothing_is_sent_when_the_reminder_is_off(armed, sent):
    settings.put(armed, "reminder_enabled", False)
    assert push.run_reminder(armed, utc(2026, 10, 20, 21, 30)) is None
    assert sent == []


def test_nothing_is_sent_before_the_chosen_time(armed, sent):
    assert push.run_reminder(armed, utc(2026, 10, 20, 20, 59)) is None
    assert sent == []


def test_it_is_sent_once_a_day_at_the_chosen_time(armed, sent):
    assert push.run_reminder(armed, utc(2026, 10, 20, 21, 0)) == 1
    assert push.run_reminder(armed, utc(2026, 10, 20, 21, 1)) is None
    assert len(sent) == 1
    assert sent[0][0] == ENDPOINT
    assert push.run_reminder(armed, utc(2026, 10, 21, 21, 5)) == 1
    assert len(sent) == 2


def test_a_reminder_that_is_hours_late_is_dropped(armed, sent):
    assert push.run_reminder(armed, utc(2026, 10, 20, 23, 59)) == 1
    settings.put(armed, "last_reminder_date", None)
    assert push.run_reminder(armed, utc(2026, 10, 21, 0, 30)) is None
    assert len(sent) == 1


def test_the_time_follows_the_configured_timezone(armed, sent):
    settings.put(armed, "timezone", "Europe/Rome")
    assert push.run_reminder(armed, utc(2026, 10, 20, 18, 59)) is None
    assert push.run_reminder(armed, utc(2026, 10, 20, 19, 30)) == 1


def test_a_finished_report_skips_the_reminder(armed, sent, user_id):
    now = utc(2026, 10, 20, 20, 0)
    report_id = reports.open_report(armed, user_id, date(2026, 10, 20), now, DayRules(timezone="UTC"))
    reports.complete_report(armed, report_id, now)
    assert push.run_reminder(armed, utc(2026, 10, 20, 21, 5)) == 0
    assert sent == []
    assert push.run_reminder(armed, utc(2026, 10, 20, 21, 10)) is None


def test_an_unfinished_report_still_gets_the_reminder(armed, sent, user_id):
    now = utc(2026, 10, 20, 20, 0)
    reports.open_report(armed, user_id, date(2026, 10, 20), now, DayRules(timezone="UTC"))
    assert push.run_reminder(armed, utc(2026, 10, 20, 21, 5)) == 1


def test_a_gone_subscription_is_removed(armed, monkeypatch):
    monkeypatch.setattr(push, "_post", lambda endpoint, authorization: 410)
    assert push.run_reminder(armed, utc(2026, 10, 20, 21, 0)) == 0
    assert push.device_count(armed) == 0


def test_a_failing_push_service_does_not_stop_the_others(armed, monkeypatch):
    push.subscribe(armed, "https://fcm.googleapis.com/def", utc(2026, 10, 20, 12))
    calls = []

    def fake(endpoint, authorization):
        calls.append(endpoint)
        if endpoint == ENDPOINT:
            raise OSError("unreachable")
        return 201

    monkeypatch.setattr(push, "_post", fake)
    assert push.send_all(armed, utc(2026, 10, 20, 21, 0)) == 1
    assert len(calls) == 2
    assert push.device_count(armed) == 2


def test_the_api_stores_devices_and_settings(client, sent):
    status = client.get("/api/v1/push").json()
    assert len(decode(status["public_key"])) == 65
    assert status["devices"] == 0
    assert client.post("/api/v1/push/subscriptions", json={"endpoint": ENDPOINT}).json() == {"devices": 1}
    assert client.post("/api/v1/push/subscriptions", json={"endpoint": "http://x.test/a"}).status_code == 422
    assert client.post("/api/v1/push/test").json() == {"sent": 1}
    assert client.post("/api/v1/push/subscriptions/remove", json={"endpoint": ENDPOINT}).json() == {"devices": 0}


def test_the_reminder_settings_round_trip(client):
    current = client.get("/api/v1/settings").json()
    assert current["reminder_enabled"] is False
    assert current["reminder_time"] == "21:00"
    changed = client.patch("/api/v1/settings", json={"reminder_enabled": True, "reminder_time": "22:15"})
    assert changed.status_code == 200
    again = client.get("/api/v1/settings").json()
    assert again["reminder_enabled"] is True
    assert again["reminder_time"] == "22:15"
    assert client.patch("/api/v1/settings", json={"reminder_time": "25:99"}).json()["error"]["code"] == "invalid_reminder_time"
    assert "push_vapid_private" not in json.dumps(again)


def test_the_api_needs_a_login(anon_client):
    assert anon_client.get("/api/v1/push").status_code == 401
    assert anon_client.post("/api/v1/push/test").status_code == 401


def test_the_request_has_no_body_and_carries_the_vapid_header():
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["length"] = self.headers.get("Content-Length")
            seen["authorization"] = self.headers.get("Authorization")
            seen["ttl"] = self.headers.get("TTL")
            seen["body"] = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            self.send_response(201)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    try:
        status = push._post(f"http://127.0.0.1:{server.server_port}/push", "vapid t=a.b.c, k=key")
    finally:
        thread.join()
        server.server_close()
    assert status == 201
    assert seen == {"length": "0", "authorization": "vapid t=a.b.c, k=key", "ttl": "7200", "body": b""}
