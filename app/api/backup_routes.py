import os
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from .. import backup, setup
from .deps import get_now
from .errors import ApiError

router = APIRouter(prefix="/backups")


def _require_confirmation(confirm: str | None) -> None:
    if confirm != "restore":
        raise ApiError(422, "confirmation_required", "confirm the restore with confirm=restore")


def _finish_restore(request: Request, now: datetime, safety: dict) -> dict:
    setup.finish()
    registry = getattr(request.app.state, "plugins", None)
    if registry is not None:
        registry.refresh(now)
    return {"restored": True, "safety_backup": safety}


@router.get("")
def list_backups() -> dict:
    return {"backups": backup.list_backups(), "keep": backup.KINDS}


@router.post("", status_code=201)
async def create_backup(now: datetime = Depends(get_now)) -> dict:
    return await run_in_threadpool(backup.create, "manual", now)


@router.post("/restore")
async def restore_upload(
    request: Request,
    confirm: str | None = Query(None),
    now: datetime = Depends(get_now),
) -> dict:
    _require_confirmation(confirm)
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > backup.MAX_UPLOAD_BYTES:
        raise ApiError(413, "too_large", "the file is too large")
    folder = backup.directory()
    handle, name = tempfile.mkstemp(prefix=".upload-", suffix=".zip", dir=folder)
    path = Path(name)
    try:
        received = 0
        with os.fdopen(handle, "wb") as out:
            async for chunk in request.stream():
                received += len(chunk)
                if received > backup.MAX_UPLOAD_BYTES:
                    raise ApiError(413, "too_large", "the file is too large")
                out.write(chunk)
        safety = await run_in_threadpool(backup.restore, path, now)
    finally:
        path.unlink(missing_ok=True)
    return _finish_restore(request, now, safety)


@router.get("/{name}")
def download(name: str) -> FileResponse:
    path = backup.path_for(name)
    return FileResponse(path, media_type="application/zip", filename=name)


@router.post("/{name}/restore")
async def restore_stored(
    name: str,
    request: Request,
    confirm: str | None = Query(None),
    now: datetime = Depends(get_now),
) -> dict:
    _require_confirmation(confirm)
    path = backup.path_for(name)
    safety = await run_in_threadpool(backup.restore, path, now)
    return _finish_restore(request, now, safety)
