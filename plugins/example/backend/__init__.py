from datetime import date

from fastapi import HTTPException
from pydantic import BaseModel, Field


class Note(BaseModel):
    text: str | None = Field(default=None, max_length=300)


def setup(api):
    def report_id_for(ctx, day: date) -> int:
        report_id = ctx.report_id(day.isoformat())
        if report_id is None:
            raise HTTPException(status_code=404, detail="no report for that day")
        return report_id

    @api.router.get("/notes/{day}")
    def get_note(day: date, ctx=api.ctx):
        row = ctx.db.execute(
            "SELECT text FROM plg_example_notes WHERE report_id = ?", (report_id_for(ctx, day),)
        ).fetchone()
        return {"text": row["text"] if row else None}

    @api.router.put("/notes/{day}")
    def put_note(day: date, body: Note, ctx=api.ctx):
        report_id = report_id_for(ctx, day)
        text = (body.text or "").strip()
        if text:
            ctx.db.execute(
                "INSERT OR REPLACE INTO plg_example_notes (report_id, text) VALUES (?, ?)",
                (report_id, text),
            )
        else:
            ctx.db.execute("DELETE FROM plg_example_notes WHERE report_id = ?", (report_id,))
        return {"text": text or None}
