import re
from datetime import date

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

MAX_PEOPLE = 500
BIRTHDAY = re.compile(r"^(?:(\d{4})-)?(\d{2})-(\d{2})$")
COLUMNS = "id, name, birth_month, birth_day, birth_year"


def parse_birthday(value: str | None) -> tuple[int | None, int | None, int | None]:
    if value is None:
        return None, None, None
    match = BIRTHDAY.match(value)
    if match is None:
        raise ValueError("a birthday is MM-DD or YYYY-MM-DD")
    year = int(match.group(1)) if match.group(1) else None
    month, day = int(match.group(2)), int(match.group(3))
    try:
        date(2000, month, day)
    except ValueError:
        raise ValueError("that day does not exist") from None
    if year is not None:
        if not 1900 <= year <= 2100:
            raise ValueError("the year must be between 1900 and 2100")
        try:
            date(year, month, day)
        except ValueError:
            raise ValueError("that day does not exist in that year") from None
    return year, month, day


def next_birthday(month: int, day: int, today: date) -> date:
    for year in (today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            candidate = date(year, 2, 28)
        if candidate >= today:
            return candidate
    raise AssertionError("unreachable")


class PersonBody(BaseModel):
    name: str = Field(max_length=100)
    birthday: str | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("the name cannot be empty")
        return value

    @field_validator("birthday")
    @classmethod
    def valid_birthday(cls, value: str | None) -> str | None:
        value = (value or "").strip() or None
        parse_birthday(value)
        return value


def _public(row, today: date) -> dict:
    person = {
        "id": row["id"],
        "name": row["name"],
        "birthday": None,
        "next_birthday": None,
        "days_until": None,
        "turning": None,
    }
    if row["birth_month"] is None:
        return person
    month, day, year = row["birth_month"], row["birth_day"], row["birth_year"]
    upcoming = next_birthday(month, day, today)
    person["birthday"] = f"{year:04d}-{month:02d}-{day:02d}" if year else f"{month:02d}-{day:02d}"
    person["next_birthday"] = upcoming.isoformat()
    person["days_until"] = (upcoming - today).days
    person["turning"] = upcoming.year - year if year else None
    return person


def setup(api):
    def person_or_404(ctx, person_id: int):
        row = ctx.db.execute(f"SELECT {COLUMNS} FROM plg_people_people WHERE id = ?", (person_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="person not found")
        return row

    @api.router.get("/people")
    def list_people(ctx=api.ctx):
        today = date.fromisoformat(ctx.today)
        rows = ctx.db.execute(f"SELECT {COLUMNS} FROM plg_people_people").fetchall()
        people = [_public(row, today) for row in rows]
        people.sort(key=lambda p: (p["days_until"] is None, p["days_until"] or 0, p["name"].lower()))
        return {"people": people}

    @api.router.post("/people", status_code=201)
    def create_person(body: PersonBody, ctx=api.ctx):
        count = ctx.db.execute("SELECT COUNT(*) FROM plg_people_people").fetchone()[0]
        if count >= MAX_PEOPLE:
            raise HTTPException(status_code=409, detail="too many people")
        year, month, day = parse_birthday(body.birthday)
        moment = ctx.now.isoformat(timespec="seconds")
        cursor = ctx.db.execute(
            "INSERT INTO plg_people_people (name, birth_month, birth_day, birth_year, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (body.name, month, day, year, moment, moment),
        )
        return _public(person_or_404(ctx, cursor.lastrowid), date.fromisoformat(ctx.today))

    @api.router.put("/people/{person_id}")
    def update_person(person_id: int, body: PersonBody, ctx=api.ctx):
        person_or_404(ctx, person_id)
        year, month, day = parse_birthday(body.birthday)
        ctx.db.execute(
            "UPDATE plg_people_people SET name = ?, birth_month = ?, birth_day = ?, birth_year = ?, updated_at = ? "
            "WHERE id = ?",
            (body.name, month, day, year, ctx.now.isoformat(timespec="seconds"), person_id),
        )
        return _public(person_or_404(ctx, person_id), date.fromisoformat(ctx.today))

    @api.router.delete("/people/{person_id}")
    def delete_person(person_id: int, ctx=api.ctx):
        person_or_404(ctx, person_id)
        ctx.db.execute("DELETE FROM plg_people_people WHERE id = ?", (person_id,))
        return {"ok": True}
