import sqlite3
from datetime import datetime, timezone

from . import audit, security

PREFIX = "pos_"
MAX_ACTIVE = 20


class TooManyTokens(Exception):
    pass


class TokenNotFound(Exception):
    pass


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _public(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "plugin": row["plugin"],
        "created_at": row["created_at"],
        "last_used_at": row["last_used_at"],
    }


def create(conn: sqlite3.Connection, name: str, plugin: str, now: datetime) -> tuple[dict, str]:
    active = conn.execute("SELECT COUNT(*) FROM api_tokens WHERE revoked_at IS NULL").fetchone()[0]
    if active >= MAX_ACTIVE:
        raise TooManyTokens()
    token = PREFIX + security.new_token()
    with conn:
        cursor = conn.execute(
            "INSERT INTO api_tokens (name, plugin, token_hash, created_at) VALUES (?, ?, ?, ?)",
            (name, plugin, security.hash_token(token), _iso(now)),
        )
        audit.log(conn, "user", "token.created", {"plugin": plugin, "name": name}, now)
    row = conn.execute("SELECT * FROM api_tokens WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _public(row), token


def list_tokens(conn: sqlite3.Connection, plugin: str | None = None) -> list[dict]:
    sql = "SELECT * FROM api_tokens WHERE revoked_at IS NULL"
    params: list = []
    if plugin is not None:
        sql += " AND plugin = ?"
        params.append(plugin)
    return [_public(row) for row in conn.execute(sql + " ORDER BY id", params)]


def revoke(conn: sqlite3.Connection, token_id: int, now: datetime) -> None:
    with conn:
        row = conn.execute(
            "SELECT plugin, name FROM api_tokens WHERE id = ? AND revoked_at IS NULL", (token_id,)
        ).fetchone()
        if row is None:
            raise TokenNotFound()
        conn.execute("UPDATE api_tokens SET revoked_at = ? WHERE id = ?", (_iso(now), token_id))
        audit.log(conn, "user", "token.revoked", {"plugin": row["plugin"], "name": row["name"]}, now)


def authenticate(conn: sqlite3.Connection, secret: str, plugin: str, now: datetime) -> bool:
    row = conn.execute(
        "SELECT id FROM api_tokens WHERE token_hash = ? AND plugin = ? AND revoked_at IS NULL",
        (security.hash_token(secret), plugin),
    ).fetchone()
    if row is None:
        return False
    with conn:
        conn.execute("UPDATE api_tokens SET last_used_at = ? WHERE id = ?", (_iso(now), row["id"]))
    return True
