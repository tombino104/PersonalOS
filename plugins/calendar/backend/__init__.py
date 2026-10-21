import re
from datetime import date
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from .recurrence import occurrences

MAX_RANGE_DAYS = 100
MAX_EVENTS = 5000
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
COLUMNS = "id, title, day, time, category, notes, repeat, until"


class EventBody(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    day: date
    time: str | None = None
    category: Literal["personal", "work", "study", "health", "social", "other"] = "personal"
    notes: str | None = Field(default=None, max_length=500)
    repeat: Literal["none", "daily", "weekly", "monthly", "yearly"] = "none"
    until: date | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("the title cannot be empty")
        return value

    @field_validator("time")
    @classmethod
    def valid_time(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        if not TIME.match(value):
            raise ValueError("the time must look like 18:30")
        return value

    @field_validator("day", "until")
    @classmethod
    def sane_year(cls, value: date | None) -> date | None:
        if value is not None and not 1970 <= value.year <= 2100:
            raise ValueError("the year must be between 1970 and 2100")
        return value


def _public(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "day": row["day"],
        "time": row["time"],
        "category": row["category"],
        "notes": row["notes"],
        "repeat": row["repeat"],
        "until": row["until"],
    }


def _values(body: EventBody) -> tuple:
    if body.until is not None and (body.repeat == "none" or body.until < body.day):
        raise HTTPException(status_code=422, detail="'until' needs a repeat and cannot be before the day")
    notes = (body.notes or "").strip() or None
    return (
        body.title,
        body.day.isoformat(),
        body.time,
        body.category,
        notes,
        body.repeat,
        body.until.isoformat() if body.until else None,
    )


def setup(api):
    @api.router.get("/events")
    def list_events(start: date, end: date, ctx=api.ctx):
        if end < start or (end - start).days >= MAX_RANGE_DAYS:
            raise HTTPException(status_code=422, detail=f"the range must be 1 to {MAX_RANGE_DAYS} days")
        rows = ctx.db.execute(
            f"SELECT {COLUMNS} FROM plg_calendar_events "
            "WHERE day <= ? AND (until IS NULL OR until >= ?)",
            (end.isoformat(), start.isoformat()),
        ).fetchall()
        found = []
        for row in rows:
            until = date.fromisoformat(row["until"]) if row["until"] else None
            for day in occurrences(date.fromisoformat(row["day"]), row["repeat"], until, start, end):
                item = _public(row)
                item["event_id"] = item.pop("id")
                item["day"] = day.isoformat()
                found.append(item)
        found.sort(key=lambda item: (item["day"], item["time"] or "", item["title"].lower()))
        return {"start": start.isoformat(), "end": end.isoformat(), "occurrences": found}

    @api.router.get("/events/{event_id}")
    def get_event(event_id: int, ctx=api.ctx):
        row = ctx.db.execute(
            f"SELECT {COLUMNS} FROM plg_calendar_events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="event not found")
        return _public(row)

    @api.router.post("/events", status_code=201)
    def create_event(body: EventBody, ctx=api.ctx):
        count = ctx.db.execute("SELECT COUNT(*) FROM plg_calendar_events").fetchone()[0]
        if count >= MAX_EVENTS:
            raise HTTPException(status_code=409, detail="too many events")
        moment = ctx.now.isoformat(timespec="seconds")
        cursor = ctx.db.execute(
            "INSERT INTO plg_calendar_events "
            "(title, day, time, category, notes, repeat, until, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*_values(body), moment, moment),
        )
        row = ctx.db.execute(
            f"SELECT {COLUMNS} FROM plg_calendar_events WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _public(row)

    @api.router.put("/events/{event_id}")
    def update_event(event_id: int, body: EventBody, ctx=api.ctx):
        values = _values(body)
        cursor = ctx.db.execute(
            "UPDATE plg_calendar_events SET title = ?, day = ?, time = ?, category = ?, "
            "notes = ?, repeat = ?, until = ?, updated_at = ? WHERE id = ?",
            (*values, ctx.now.isoformat(timespec="seconds"), event_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="event not found")
        row = ctx.db.execute(
            f"SELECT {COLUMNS} FROM plg_calendar_events WHERE id = ?", (event_id,)
        ).fetchone()
        return _public(row)

    @api.router.delete("/events/{event_id}")
    def delete_event(event_id: int, ctx=api.ctx):
        cursor = ctx.db.execute("DELETE FROM plg_calendar_events WHERE id = ?", (event_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="event not found")
        return {"ok": True}
