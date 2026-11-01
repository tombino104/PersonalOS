import re
from datetime import date, timedelta

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field, field_validator

TIME = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
MAX_NIGHT_MINUTES = 960
DEFAULT_TARGET = 420
MIN_TARGET, MAX_TARGET = 240, 840


def to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def night_minutes(lights_off: str | None, woke_up: str | None) -> int | None:
    if lights_off is None or woke_up is None:
        return None
    start, end = to_minutes(lights_off), to_minutes(woke_up)
    return end - start if end > start else end - start + 1440


def _clean_time(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not TIME.match(value):
        raise ValueError("a time is HH:MM")
    return value


class NightBody(BaseModel):
    lights_off: str | None = None
    woke_up: str | None = None

    @field_validator("lights_off", "woke_up")
    @classmethod
    def valid_time(cls, value: str | None) -> str | None:
        return _clean_time(value)


class SettingsBody(BaseModel):
    target_minutes: int = Field(ge=MIN_TARGET, le=MAX_TARGET)


def _public(day: str, lights_off: str | None, woke_up: str | None) -> dict:
    return {
        "day": day,
        "lights_off": lights_off,
        "woke_up": woke_up,
        "minutes": night_minutes(lights_off, woke_up),
    }


def setup(api):
    def read_night(ctx, day: str) -> dict:
        row = ctx.db.execute("SELECT lights_off, woke_up FROM plg_sleep_nights WHERE day = ?", (day,)).fetchone()
        return _public(day, row["lights_off"] if row else None, row["woke_up"] if row else None)

    @api.router.get("/nights")
    def list_nights(
        start: date | None = None,
        end: date | None = None,
        limit: int = Query(60, ge=1, le=400),
        ctx=api.ctx,
    ):
        clauses, params = [], []
        if start is not None:
            clauses.append("day >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("day <= ?")
            params.append(end.isoformat())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = ctx.db.execute(
            f"SELECT day, lights_off, woke_up FROM plg_sleep_nights{where} ORDER BY day DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return {"nights": [_public(row["day"], row["lights_off"], row["woke_up"]) for row in rows]}

    @api.router.get("/nights/{day}")
    def get_night(day: date, ctx=api.ctx):
        return read_night(ctx, day.isoformat())

    @api.router.put("/nights/{day}")
    def put_night(day: date, body: NightBody, ctx=api.ctx):
        if day > date.fromisoformat(ctx.today) + timedelta(days=1):
            raise HTTPException(status_code=422, detail="that night has not happened yet")
        current = read_night(ctx, day.isoformat())
        lights_off = body.lights_off if "lights_off" in body.model_fields_set else current["lights_off"]
        woke_up = body.woke_up if "woke_up" in body.model_fields_set else current["woke_up"]
        length = night_minutes(lights_off, woke_up)
        if length is not None and length > MAX_NIGHT_MINUTES:
            raise HTTPException(status_code=422, detail="a night is at most 16 hours")
        if lights_off is None and woke_up is None:
            ctx.db.execute("DELETE FROM plg_sleep_nights WHERE day = ?", (day.isoformat(),))
        else:
            ctx.db.execute(
                "INSERT INTO plg_sleep_nights (day, lights_off, woke_up, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (day) DO UPDATE SET lights_off = excluded.lights_off, "
                "woke_up = excluded.woke_up, updated_at = excluded.updated_at",
                (day.isoformat(), lights_off, woke_up, ctx.now.isoformat(timespec="seconds")),
            )
        return _public(day.isoformat(), lights_off, woke_up)

    @api.router.delete("/nights/{day}")
    def delete_night(day: date, ctx=api.ctx):
        cursor = ctx.db.execute("DELETE FROM plg_sleep_nights WHERE day = ?", (day.isoformat(),))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="night not found")
        return {"ok": True}

    @api.router.get("/settings")
    def get_settings(ctx=api.ctx):
        row = ctx.db.execute("SELECT target_minutes FROM plg_sleep_settings WHERE id = 1").fetchone()
        return {"target_minutes": row["target_minutes"] if row else DEFAULT_TARGET}

    @api.router.put("/settings")
    def put_settings(body: SettingsBody, ctx=api.ctx):
        ctx.db.execute(
            "INSERT INTO plg_sleep_settings (id, target_minutes) VALUES (1, ?) "
            "ON CONFLICT (id) DO UPDATE SET target_minutes = excluded.target_minutes",
            (body.target_minutes,),
        )
        return {"target_minutes": body.target_minutes}
