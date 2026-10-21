import sqlite3
from datetime import datetime, timezone

SOFT_LIMIT_PER_AREA = 5

_SELECT = (
    "SELECT act.id, act.name, act.weight, act.cadence, act.days, act.created_at, act.archived_at, "
    "a.slug AS area FROM activities act JOIN areas a ON a.id = act.area_id"
)


class ActivityNotFound(KeyError):
    pass


class UnknownArea(ValueError):
    pass


class InvalidDays(ValueError):
    pass


ALL_DAYS = 127


def days_to_mask(days: list[int]) -> int:
    if not days or len(set(days)) != len(days) or any(day not in range(7) for day in days):
        raise InvalidDays("days must be a non-empty list of different weekdays, 0 (Monday) to 6 (Sunday)")
    return sum(1 << day for day in days)


def mask_to_days(mask: int) -> list[int]:
    return [day for day in range(7) if mask & (1 << day)]


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
        "days": mask_to_days(row["days"]),
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
    conn: sqlite3.Connection,
    area_slug: str,
    name: str,
    weight: int,
    now: datetime,
    days: list[int] | None = None,
) -> dict:
    area_id = _area_id(conn, area_slug)
    mask = ALL_DAYS if days is None else days_to_mask(days)
    with conn:
        cursor = conn.execute(
            "INSERT INTO activities (area_id, name, weight, days, created_at) VALUES (?, ?, ?, ?, ?)",
            (area_id, name, weight, mask, _iso(now)),
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
    if "days" in changes:
        assignments.append("days = ?")
        params.append(days_to_mask(changes["days"]))
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
