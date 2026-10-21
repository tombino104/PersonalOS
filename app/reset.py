import sqlite3
from datetime import datetime

from . import audit, db, seed


def wipe(conn: sqlite3.Connection, now: datetime) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for name in names:
            conn.execute(f'DROP TABLE IF EXISTS "{name}"')
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    db.migrate(conn)
    seed.sample_activities(conn)
    with conn:
        audit.log(conn, "user", "data.reset", None, now)
