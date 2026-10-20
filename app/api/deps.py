import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone

from fastapi import Depends

from .. import config, db, users


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = db.connect(config.db_path(), check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


def get_now() -> datetime:
    return datetime.now(timezone.utc)


def get_user_id(conn: sqlite3.Connection = Depends(get_conn)) -> int:
    return users.ensure_owner(conn)
