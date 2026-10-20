import sqlite3
from datetime import datetime, timezone

SOFT_LIMIT_PER_AREA = 5

_SELECT = (
    "SELECT act.id, act.name, act.weight, act.cadence, act.created_at, act.archived_at, "
    "a.slug AS area FROM activities act JOIN areas a ON a.id = act.area_id"
)


class ActivityNotFound(KeyError):
    pass


class UnknownArea(ValueError):
    pass


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _area_id(conn: sqlite3.Connection, slug: str) -> int:
    row = conn.execute("SELECT id FROM areas WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise UnknownArea(f"unknown area: {slug}")
    return row["id"]


def _as_dict(row) -> dict:
    return {
        "id": row["id"],
        "area": row["area"],
        "name": row["name"],
        "weight": row["weight"],
        "cadence": row["cadence"],
        "created_at": row["created_at"],
        "archived_at": row["archived_at"],
    }


def get(conn: sqlite3.Connection, activity_id: int) -> dict:
    row = conn.execute(f"{_SELECT} WHERE act.id = ?", (activity_id,)).fetchone()
    if row is None:
        raise ActivityNotFound(f"activity {activity_id} not found")
    return _as_dict(row)


def list_activities(conn: sqlite3.Connection, include_archived: bool = False) -> list[dict]:
    where = "" if include_archived else " WHERE act.archived_at IS NULL"
    rows = conn.execute(f"{_SELECT}{where} ORDER BY a.position, act.id").fetchall()
    return [_as_dict(r) for r in rows]


def create(
    conn: sqlite3.Connection, area_slug: str, name: str, weight: int, now: datetime
) -> dict:
    area_id = _area_id(conn, area_slug)
    with conn:
        cursor = conn.execute(
            "INSERT INTO activities (area_id, name, weight, created_at) VALUES (?, ?, ?, ?)",
            (area_id, name, weight, _iso(now)),
        )
    return get(conn, cursor.lastrowid)


def update(conn: sqlite3.Connection, activity_id: int, changes: dict, now: datetime) -> dict:
    current = get(conn, activity_id)
    assignments: list[str] = []
    params: list = []
    if "name" in changes:
        assignments.append("name = ?")
        params.append(changes["name"])
    if "area" in changes:
        assignments.append("area_id = ?")
        params.append(_area_id(conn, changes["area"]))
    if "weight" in changes:
        assignments.append("weight = ?")
        params.append(changes["weight"])
    if "archived" in changes:
        assignments.append("archived_at = ?")
        if changes["archived"]:
            params.append(current["archived_at"] or _iso(now))
        else:
            params.append(None)
    if assignments:
        with conn:
            conn.execute(
                f"UPDATE activities SET {', '.join(assignments)} WHERE id = ?",
                (*params, activity_id),
            )
    return get(conn, activity_id)


def warnings(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT a.slug, COUNT(*) AS n FROM activities act "
        "JOIN areas a ON a.id = act.area_id WHERE act.archived_at IS NULL "
        "GROUP BY a.id HAVING n > ? ORDER BY a.position",
        (SOFT_LIMIT_PER_AREA,),
    ).fetchall()
    return [
        {
            "code": "too_many_activities",
            "area": r["slug"],
            "count": r["n"],
            "suggested_max": SOFT_LIMIT_PER_AREA,
        }
        for r in rows
    ]
