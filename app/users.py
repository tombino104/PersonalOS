import sqlite3

OWNER_NAME = "owner"
UNUSABLE_PASSWORD_HASH = "!"


def ensure_owner(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    if row is not None:
        return row["id"]
    with conn:
        cursor = conn.execute(
            "INSERT INTO users (name, password_hash) VALUES (?, ?)",
            (OWNER_NAME, UNUSABLE_PASSWORD_HASH),
        )
    return cursor.lastrowid
