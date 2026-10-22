import sqlite3
from datetime import date, datetime, timedelta, timezone

from . import reports


class InvalidWeek(ValueError):
    pass


class FutureWeek(ValueError):
    pass


def check_week(week_start: date, today: date) -> None:
    if week_start.weekday() != 0:
        raise InvalidWeek("a week starts on a Monday")
    if week_start > today:
        raise FutureWeek("that week has not started yet")


def summary(conn: sqlite3.Connection, user_id: int, week_start: date, today: date) -> dict:
    check_week(week_start, today)
    week_end = week_start + timedelta(days=6)
    previous_start = week_start - timedelta(days=7)
    rows = conn.execute(
        "SELECT day, completed_at, reflection FROM reports WHERE user_id = ? AND day BETWEEN ? AND ?",
        (user_id, week_start.isoformat(), week_end.isoformat()),
    ).fetchall()
    known = {row["day"]: row for row in rows}
    overall = {
        item["day"]: item["overall"]
        for item in reports.scores_range(conn, user_id, week_start, week_end)
    }
    days = []
    for offset in range(7):
        day = (week_start + timedelta(days=offset)).isoformat()
        row = known.get(day)
        completed = row is not None and row["completed_at"] is not None
        days.append(
            {
                "day": day,
                "completed": completed,
                "overall": overall.get(day),
                "reflection": row["reflection"] if completed else None,
            }
        )
    current = reports.area_averages(conn, user_id, week_start, week_end)
    before = reports.area_averages(conn, user_id, previous_start, week_start - timedelta(days=1))
    previous = {item["area"]: item["average"] for item in before["areas"]}
    note = conn.execute(
        "SELECT note FROM weekly_reviews WHERE week_start = ?", (week_start.isoformat(),)
    ).fetchone()
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "is_current": week_start <= today <= week_end,
        "filled_days": current["filled_days"],
        "previous_filled_days": before["filled_days"],
        "days": days,
        "areas": [
            {"area": item["area"], "average": item["average"], "previous": previous[item["area"]]}
            for item in current["areas"]
        ],
        "activities": reports.activity_stats(conn, user_id, week_start, week_end),
        "note": None if note is None else note["note"],
    }


def save_note(
    conn: sqlite3.Connection, week_start: date, today: date, text: str | None, now: datetime
) -> str | None:
    check_week(week_start, today)
    text = (text or "").strip() or None
    with conn:
        if text is None:
            conn.execute("DELETE FROM weekly_reviews WHERE week_start = ?", (week_start.isoformat(),))
        else:
            conn.execute(
                "INSERT INTO weekly_reviews (week_start, note, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT (week_start) DO UPDATE SET note = excluded.note, updated_at = excluded.updated_at",
                (week_start.isoformat(), text, now.astimezone(timezone.utc).isoformat(timespec="seconds")),
            )
    return text
