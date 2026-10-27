import json
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from .. import tokens
from ..plugins.registry import IngestFailed, PluginUnavailable
from .deps import get_conn, get_now
from .errors import ApiError

router = APIRouter(prefix="/api/v1/ingest")

MAX_BODY_BYTES = 1_000_000


def _secret(request: Request) -> str | None:
    scheme, _, value = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    return request.headers.get("x-api-key", "").strip() or None


async def _read_json(request: Request):
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise ApiError(413, "too_large", "the request is too large")
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise ApiError(413, "too_large", "the request is too large")
        chunks.append(chunk)
    try:
        return json.loads(b"".join(chunks))
    except ValueError:
        raise ApiError(422, "invalid_json", "the body must be JSON") from None


@router.post("/{plugin_id}")
async def ingest(
    plugin_id: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    secret = _secret(request)
    if secret is None or not await run_in_threadpool(tokens.authenticate, conn, secret, plugin_id, now):
        raise ApiError(401, "unauthorized", "a valid token is needed")
    payload = await _read_json(request)
    registry = getattr(request.app.state, "plugins", None)
    if registry is None:
        raise ApiError(503, "plugins_unavailable", "the plugin system is not running")
    try:
        await run_in_threadpool(registry.ingest, plugin_id, payload, now)
    except PluginUnavailable:
        raise ApiError(404, "plugin_inactive", "this plugin is not active") from None
    except IngestFailed:
        raise ApiError(500, "plugin_error", "the plugin failed") from None
    except ValueError as error:
        raise ApiError(422, "invalid_payload", str(error)[:200]) from None
    return {"ok": True}
