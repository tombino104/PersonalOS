import base64
import ipaddress
import json
import logging
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, time, timedelta, timezone
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from . import reports, settings
from .logical_day import logical_day

logger = logging.getLogger("uvicorn.error")

SUBJECT = "https://github.com/tombino104/PersonalOS"
DEFAULT_TIME = "21:00"
LATE_WINDOW = timedelta(hours=3)
MAX_ENDPOINT = 2048
TOKEN_LIFETIME = timedelta(hours=12)
TIMEOUT = 10


class InvalidEndpoint(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _load_key(conn: sqlite3.Connection) -> ec.EllipticCurvePrivateKey:
    stored = settings.get(conn, "push_vapid_private")
    if stored is not None:
        padded = stored + "=" * (-len(stored) % 4)
        return ec.derive_private_key(
            int.from_bytes(base64.urlsafe_b64decode(padded), "big"), ec.SECP256R1()
        )
    key = ec.generate_private_key(ec.SECP256R1())
    settings.put(conn, "push_vapid_private", _b64(key.private_numbers().private_value.to_bytes(32, "big")))
    return key


def public_key(conn: sqlite3.Connection) -> str:
    point = _load_key(conn).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return _b64(point)


def _authorization(conn: sqlite3.Connection, endpoint: str, now: datetime) -> str:
    parts = urlsplit(endpoint)
    claims = {
        "aud": f"{parts.scheme}://{parts.netloc}",
        "exp": int((now + TOKEN_LIFETIME).timestamp()),
        "sub": SUBJECT,
    }
    signing_input = (
        _b64(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
        + "."
        + _b64(json.dumps(claims, separators=(",", ":")).encode())
    )
    key = _load_key(conn)
    r, s = decode_dss_signature(key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256())))
    token = signing_input + "." + _b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    return f"vapid t={token}, k={public_key(conn)}"


def validate_endpoint(endpoint: str) -> str:
    if len(endpoint) > MAX_ENDPOINT:
        raise InvalidEndpoint("the endpoint is too long")
    parts = urlsplit(endpoint)
    host = parts.hostname
    if parts.scheme != "https" or not host or parts.username or parts.password:
        raise InvalidEndpoint("the endpoint must be an https address")
    if host == "localhost" or host.endswith(".localhost"):
        raise InvalidEndpoint("the endpoint must be a public push service")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return endpoint
    raise InvalidEndpoint("the endpoint must be a public push service")


def subscribe(conn: sqlite3.Connection, endpoint: str, now: datetime) -> None:
    validate_endpoint(endpoint)
    with conn:
        conn.execute(
            "INSERT INTO push_subscriptions (endpoint, created_at) VALUES (?, ?) "
            "ON CONFLICT (endpoint) DO NOTHING",
            (endpoint, now.astimezone(timezone.utc).isoformat(timespec="seconds")),
        )


def unsubscribe(conn: sqlite3.Connection, endpoint: str) -> None:
    with conn:
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))


def device_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM push_subscriptions").fetchone()["n"]


def _post(endpoint: str, authorization: str) -> int:
    request = urllib.request.Request(
        endpoint,
        data=b"",
        method="POST",
        headers={"Authorization": authorization, "TTL": "7200", "Urgency": "normal", "Content-Length": "0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def send_all(conn: sqlite3.Connection, now: datetime) -> int:
    endpoints = [row["endpoint"] for row in conn.execute("SELECT endpoint FROM push_subscriptions")]
    delivered = 0
    for endpoint in endpoints:
        try:
            status = _post(endpoint, _authorization(conn, endpoint, now))
        except Exception:
            logger.exception("a push notification could not be sent")
            continue
        if status in (404, 410):
            unsubscribe(conn, endpoint)
        elif 200 <= status < 300:
            delivered += 1
    return delivered


def reminder(conn: sqlite3.Connection) -> dict:
    return {
        "enabled": bool(settings.get(conn, "reminder_enabled", False)),
        "time": settings.get(conn, "reminder_time", DEFAULT_TIME),
    }


def _report_completed(conn: sqlite3.Connection, day) -> bool:
    for row in conn.execute("SELECT id FROM users"):
        report_id = reports.report_id_for_day(conn, row["id"], day)
        if report_id is None:
            continue
        done = conn.execute("SELECT completed_at FROM reports WHERE id = ?", (report_id,)).fetchone()
        if done["completed_at"] is not None:
            return True
    return False


def run_reminder(conn: sqlite3.Connection, now: datetime) -> int | None:
    config = reminder(conn)
    if not config["enabled"]:
        return None
    rules = settings.day_rules(conn)
    local = now.astimezone(rules.zone)
    due = datetime.combine(local.date(), time.fromisoformat(config["time"]), tzinfo=rules.zone)
    if local < due or local - due > LATE_WINDOW:
        return None
    today = local.date().isoformat()
    if settings.get(conn, "last_reminder_date") == today:
        return None
    settings.put(conn, "last_reminder_date", today)
    if _report_completed(conn, logical_day(now, rules)):
        return 0
    return send_all(conn, now)
