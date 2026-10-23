import asyncio
import logging
import os
from datetime import datetime, timezone

from .. import backup, config, db, push, reports
from .registry import Registry

logger = logging.getLogger("uvicorn.error")


def tick(registry: Registry, now: datetime) -> list[dict]:
    conn = db.connect(config.db_path())
    try:
        expired = reports.expire_reports(conn, now)
        try:
            backup.run_scheduled(conn, now)
        except Exception:
            logger.exception("the scheduled backup failed")
        try:
            push.run_reminder(conn, now)
        except Exception:
            logger.exception("the evening reminder failed")
    finally:
        conn.close()
    for item in expired:
        registry.dispatch("report.closed", {"day": item["day"], "report_id": item["report_id"]}, now)
    return expired


def interval() -> float:
    return float(os.environ.get("SCHEDULER_INTERVAL", "60"))


async def run(registry: Registry) -> None:
    while True:
        await asyncio.sleep(interval())
        try:
            await asyncio.to_thread(tick, registry, datetime.now(timezone.utc))
        except Exception:
            continue
