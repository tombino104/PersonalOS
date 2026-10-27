from datetime import date, timedelta

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

LEVELS = (1, 2, 3, 4, 5)
RECENT_NOTES = 5
DAY_WEIGHT = 2
JOURNAL_WEIGHT = 1


class Entry(BaseModel):
    value: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=300)


def _valid_day(value) -> bool:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def _valid_journal_mood(item) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("entry_id"), int)
        and _valid_day(item.get("day"))
        and isinstance(item.get("mood"), int)
        and 1 <= item["mood"] <= 5
    )


def blend(day_value: int | None, journal_values: list[int]) -> float | None:
    parts = []
    if day_value is not None:
        parts.append((DAY_WEIGHT, day_value))
    if journal_values:
        parts.append((JOURNAL_WEIGHT, sum(journal_values) / len(journal_values)))
    if not parts:
        return None
    return round(sum(weight * value for weight, value in parts) / sum(weight for weight, _ in parts), 2)


def setup(api):
    @api.on("journal.mood_set")
    def on_journal_mood(ctx, payload):
        entry_id = payload.get("entry_id")
        if not isinstance(entry_id, int):
            return
        if payload.get("mood") is None:
            ctx.db.execute("DELETE FROM plg_mood_journal WHERE entry_id = ?", (entry_id,))
        elif _valid_journal_mood(payload):
            ctx.db.execute(
                "INSERT INTO plg_mood_journal (entry_id, day, value) VALUES (?, ?, ?) "
                "ON CONFLICT (entry_id) DO UPDATE SET day = excluded.day, value = excluded.value",
                (entry_id, payload["day"], payload["mood"]),
            )

    @api.on("journal.mood_snapshot")
    def on_journal_snapshot(ctx, payload):
        moods = [item for item in payload.get("moods", []) if _valid_journal_mood(item)]
        with ctx.transaction():
            ctx.db.execute("DELETE FROM plg_mood_journal")
            ctx.db.executemany(
                "INSERT INTO plg_mood_journal (entry_id, day, value) VALUES (?, ?, ?)",
                [(item["entry_id"], item["day"], item["mood"]) for item in moods],
            )

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
        journal: dict[str, list[int]] = {}
        for row in ctx.db.execute(
            "SELECT day, value FROM plg_mood_journal WHERE day BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat()),
        ):
            journal.setdefault(row["day"], []).append(row["value"])
        own = {row["day"]: row["value"] for row in rows if row["value"] is not None}
        entries = []
        for day in sorted(set(own) | set(journal)):
            value = blend(own.get(day), journal.get(day, []))
            entries.append({"day": day, "value": value, "journal_entries": len(journal.get(day, []))})
        counts = {level: 0 for level in LEVELS}
        for entry in entries:
            counts[int(entry["value"] + 0.5)] += 1
        notes = [{"day": row["day"], "note": row["note"]} for row in rows if row["note"]]
        return {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "days": days,
            "entries": entries,
            "distribution": [counts[level] for level in LEVELS],
            "notes": list(reversed(notes))[:RECENT_NOTES],
        }
