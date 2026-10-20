import sqlite3
from datetime import date, datetime, timezone

from .logical_day import DayRules, edit_deadline, logical_day
from .scoring import Item, score, tally


class ReportClosed(Exception):
    pass


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _require_editable(conn: sqlite3.Connection, report_id: int, now: datetime) -> None:
    row = conn.execute(
        "SELECT status, editable_until FROM reports WHERE id = ?", (report_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"report {report_id} not found")
    if row["status"] == "closed" or now >= datetime.fromisoformat(row["editable_until"]):
        raise ReportClosed(f"report {report_id} is closed")


def _write_scores(conn: sqlite3.Connection, report_id: int) -> None:
    per_area: dict[int, list[Item]] = {
        row["id"]: [] for row in conn.execute("SELECT id FROM areas")
    }
    for row in conn.execute(
        "SELECT area_id, weight_at_time, done FROM completions WHERE report_id = ?",
        (report_id,),
    ):
        per_area[row["area_id"]].append(Item(row["weight_at_time"], bool(row["done"])))
    conn.execute("DELETE FROM daily_scores WHERE report_id = ?", (report_id,))
    for area_id, items in per_area.items():
        maximum, obtained = tally(items)
        conn.execute(
            "INSERT INTO daily_scores (report_id, area_id, maximum, obtained) "
            "VALUES (?, ?, ?, ?)",
            (report_id, area_id, maximum, obtained),
        )


def open_report(
    conn: sqlite3.Connection, user_id: int, day: date, now: datetime, rules: DayRules
) -> int:
    existing = conn.execute(
        "SELECT id FROM reports WHERE user_id = ? AND day = ?", (user_id, day.isoformat())
    ).fetchone()
    if existing is not None:
        return existing["id"]
    if day > logical_day(now, rules):
        raise ValueError("cannot open a report for a future day")
    deadline = edit_deadline(day, rules)
    if now >= deadline:
        raise ReportClosed(f"the edit window for {day.isoformat()} has ended")
    with conn:
        cursor = conn.execute(
            "INSERT INTO reports (user_id, day, status, editable_until) "
            "VALUES (?, ?, 'open', ?)",
            (user_id, day.isoformat(), _iso(deadline)),
        )
        report_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO completions "
            "(report_id, activity_id, name_at_time, weight_at_time, area_id) "
            "SELECT ?, id, name, weight, area_id FROM activities WHERE archived_at IS NULL",
            (report_id,),
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
            raise KeyError(f"activity {activity_id} is not part of report {report_id}")
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


def close_expired(conn: sqlite3.Connection, now: datetime) -> int:
    with conn:
        cursor = conn.execute(
            "UPDATE reports SET status = 'closed' "
            "WHERE status = 'open' AND editable_until <= ?",
            (_iso(now),),
        )
    return cursor.rowcount


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
