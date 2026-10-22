import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from starlette.concurrency import run_in_threadpool

from .. import export
from .deps import get_conn, get_now, get_user_id

router = APIRouter(prefix="/export")


@router.get("")
async def download(
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> Response:
    data = await run_in_threadpool(export.build, conn, user_id, now)
    name = f"personal-os-export-{now.strftime('%Y%m%d')}.zip"
    return Response(
        data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"},
    )
