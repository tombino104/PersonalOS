import json
import sqlite3
from datetime import datetime, timezone


def log(
    conn: sqlite3.Connection,
    actor: str,
    action: str,
    detail: dict | None = None,
    now: datetime | None = None,
) -> None:
    moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    conn.execute(
        "INSERT INTO audit_log (at, actor, action, detail) VALUES (?, ?, ?, ?)",
        (moment.isoformat(timespec="seconds"), actor, action, json.dumps(detail or {})),
    )
