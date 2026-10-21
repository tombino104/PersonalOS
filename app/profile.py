import sqlite3
from datetime import datetime, timezone

MAX_PHOTO_BYTES = 2 * 1024 * 1024
FIELDS = ("display_name", "about", "birth_year")


class InvalidPhoto(Exception):
    pass


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def detect_type(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _ensure(conn: sqlite3.Connection, now: datetime) -> None:
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO profile (id, updated_at) VALUES (1, ?)", (_iso(now),)
        )


def get(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT display_name, about, birth_year, photo IS NOT NULL AS has_photo, updated_at "
        "FROM profile WHERE id = 1"
    ).fetchone()
    if row is None:
        return {
            "display_name": None,
            "about": None,
            "birth_year": None,
            "has_photo": False,
            "version": None,
        }
    return {
        "display_name": row["display_name"],
        "about": row["about"],
        "birth_year": row["birth_year"],
        "has_photo": bool(row["has_photo"]),
        "version": row["updated_at"],
    }


def update(conn: sqlite3.Connection, changes: dict, now: datetime) -> dict:
    _ensure(conn, now)
    with conn:
        for key in FIELDS:
            if key in changes:
                conn.execute(f"UPDATE profile SET {key} = ? WHERE id = 1", (changes[key],))
        conn.execute("UPDATE profile SET updated_at = ? WHERE id = 1", (_iso(now),))
    return get(conn)


def set_photo(conn: sqlite3.Connection, data: bytes, now: datetime) -> dict:
    if not data or len(data) > MAX_PHOTO_BYTES:
        raise InvalidPhoto("the photo must be between 1 byte and 2 MB")
    kind = detect_type(data)
    if kind is None:
        raise InvalidPhoto("the photo must be a JPEG, PNG or WebP image")
    _ensure(conn, now)
    with conn:
        conn.execute(
            "UPDATE profile SET photo = ?, photo_type = ?, updated_at = ? WHERE id = 1",
            (data, kind, _iso(now)),
        )
    return get(conn)


def remove_photo(conn: sqlite3.Connection, now: datetime) -> dict:
    _ensure(conn, now)
    with conn:
        conn.execute(
            "UPDATE profile SET photo = NULL, photo_type = NULL, updated_at = ? WHERE id = 1",
            (_iso(now),),
        )
    return get(conn)


def photo(conn: sqlite3.Connection) -> tuple[bytes, str] | None:
    row = conn.execute("SELECT photo, photo_type FROM profile WHERE id = 1").fetchone()
    if row is None or row["photo"] is None:
        return None
    return bytes(row["photo"]), row["photo_type"]
