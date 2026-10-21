from datetime import date, timedelta

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

LEVELS = (1, 2, 3, 4, 5)
RECENT_NOTES = 5


class Entry(BaseModel):
    value: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=300)


def setup(api):
    @api.router.get("/entries/{day}")
    def get_entry(day: date, ctx=api.ctx):
        row = ctx.db.execute(
            "SELECT value, note FROM plg_mood_entries WHERE day = ?", (day.isoformat(),)
        ).fetchone()
        return {"value": row["value"] if row else None, "note": row["note"] if row else None}

    @api.router.put("/entries/{day}")
    def put_entry(day: date, body: Entry, ctx=api.ctx):
        report_id = ctx.report_id(day.isoformat())
        if report_id is None:
            raise HTTPException(status_code=404, detail="no report for that day")
        note = (body.note or "").strip() or None
        if body.value is None and note is None:
            ctx.db.execute("DELETE FROM plg_mood_entries WHERE report_id = ?", (report_id,))
        else:
            ctx.db.execute(
                "INSERT INTO plg_mood_entries (report_id, day, value, note, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT (report_id) DO UPDATE SET "
                "value = excluded.value, note = excluded.note, updated_at = excluded.updated_at",
                (report_id, day.isoformat(), body.value, note, ctx.now.isoformat(timespec="seconds")),
            )
        return {"value": body.value, "note": note}

    @api.router.get("/summary")
    def summary(days: int = Query(30, ge=7, le=366), ctx=api.ctx):
        end = date.fromisoformat(ctx.today)
        start = end - timedelta(days=days - 1)
        rows = ctx.db.execute(
            "SELECT day, value, note FROM plg_mood_entries WHERE day BETWEEN ? AND ? ORDER BY day",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        counts = {level: 0 for level in LEVELS}
        for row in rows:
            if row["value"] is not None:
                counts[row["value"]] += 1
        notes = [{"day": row["day"], "note": row["note"]} for row in rows if row["note"]]
        return {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "days": days,
            "entries": [{"day": row["day"], "value": row["value"]} for row in rows if row["value"] is not None],
            "distribution": [counts[level] for level in LEVELS],
            "notes": list(reversed(notes))[:RECENT_NOTES],
        }
