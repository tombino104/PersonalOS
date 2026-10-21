import sqlite3
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .. import profile
from .deps import get_conn, get_now
from .errors import ApiError

router = APIRouter(prefix="/profile")


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] | None = None
    about: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    birth_year: int | None = Field(default=None, ge=1900, le=2100)


@router.get("")
def get_profile(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    return profile.get(conn)


@router.put("")
def update_profile(
    body: ProfileUpdate,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    changes = {key: body.__dict__[key] or None for key in body.model_fields_set}
    return profile.update(conn, changes, now)


@router.put("/photo")
async def put_photo(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > profile.MAX_PHOTO_BYTES:
        raise ApiError(413, "too_large", "the photo is too large")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > profile.MAX_PHOTO_BYTES:
            raise ApiError(413, "too_large", "the photo is too large")
    return profile.set_photo(conn, bytes(data), now)


@router.delete("/photo")
def delete_photo(
    conn: sqlite3.Connection = Depends(get_conn), now: datetime = Depends(get_now)
) -> dict:
    return profile.remove_photo(conn, now)


@router.get("/photo")
def get_photo(conn: sqlite3.Connection = Depends(get_conn)) -> Response:
    found = profile.photo(conn)
    if found is None:
        raise ApiError(404, "not_found", "no photo")
    data, kind = found
    return Response(data, media_type=kind, headers={"Cache-Control": "private, max-age=3600"})
