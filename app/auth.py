import math
import sqlite3
from datetime import datetime, timedelta, timezone

from . import security

PLACEHOLDER_HASH = "!"
SESSION_LIFETIME = timedelta(days=30)
RENEW_AFTER = timedelta(hours=1)
MAX_FAILED_ATTEMPTS = 5
LOCKOUT = timedelta(minutes=15)


class InvalidCredentials(Exception):
    pass


class LockedOut(Exception):
    def __init__(self, retry_after: int):
        super().__init__("too many failed attempts")
        self.retry_after = retry_after


class UserExists(Exception):
    pass


class UserNotFound(Exception):
    pass


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def setup_required(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM users WHERE password_hash != ?", (PLACEHOLDER_HASH,)
    ).fetchone()
    return row[0] == 0


def create_user(conn: sqlite3.Connection, name: str, password: str) -> int:
    security.validate_new_password(password)
    rows = conn.execute("SELECT id, password_hash FROM users").fetchall()
    if any(row["password_hash"] != PLACEHOLDER_HASH for row in rows):
        raise UserExists("a user already exists; use reset-password instead")
    hashed = security.hash_password(password)
    with conn:
        if rows:
            conn.execute(
                "UPDATE users SET name = ?, password_hash = ? WHERE id = ?",
                (name, hashed, rows[0]["id"]),
            )
            return rows[0]["id"]
        cursor = conn.execute(
            "INSERT INTO users (name, password_hash) VALUES (?, ?)", (name, hashed)
        )
    return cursor.lastrowid


def reset_password(conn: sqlite3.Connection, name: str | None, password: str) -> str:
    security.validate_new_password(password)
    if name is None:
        rows = conn.execute("SELECT id, name FROM users").fetchall()
        if len(rows) != 1:
            raise UserNotFound("pass --name: there is no single user to pick")
        row = rows[0]
    else:
        row = conn.execute("SELECT id, name FROM users WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise UserNotFound(f"no user named {name}")
    with conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, failed_attempts = 0, locked_until = NULL "
            "WHERE id = ?",
            (security.hash_password(password), row["id"]),
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
    return row["name"]


def _authenticate(conn: sqlite3.Connection, row, password: str, now: datetime) -> None:
    locked_until = row["locked_until"]
    if locked_until is not None and _parse(locked_until) > now:
        remaining = (_parse(locked_until) - now).total_seconds()
        raise LockedOut(math.ceil(remaining))
    valid = row["password_hash"] != PLACEHOLDER_HASH and security.verify_password(
        password, row["password_hash"]
    )
    if valid:
        with conn:
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
                (row["id"],),
            )
        return
    failed = row["failed_attempts"] + 1
    locking = failed >= MAX_FAILED_ATTEMPTS
    with conn:
        conn.execute(
            "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
            (0 if locking else failed, _iso(now + LOCKOUT) if locking else None, row["id"]),
        )
    if locking:
        raise LockedOut(int(LOCKOUT.total_seconds()))
    raise InvalidCredentials("invalid name or password")


def _create_session(conn: sqlite3.Connection, user_id: int, now: datetime) -> str:
    token = security.new_token()
    with conn:
        conn.execute(
            "INSERT INTO sessions (user_id, token_hash, created_at, expires_at, last_used_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                security.hash_token(token),
                _iso(now),
                _iso(now + SESSION_LIFETIME),
                _iso(now),
            ),
        )
    return token


def login(conn: sqlite3.Connection, name: str, password: str, now: datetime) -> str:
    row = conn.execute(
        "SELECT id, password_hash, failed_attempts, locked_until FROM users WHERE name = ?",
        (name,),
    ).fetchone()
    if row is None:
        security.verify_password(password, security.dummy_hash())
        raise InvalidCredentials("invalid name or password")
    _authenticate(conn, row, password, now)
    return _create_session(conn, row["id"], now)


def resolve_session(conn: sqlite3.Connection, token: str, now: datetime) -> int | None:
    row = conn.execute(
        "SELECT id, user_id, expires_at, last_used_at FROM sessions WHERE token_hash = ?",
        (security.hash_token(token),),
    ).fetchone()
    if row is None:
        return None
    if _parse(row["expires_at"]) <= now:
        with conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (row["id"],))
        return None
    if now - _parse(row["last_used_at"]) >= RENEW_AFTER:
        with conn:
            conn.execute(
                "UPDATE sessions SET last_used_at = ?, expires_at = ? WHERE id = ?",
                (_iso(now), _iso(now + SESSION_LIFETIME), row["id"]),
            )
    return row["user_id"]


def logout(conn: sqlite3.Connection, token: str) -> None:
    with conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (security.hash_token(token),))


def user_name(conn: sqlite3.Connection, user_id: int) -> str:
    return conn.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()["name"]


def change_password(
    conn: sqlite3.Connection,
    user_id: int,
    current_password: str,
    new_password: str,
    keep_token: str | None,
    now: datetime,
) -> None:
    row = conn.execute(
        "SELECT id, password_hash, failed_attempts, locked_until FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    _authenticate(conn, row, current_password, now)
    security.validate_new_password(new_password)
    keep_hash = security.hash_token(keep_token) if keep_token else ""
    with conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (security.hash_password(new_password), user_id),
        )
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token_hash != ?", (user_id, keep_hash)
        )


def purge_expired_sessions(conn: sqlite3.Connection, now: datetime) -> int:
    with conn:
        cursor = conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (_iso(now),))
    return cursor.rowcount
