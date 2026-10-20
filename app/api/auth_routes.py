import os
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response

from .. import auth
from .deps import (
    COOKIE_NAME,
    get_conn,
    get_now,
    get_session_token,
    get_user_id,
    verify_origin,
)
from .schemas import Login, PasswordChange

public_router = APIRouter(prefix="/api/v1/auth", dependencies=[Depends(verify_origin)])
protected_router = APIRouter(prefix="/auth")


def _cookie_secure(request: Request) -> bool:
    mode = os.environ.get("COOKIE_SECURE", "auto").lower()
    if mode in ("1", "true", "yes"):
        return True
    if mode in ("0", "false", "no"):
        return False
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    return request.url.scheme == "https" or forwarded == "https"


@public_router.post("/login")
def login(
    body: Login,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    token = auth.login(conn, body.name, body.password, now)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(auth.SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="strict",
        secure=_cookie_secure(request),
        path="/",
    )
    return {"name": body.name}


@protected_router.post("/logout")
def logout(
    response: Response,
    token: str | None = Depends(get_session_token),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    if token:
        auth.logout(conn, token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@protected_router.get("/me")
def me(
    user_id: int = Depends(get_user_id), conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    return {"name": auth.user_name(conn, user_id)}


@protected_router.post("/password")
def change_password(
    body: PasswordChange,
    user_id: int = Depends(get_user_id),
    token: str | None = Depends(get_session_token),
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    auth.change_password(conn, user_id, body.current_password, body.new_password, token, now)
    return {"ok": True}
