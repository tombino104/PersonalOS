import os
import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import Depends, Request

from .. import auth, config, db
from .errors import ApiError

COOKIE_NAME = "personal_os_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = db.connect(config.db_path(), check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


def get_now() -> datetime:
    return datetime.now(timezone.utc)


def get_session_token(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)


def get_user_id(
    token: str | None = Depends(get_session_token),
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> int:
    user_id = auth.resolve_session(conn, token, now) if token else None
    if user_id is None:
        raise ApiError(401, "unauthorized", "login required")
    return user_id


def verify_origin(request: Request) -> None:
    if request.method in SAFE_METHODS:
        return
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None:
        if fetch_site in ("same-origin", "none"):
            return
        raise ApiError(403, "bad_origin", "request origin not allowed")
    origin = request.headers.get("origin")
    if origin is None:
        return
    allowed = {request.headers.get("host"), request.headers.get("x-forwarded-host")}
    allowed.update(
        item.strip() for item in os.environ.get("ALLOWED_ORIGINS", "").split(",") if item.strip()
    )
    if urlsplit(origin).netloc not in allowed:
        raise ApiError(403, "bad_origin", "request origin not allowed")
