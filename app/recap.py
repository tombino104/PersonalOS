import calendar
import sqlite3
from datetime import date, timedelta

from . import reports
from .scoring import mean_score

MIN_HABIT_DAYS = 3
TOP_HABITS = 3
SAMPLE_LINES = 5


class InvalidPeriod(ValueError):
    pass


class FuturePeriod(ValueError):
    pass


def parse_period(period: str) -> tuple[str, date, date]:
    try:
        if len(period) == 7 and period[4] == "-" and period[:4].isdigit() and period[5:].isdigit():
            year, month = int(period[:4]), int(period[5:])
            start = date(year, month, 1)
            return "month", start, date(year, month, calendar.monthrange(year, month)[1])
        if len(period) == 4 and period.isdigit():
            year = int(period)
            return "year", date(year, 1, 1), date(year, 12, 31)
    except ValueError:
        pass
    raise InvalidPeriod("a period is YYYY-MM or YYYY")


def previous_range(kind: str, start: date) -> tuple[date, date]:
    end = start - timedelta(days=1)
    if kind == "year":
        return date(end.year, 1, 1), end
    return date(end.year, end.month, 1), end


def _days(start: date, end: date) -> int:
    return (end - start).days + 1


def _weeks(start: date, last: date, completed: set[str]) -> list[dict]:
    weeks = []
    monday = start - timedelta(days=start.weekday())
    while monday <= last:
        first = max(monday, start)
        final = min(monday + timedelta(days=6), last)
        filled = sum(
            1 for offset in range(_days(first, final)) if (first + timedelta(days=offset)).isoformat() in completed
        )
        weeks.append({"week_start": monday.isoformat(), "filled": filled, "possible": _days(first, final)})
        monday += timedelta(days=7)
    return weeks


def _best_week(weeks: list[dict]) -> dict | None:
    candidates = [week for week in weeks if week["filled"] > 0]
    if len(weeks) < 2 or not candidates:
        return None
    return max(candidates, key=lambda week: (week["filled"], week["week_start"]))


def _top_habits(stats: list[dict]) -> list[dict]:
    eligible = [item for item in stats if item["total"] >= MIN_HABIT_DAYS and item["done"] > 0]
    eligible.sort(key=lambda item: (-item["done"] / item["total"], -item["done"], item["activity_id"]))
    return [
        {key: item[key] for key in ("activity_id", "name", "area", "done", "total")}
        for item in eligible[:TOP_HABITS]
    ]


def summary(conn: sqlite3.Connection, user_id: int, period: str, today: date) -> dict:
    kind, start, end = parse_period(period)
    if start > today:
        raise FuturePeriod("that period has not started yet")
    last = min(end, today)
    before_start, before_end = previous_range(kind, start)

    rows = conn.execute(
        "SELECT day, reflection FROM reports "
        "WHERE user_id = ? AND day BETWEEN ? AND ? AND completed_at IS NOT NULL ORDER BY day",
        (user_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    completed = {row["day"] for row in rows}
    lines = [{"day": row["day"], "text": row["reflection"]} for row in rows if (row["reflection"] or "").strip()]

    scored = reports.scores_range(conn, user_id, start, end)
    overall = mean_score(item["overall"] for item in scored)
    before_scored = reports.scores_range(conn, user_id, before_start, before_end)
    before_overall = mean_score(item["overall"] for item in before_scored)

    current = reports.area_averages(conn, user_id, start, end)
    before = reports.area_averages(conn, user_id, before_start, before_end)
    previous = {item["area"]: item["average"] for item in before["areas"]}

    result = {
        "period": period,
        "kind": kind,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "is_current": start <= today <= end,
        "elapsed_days": _days(start, last),
        "filled_days": len(completed),
        "previous_filled_days": before["filled_days"],
        "previous_days": _days(before_start, before_end),
        "overall": overall,
        "previous_overall": before_overall,
        "areas": [
            {"area": item["area"], "average": item["average"], "previous": previous[item["area"]]}
            for item in current["areas"]
        ],
        "top_habits": _top_habits(reports.activity_stats(conn, user_id, start, end)),
        "best_week": _best_week(_weeks(start, last, completed)),
        "line_count": len(lines),
    }
    if kind == "month":
        overall_by_day = {item["day"]: item["overall"] for item in scored}
        result["days"] = [
            {
                "day": (start + timedelta(days=offset)).isoformat(),
                "completed": (start + timedelta(days=offset)).isoformat() in completed,
                "overall": overall_by_day.get((start + timedelta(days=offset)).isoformat()),
            }
            for offset in range(_days(start, end))
        ]
        result["lines"] = lines[-SAMPLE_LINES:][::-1]
    else:
        months = []
        for number in range(1, 13):
            first = date(start.year, number, 1)
            if first > today:
                break
            final = min(date(start.year, number, calendar.monthrange(start.year, number)[1]), today)
            prefix = first.isoformat()[:7]
            months.append(
                {
                    "month": prefix,
                    "filled": sum(1 for day in completed if day.startswith(prefix)),
                    "possible": _days(first, final),
                }
            )
        result["months"] = months
        result["lines"] = []
    return result
