import math
from datetime import date, timedelta

from fastapi import HTTPException, Query

MAX_STEPS = 200000
MAX_SAMPLES = 20000
MAX_DAYS = 400
METRIC = "step_count"


def _day(value, today: date) -> date:
    if not isinstance(value, str):
        raise ValueError("a day must be text like 2026-10-27")
    try:
        day = date.fromisoformat(value[:10])
    except ValueError:
        raise ValueError(f"not a valid day: {value[:30]}") from None
    if not 1970 <= day.year <= 2100 or day > today + timedelta(days=1):
        raise ValueError(f"day out of range: {day.isoformat()}")
    return day


def _count(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("steps must be a number")
    if not 0 <= value <= MAX_STEPS:
        raise ValueError("steps out of range")
    return float(value)


def _from_export(data, today: date) -> dict:
    metrics = data.get("metrics") if isinstance(data, dict) else None
    if not isinstance(metrics, list):
        raise ValueError("expected data.metrics to be a list")
    totals: dict = {}
    seen = 0
    for metric in metrics:
        if not isinstance(metric, dict) or metric.get("name") != METRIC:
            continue
        samples = metric.get("data")
        if not isinstance(samples, list):
            raise ValueError("expected the step samples to be a list")
        for sample in samples:
            seen += 1
            if seen > MAX_SAMPLES:
                raise ValueError("too many samples")
            if not isinstance(sample, dict):
                raise ValueError("each sample must be an object")
            day = _day(sample.get("date"), today)
            totals[day] = totals.get(day, 0.0) + _count(sample.get("qty"))
    return totals


def _from_days(items, today: date) -> dict:
    if not isinstance(items, list) or len(items) > MAX_DAYS:
        raise ValueError(f"'days' must be a list of at most {MAX_DAYS} items")
    totals: dict = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each day must be an object")
        day = _day(item.get("day"), today)
        totals[day] = max(totals.get(day, 0.0), _count(item.get("steps")))
    return totals


def collect(payload, today: date) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("the payload must be an object")
    if "data" in payload:
        totals = _from_export(payload["data"], today)
    elif "days" in payload:
        totals = _from_days(payload["days"], today)
    elif "steps" in payload:
        totals = _from_days([{"day": payload.get("day", today.isoformat()), "steps": payload["steps"]}], today)
    else:
        raise ValueError("expected 'steps', 'days' or an export with data.metrics")
    totals = {day: round(steps) for day, steps in totals.items()}
    if not totals:
        raise ValueError("no step data found")
    if any(steps > MAX_STEPS for steps in totals.values()):
        raise ValueError("steps out of range")
    return totals


def setup(api):
    @api.ingest
    def receive(ctx, payload):
        totals = collect(payload, date.fromisoformat(ctx.today))
        moment = ctx.now.isoformat(timespec="seconds")
        with ctx.transaction():
            for day, steps in sorted(totals.items()):
                ctx.db.execute(
                    "INSERT INTO plg_health_days (day, steps, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT (day) DO UPDATE SET "
                    "updated_at = CASE WHEN excluded.steps > steps THEN excluded.updated_at ELSE updated_at END, "
                    "steps = MAX(steps, excluded.steps)",
                    (day.isoformat(), steps, moment),
                )

    @api.router.get("/days")
    def list_days(
        start: date | None = None,
        end: date | None = None,
        limit: int = Query(60, ge=1, le=MAX_DAYS),
        ctx=api.ctx,
    ):
        where = []
        params: list = []
        if start is not None:
            where.append("day >= ?")
            params.append(start.isoformat())
        if end is not None:
            where.append("day <= ?")
            params.append(end.isoformat())
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        rows = ctx.db.execute(
            f"SELECT day, steps FROM plg_health_days{clause} ORDER BY day DESC LIMIT ?", [*params, limit]
        ).fetchall()
        return {"days": [{"day": row["day"], "steps": row["steps"]} for row in rows]}

    @api.router.delete("/days/{day}")
    def delete_day(day: date, ctx=api.ctx):
        cursor = ctx.db.execute("DELETE FROM plg_health_days WHERE day = ?", (day.isoformat(),))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="no steps for this day")
        return {"ok": True}
