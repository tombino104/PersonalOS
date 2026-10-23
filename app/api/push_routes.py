import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from .. import push
from .deps import get_conn, get_now
from .errors import ApiError

router = APIRouter(prefix="/push")


class Endpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint: str


@router.get("")
def status(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    return {"public_key": push.public_key(conn), "devices": push.device_count(conn)}


@router.post("/subscriptions", status_code=201)
def subscribe(
    body: Endpoint, conn: sqlite3.Connection = Depends(get_conn), now: datetime = Depends(get_now)
) -> dict:
    try:
        push.subscribe(conn, body.endpoint, now)
    except push.InvalidEndpoint as error:
        raise ApiError(422, "invalid_endpoint", str(error)) from None
    return {"devices": push.device_count(conn)}


@router.post("/subscriptions/remove")
def unsubscribe(body: Endpoint, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    push.unsubscribe(conn, body.endpoint)
    return {"devices": push.device_count(conn)}


@router.post("/test")
async def test(conn: sqlite3.Connection = Depends(get_conn), now: datetime = Depends(get_now)) -> dict:
    return {"sent": await run_in_threadpool(push.send_all, conn, now)}
