from datetime import date

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field, field_validator

MAX_ENTRIES = 20000
MAX_BODY = 20000
COLUMNS = "id, day, title, body, created_at, updated_at"


class EntryBody(BaseModel):
    day: date | None = None
    title: str | None = Field(default=None, max_length=120)
    body: str = Field(max_length=MAX_BODY)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        return (value or "").strip() or None

    @field_validator("body")
    @classmethod
    def clean_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("the entry cannot be empty")
        return value

    @field_validator("day")
    @classmethod
    def sane_year(cls, value: date | None) -> date | None:
        if value is not None and not 1970 <= value.year <= 2100:
            raise ValueError("the year must be between 1970 and 2100")
        return value


def _public(row) -> dict:
    return {
        "id": row["id"],
        "day": row["day"],
        "title": row["title"],
        "body": row["body"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def setup(api):
    def entry_or_404(ctx, entry_id: int):
        row = ctx.db.execute(
            f"SELECT {COLUMNS} FROM plg_journal_entries WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="entry not found")
        return row

    @api.router.get("/entries")
    def list_entries(
        q: str | None = Query(None, max_length=100),
        start: date | None = None,
        end: date | None = None,
        limit: int = Query(30, ge=1, le=100),
        offset: int = Query(0, ge=0),
        ctx=api.ctx,
    ):
        where = []
        params: list = []
        text = (q or "").strip()
        if text:
            where.append("(body LIKE ? ESCAPE '\\' OR title LIKE ? ESCAPE '\\')")
            params += [_like(text), _like(text)]
        if start is not None:
            where.append("day >= ?")
            params.append(start.isoformat())
        if end is not None:
            where.append("day <= ?")
            params.append(end.isoformat())
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        total = ctx.db.execute(f"SELECT COUNT(*) FROM plg_journal_entries{clause}", params).fetchone()[0]
        rows = ctx.db.execute(
            f"SELECT {COLUMNS} FROM plg_journal_entries{clause} ORDER BY day DESC, id DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return {"entries": [_public(row) for row in rows], "total": total}

    @api.router.get("/entries/{entry_id}")
    def get_entry(entry_id: int, ctx=api.ctx):
        return _public(entry_or_404(ctx, entry_id))

    @api.router.post("/entries", status_code=201)
    def create_entry(body: EntryBody, ctx=api.ctx):
        today = date.fromisoformat(ctx.today)
        day = body.day or today
        if day > today:
            raise HTTPException(status_code=422, detail="an entry cannot be dated in the future")
        count = ctx.db.execute("SELECT COUNT(*) FROM plg_journal_entries").fetchone()[0]
        if count >= MAX_ENTRIES:
            raise HTTPException(status_code=409, detail="too many entries")
        moment = ctx.now.isoformat(timespec="seconds")
        cursor = ctx.db.execute(
            "INSERT INTO plg_journal_entries (day, title, body, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (day.isoformat(), body.title, body.body, moment, moment),
        )
        return _public(entry_or_404(ctx, cursor.lastrowid))

    @api.router.put("/entries/{entry_id}")
    def update_entry(entry_id: int, body: EntryBody, ctx=api.ctx):
        current = entry_or_404(ctx, entry_id)
        day = body.day.isoformat() if body.day else current["day"]
        if date.fromisoformat(day) > date.fromisoformat(ctx.today):
            raise HTTPException(status_code=422, detail="an entry cannot be dated in the future")
        ctx.db.execute(
            "UPDATE plg_journal_entries SET day = ?, title = ?, body = ?, updated_at = ? WHERE id = ?",
            (day, body.title, body.body, ctx.now.isoformat(timespec="seconds"), entry_id),
        )
        return _public(entry_or_404(ctx, entry_id))

    @api.router.delete("/entries/{entry_id}")
    def delete_entry(entry_id: int, ctx=api.ctx):
        entry_or_404(ctx, entry_id)
        ctx.db.execute("DELETE FROM plg_journal_entries WHERE id = ?", (entry_id,))
        return {"ok": True}
