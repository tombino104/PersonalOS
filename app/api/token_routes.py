import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .. import tokens
from .deps import get_conn, get_now
from .errors import ApiError

router = APIRouter(prefix="/tokens")


class TokenCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=60)
    plugin: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("the name cannot be empty")
        return value


@router.get("")
def list_tokens(
    plugin: str | None = Query(None, max_length=32), conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    return {"tokens": tokens.list_tokens(conn, plugin)}


@router.post("", status_code=201)
def create_token(
    body: TokenCreate,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    registry = getattr(request.app.state, "plugins", None)
    loaded = registry.get(body.plugin) if registry is not None else None
    if loaded is None or loaded.manifest is None or "ingest" not in loaded.manifest.permissions:
        raise ApiError(422, "no_ingest", "this plugin does not accept data from outside")
    try:
        row, secret = tokens.create(conn, body.name, body.plugin, now)
    except tokens.TooManyTokens:
        raise ApiError(409, "too_many_tokens", "revoke a token before creating another") from None
    return {**row, "token": secret}


@router.delete("/{token_id}")
def revoke_token(
    token_id: int, conn: sqlite3.Connection = Depends(get_conn), now: datetime = Depends(get_now)
) -> dict:
    try:
        tokens.revoke(conn, token_id, now)
    except tokens.TokenNotFound:
        raise ApiError(404, "not_found", "token not found") from None
    return {"ok": True}
