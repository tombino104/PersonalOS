import sqlite3
from datetime import date, datetime, time, timedelta, timezone

from . import settings
from .logical_day import DayRules, edit_deadline, logical_day
from .scoring import Item, mean_score, score, tally, weekly_forced


class ReportClosed(Exception):
    pass


class FutureDay(ValueError):
    pass


class ReportNotOpen(Exception):
    def __init__(self, opens_at: str):
        super().__init__(f"the report opens at {opens_at}")
        self.opens_at = opens_at


class ReportNotFound(KeyError):
    pass


class NotInReport(KeyError):
    pass


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def opens_at(conn: sqlite3.Connection, day: date) -> datetime | None:
    if not settings.get(conn, "report_lock", False):
        return None
    zone = settings.day_rules(conn).zone
    at = time.fromisoformat(settings.get(conn, "report_time", "20:00"))
    return datetime.combine(day, at, tzinfo=zone)


def require_open_time(conn: sqlite3.Connection, day: date, now: datetime) -> None:
    moment = opens_at(conn, day)
    if moment is not None and now < moment:
        raise ReportNotOpen(moment.strftime("%H:%M"))


def _require_editable(conn: sqlite3.Connection, report_id: int, now: datetime) -> None:
    row = conn.execute(
        "SELECT status, editable_until, day FROM reports WHERE id = ?", (report_id,)
    ).fetchone()
    if row is None:
        raise ReportNotFound(f"report {report_id} not found")
    if row["status"] == "closed" or now >= datetime.fromisoformat(row["editable_until"]):
        raise ReportClosed(f"report {report_id} is closed")
    require_open_time(conn, date.fromisoformat(row["day"]), now)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def weekly_progress(conn: sqlite3.Connection, activity_id: int, target: int, day: date) -> dict:
    done_before = conn.execute(
        "SELECT COUNT(*) FROM completions c JOIN reports r ON r.id = c.report_id "
        "WHERE c.activity_id = ? AND c.done = 1 AND r.completed_at IS NOT NULL "
        "AND r.day >= ? AND r.day < ?",
        (activity_id, _week_start(day).isoformat(), day.isoformat()),
    ).fetchone()[0]
    mask = conn.execute("SELECT days FROM activities WHERE id = ?", (activity_id,)).fetchone()["days"]
    days_left = sum(1 for weekday in range(day.weekday(), 7) if mask & (1 << weekday))
    return {
        "target": target,
        "done_before": done_before,
        "forced": weekly_forced(target, done_before, days_left),
    }


def _write_scores(conn: sqlite3.Connection, report_id: int, cascade: bool = True) -> None:
    day = date.fromisoformat(
        conn.execute("SELECT day FROM reports WHERE id = ?", (report_id,)).fetchone()["day"]
    )
    per_area: dict[int, list[Item]] = {
        row["id"]: [] for row in conn.execute("SELECT id FROM areas")
    }
    for row in conn.execute(
        "SELECT area_id, activity_id, weight_at_time, done, target_at_time "
        "FROM completions WHERE report_id = ?",
        (report_id,),
    ).fetchall():
        optional = False
        if row["target_at_time"] is not None:
            progress = weekly_progress(conn, row["activity_id"], row["target_at_time"], day)
            optional = not progress["forced"]
        per_area[row["area_id"]].append(Item(row["weight_at_time"], bool(row["done"]), optional))
    conn.execute("DELETE FROM daily_scores WHERE report_id = ?", (report_id,))
    for area_id, items in per_area.items():
        maximum, obtained = tally(items)
        conn.execute(
            "INSERT INTO daily_scores (report_id, area_id, maximum, obtained) "
            "VALUES (?, ?, ?, ?)",
            (report_id, area_id, maximum, obtained),
        )
    if cascade:
        later = conn.execute(
            "SELECT id FROM reports WHERE user_id = (SELECT user_id FROM reports WHERE id = ?) "
            "AND completed_at IS NOT NULL AND day > ? AND day <= ?",
            (report_id, day.isoformat(), (_week_start(day) + timedelta(days=6)).isoformat()),
        ).fetchall()
        for item in later:
            _write_scores(conn, item["id"], cascade=False)


def open_report(
    conn: sqlite3.Connection, user_id: int, day: date, now: datetime, rules: DayRules
) -> int:
    existing = conn.execute(
        "SELECT id FROM reports WHERE user_id = ? AND day = ?", (user_id, day.isoformat())
    ).fetchone()
    if existing is not None:
        return existing["id"]
    if day > logical_day(now, rules):
        raise FutureDay("cannot open a report for a future day")
    deadline = edit_deadline(day, rules)
    if now >= deadline:
        raise ReportClosed(f"the edit window for {day.isoformat()} has ended")
    require_open_time(conn, day, now)
    with conn:
        cursor = conn.execute(
            "INSERT INTO reports (user_id, day, status, editable_until) "
            "VALUES (?, ?, 'open', ?)",
            (user_id, day.isoformat(), _iso(deadline)),
        )
        report_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO completions "
            "(report_id, activity_id, name_at_time, weight_at_time, area_id, target_at_time) "
            "SELECT ?, id, name, weight, area_id, times_per_week FROM activities "
            "WHERE archived_at IS NULL AND (days & ?) != 0",
            (report_id, 1 << day.weekday()),
        )
    return report_id


def set_done(
    conn: sqlite3.Connection, report_id: int, activity_id: int, done: bool, now: datetime
) -> None:
    _require_editable(conn, report_id, now)
    with conn:
        cursor = conn.execute(
            "UPDATE completions SET done = ? WHERE report_id = ? AND activity_id = ?",
            (int(done), report_id, activity_id),
        )
        if cursor.rowcount == 0:
            raise NotInReport(f"activity {activity_id} is not part of report {report_id}")
        completed = conn.execute(
            "SELECT completed_at FROM reports WHERE id = ?", (report_id,)
        ).fetchone()["completed_at"]
        if completed is not None:
            _write_scores(conn, report_id)


def complete_report(conn: sqlite3.Connection, report_id: int, now: datetime) -> None:
    _require_editable(conn, report_id, now)
    with conn:
        conn.execute(
            "UPDATE reports SET completed_at = COALESCE(completed_at, ?) WHERE id = ?",
            (_iso(now), report_id),
        )
        _write_scores(conn, report_id)


def expire_reports(conn: sqlite3.Connection, now: datetime) -> list[dict]:
    expired = conn.execute(
        "SELECT id, day FROM reports WHERE status = 'open' AND editable_until <= ?",
        (_iso(now),),
    ).fetchall()
    with conn:
        conn.execute(
            "UPDATE reports SET status = 'closed' WHERE status = 'open' AND editable_until <= ?",
            (_iso(now),),
        )
    return [{"report_id": row["id"], "day": row["day"]} for row in expired]


def close_expired(conn: sqlite3.Connection, now: datetime) -> int:
    return len(expire_reports(conn, now))


def scores_for_day(conn: sqlite3.Connection, user_id: int, day: date) -> list[dict]:
    rows = conn.execute(
        "SELECT a.slug, s.maximum, s.obtained "
        "FROM reports r "
        "JOIN daily_scores s ON s.report_id = r.id "
        "JOIN areas a ON a.id = s.area_id "
        "WHERE r.user_id = ? AND r.day = ? AND r.completed_at IS NOT NULL "
        "ORDER BY a.position",
        (user_id, day.isoformat()),
    ).fetchall()
    return [
        {
            "area": row["slug"],
            "maximum": row["maximum"],
            "obtained": row["obtained"],
            "score": score(row["maximum"], row["obtained"]),
        }
        for row in rows
    ]


def _effective_status(row, now: datetime) -> str:
    if row["status"] == "closed" or now >= datetime.fromisoformat(row["editable_until"]):
        return "closed"
    return "open"


def _score_entry(row) -> dict:
    return {
        "area": row["slug"],
        "maximum": row["maximum"],
        "obtained": row["obtained"],
        "score": score(row["maximum"], row["obtained"]),
    }


def report_id_for_day(conn: sqlite3.Connection, user_id: int, day: date) -> int | None:
    row = conn.execute(
        "SELECT id FROM reports WHERE user_id = ? AND day = ?", (user_id, day.isoformat())
    ).fetchone()
    return None if row is None else row["id"]


def report_detail(conn: sqlite3.Connection, report_id: int, now: datetime) -> dict:
    row = conn.execute(
        "SELECT id, day, status, completed_at, editable_until, reflection "
        "FROM reports WHERE id = ?",
        (report_id,),
    ).fetchone()
    if row is None:
        raise ReportNotFound(f"report {report_id} not found")
    completions = conn.execute(
        "SELECT c.activity_id, c.name_at_time, c.weight_at_time, c.done, c.target_at_time, a.slug, "
        "act.description "
        "FROM completions c JOIN areas a ON a.id = c.area_id "
        "JOIN activities act ON act.id = c.activity_id "
        "WHERE c.report_id = ? ORDER BY a.position, c.id",
        (report_id,),
    ).fetchall()
    scores = None
    if row["completed_at"] is not None:
        scores = [
            _score_entry(r)
            for r in conn.execute(
                "SELECT a.slug, s.maximum, s.obtained FROM daily_scores s "
                "JOIN areas a ON a.id = s.area_id WHERE s.report_id = ? ORDER BY a.position",
                (report_id,),
            )
        ]
    status = _effective_status(row, now)
    return {
        "day": row["day"],
        "status": status,
        "editable": status == "open",
        "completed": row["completed_at"] is not None,
        "completed_at": row["completed_at"],
        "editable_until": row["editable_until"],
        "reflection": row["reflection"],
        "completions": [
            {
                "activity_id": c["activity_id"],
                "name": c["name_at_time"],
                "description": c["description"],
                "weight": c["weight_at_time"],
                "area": c["slug"],
                "done": bool(c["done"]),
                "weekly": None
                if c["target_at_time"] is None
                else weekly_progress(
                    conn, c["activity_id"], c["target_at_time"], date.fromisoformat(row["day"])
                ),
            }
            for c in completions
        ],
        "scores": scores,
        "overall": None if scores is None else mean_score(s["score"] for s in scores),
    }


def list_reports(
    conn: sqlite3.Connection, user_id: int, start: date, end: date, now: datetime
) -> list[dict]:
    rows = conn.execute(
        "SELECT day, status, completed_at, editable_until FROM reports "
        "WHERE user_id = ? AND day BETWEEN ? AND ? ORDER BY day DESC",
        (user_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    return [
        {
            "day": r["day"],
            "status": _effective_status(r, now),
            "completed": r["completed_at"] is not None,
            "completed_at": r["completed_at"],
            "editable_until": r["editable_until"],
        }
        for r in rows
    ]


def scores_range(conn: sqlite3.Connection, user_id: int, start: date, end: date) -> list[dict]:
    rows = conn.execute(
        "SELECT r.day, a.slug, s.maximum, s.obtained "
        "FROM reports r "
        "JOIN daily_scores s ON s.report_id = r.id "
        "JOIN areas a ON a.id = s.area_id "
        "WHERE r.user_id = ? AND r.day BETWEEN ? AND ? AND r.completed_at IS NOT NULL "
        "ORDER BY r.day, a.position",
        (user_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    days: dict[str, list[dict]] = {}
    for row in rows:
        days.setdefault(row["day"], []).append(_score_entry(row))
    return [
        {"day": day, "areas": areas, "overall": mean_score(a["score"] for a in areas)}
        for day, areas in days.items()
    ]


def set_reflection(
    conn: sqlite3.Connection, report_id: int, text: str | None, now: datetime
) -> None:
    _require_editable(conn, report_id, now)
    with conn:
        conn.execute("UPDATE reports SET reflection = ? WHERE id = ?", (text, report_id))


def sync_draft(conn: sqlite3.Connection, report_id: int, now: datetime) -> None:
    _require_editable(conn, report_id, now)
    completed = conn.execute(
        "SELECT completed_at FROM reports WHERE id = ?", (report_id,)
    ).fetchone()["completed_at"]
    day = date.fromisoformat(
        conn.execute("SELECT day FROM reports WHERE id = ?", (report_id,)).fetchone()["day"]
    )
    bit = 1 << day.weekday()
    with conn:
        conn.execute(
            "DELETE FROM completions WHERE report_id = ? AND activity_id IN "
            "(SELECT id FROM activities WHERE archived_at IS NOT NULL OR (days & ?) = 0)",
            (report_id, bit),
        )
        conn.execute(
            "UPDATE completions SET "
            "name_at_time = (SELECT name FROM activities WHERE id = completions.activity_id), "
            "weight_at_time = (SELECT weight FROM activities WHERE id = completions.activity_id), "
            "target_at_time = (SELECT times_per_week FROM activities WHERE id = completions.activity_id), "
            "area_id = (SELECT area_id FROM activities WHERE id = completions.activity_id) "
            "WHERE report_id = ?",
            (report_id,),
        )
        conn.execute(
            "INSERT INTO completions "
            "(report_id, activity_id, name_at_time, weight_at_time, area_id, target_at_time) "
            "SELECT ?, id, name, weight, area_id, times_per_week FROM activities "
            "WHERE archived_at IS NULL AND (days & ?) != 0 AND id NOT IN "
            "(SELECT activity_id FROM completions WHERE report_id = ?)",
            (report_id, bit, report_id),
        )
        if completed is not None:
            _write_scores(conn, report_id)


def area_averages(conn: sqlite3.Connection, user_id: int, start: date, end: date) -> dict:
    per_area: dict[str, list[float | None]] = {
        row["slug"]: [] for row in conn.execute("SELECT slug FROM areas ORDER BY position")
    }
    filled_days: set[str] = set()
    rows = conn.execute(
        "SELECT r.day, a.slug, s.maximum, s.obtained "
        "FROM reports r "
        "JOIN daily_scores s ON s.report_id = r.id "
        "JOIN areas a ON a.id = s.area_id "
        "WHERE r.user_id = ? AND r.day BETWEEN ? AND ? AND r.completed_at IS NOT NULL",
        (user_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    for row in rows:
        filled_days.add(row["day"])
        per_area[row["slug"]].append(score(row["maximum"], row["obtained"]))
    return {
        "filled_days": len(filled_days),
        "areas": [{"area": slug, "average": mean_score(v)} for slug, v in per_area.items()],
    }


def activity_stats(conn: sqlite3.Connection, user_id: int, start: date, end: date) -> list[dict]:
    rows = conn.execute(
        "SELECT c.activity_id, c.name_at_time, c.weight_at_time, c.done, a.slug, a.position, "
        "act.archived_at "
        "FROM completions c "
        "JOIN reports r ON r.id = c.report_id "
        "JOIN areas a ON a.id = c.area_id "
        "JOIN activities act ON act.id = c.activity_id "
        "WHERE r.user_id = ? AND r.day BETWEEN ? AND ? AND r.completed_at IS NOT NULL "
        "ORDER BY r.day, c.id",
        (user_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    stats: dict[int, dict] = {}
    positions: dict[int, int] = {}
    for row in rows:
        entry = stats.setdefault(row["activity_id"], {"activity_id": row["activity_id"], "done": 0, "total": 0})
        entry.update(
            name=row["name_at_time"],
            weight=row["weight_at_time"],
            area=row["slug"],
            archived=row["archived_at"] is not None,
        )
        entry["done"] += row["done"]
        entry["total"] += 1
        positions[row["activity_id"]] = row["position"]
    return sorted(stats.values(), key=lambda e: (positions[e["activity_id"]], e["activity_id"]))
