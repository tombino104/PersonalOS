import os
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response

from .. import auth, reset, setup
from .deps import (
    COOKIE_NAME,
    get_conn,
    get_now,
    get_session_token,
    get_user_id,
    verify_origin,
)
from .schemas import Login, PasswordChange, ResetRequest, Setup

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


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(auth.SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="strict",
        secure=_cookie_secure(request),
        path="/",
    )


@public_router.get("/status")
def status(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    return {"setup_required": auth.setup_required(conn), "setup_code_required": setup.code_required()}


@public_router.post("/setup")
def first_run_setup(
    body: Setup,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    if not auth.setup_required(conn):
        raise setup.SetupDone("an account already exists")
    if setup.code_required():
        setup.verify(body.code, now)
    auth.create_user(conn, body.name, body.password)
    setup.finish()
    token = auth.login(conn, body.name, body.password, now)
    _set_session_cookie(request, response, token)
    return {"name": body.name}


@public_router.post("/reset")
def reset_everything(
    body: ResetRequest,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    setup.verify(body.code, now)
    reset.wipe(conn, now)
    request.app.state.plugins.apply_defaults(now)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"setup_required": True}


@public_router.post("/login")
def login(
    body: Login,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    token = auth.login(conn, body.name, body.password, now)
    _set_session_cookie(request, response, token)
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
