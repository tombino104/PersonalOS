import json
import sqlite3
from datetime import time

from .logical_day import DayRules


def get(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return default if row is None else json.loads(row["value"])


def put(conn: sqlite3.Connection, key: str, value) -> None:
    with conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )


def day_rules(conn: sqlite3.Connection) -> DayRules:
    return DayRules(
        timezone=get(conn, "timezone", "Europe/Rome"),
        cutoff=time.fromisoformat(get(conn, "day_cutoff", "04:00")),
    )
