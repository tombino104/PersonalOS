import calendar
from datetime import date, timedelta


def _clamped(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def occurrences(first: date, repeat: str, until: date | None, start: date, end: date) -> list[date]:
    last = min(end, until) if until else end
    if last < start or last < first:
        return []
    if repeat == "none":
        return [first] if start <= first <= last else []
    if repeat in ("daily", "weekly"):
        step = 1 if repeat == "daily" else 7
        skipped = max((start - first).days, 0)
        current = first + timedelta(days=-(-skipped // step) * step)
        days = []
        while current <= last:
            days.append(current)
            current += timedelta(days=step)
        return days
    earliest = max(first, start)
    year, month = earliest.year, earliest.month
    if repeat == "yearly":
        month = first.month
    days = []
    while True:
        current = _clamped(year, month, first.day)
        if current > last:
            return days
        if current >= earliest:
            days.append(current)
        if repeat == "yearly":
            year += 1
        else:
            month += 1
            if month > 12:
                month, year = 1, year + 1
