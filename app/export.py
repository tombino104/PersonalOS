import csv
import io
import json
import re
import sqlite3
import zipfile
from datetime import datetime

from . import activities as activity_module
from . import settings as settings_module

SAFE_TABLE = re.compile(r"^plg_[a-z0-9_]+$")
SETTING_KEYS = (
    "timezone",
    "day_cutoff",
    "report_lock",
    "report_time",
    "home_period",
    "home_areas",
    "theme",
    "language",
    "dock",
)
README = """Personal OS export

activities.csv     your activities (deleted ones are left out)
reports.csv        one row per recorded day, with the free line you wrote
completions.csv    what you ticked each day, as it was that day
scores.csv         the relative score of each area, for each completed day
weekly_notes.csv   the notes written in the weekly review
journal.md         the entries of the journal plugin, if you use it
plugins/           the data of every plugin, one CSV per table
data.json          everything above in one file, plus your settings and profile

Nothing that protects the app is in here: no password, no setup code, no sessions.
Empty means nothing was recorded, not zero.
"""


def _cell(value):
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _csv(columns: list[str], rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_cell(row[column]) for column in columns])
    return buffer.getvalue().encode("utf-8-sig")


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _weekday_names(mask: int) -> str:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return " ".join(names[day] for day in activity_module.mask_to_days(mask))


def _journal(entries: list[dict]) -> bytes:
    parts = ["# Journal\n"]
    for entry in sorted(entries, key=lambda item: (item["day"], item["id"])):
        title = f" — {entry['title']}" if entry.get("title") else ""
        parts.append(f"\n## {entry['day']}{title}\n\n{entry['body']}\n")
    return "".join(parts).encode("utf-8")


def collect(conn: sqlite3.Connection, user_id: int) -> dict:
    activities = _rows(
        conn,
        "SELECT act.id, a.slug AS area, act.name, act.description, act.weight, act.days, "
        "act.times_per_week, act.created_at, act.archived_at "
        "FROM activities act JOIN areas a ON a.id = act.area_id "
        "WHERE act.deleted_at IS NULL ORDER BY a.position, act.id",
    )
    for row in activities:
        row["days"] = _weekday_names(row["days"])
    reports = _rows(
        conn,
        "SELECT day, completed_at, reflection FROM reports WHERE user_id = ? ORDER BY day",
        (user_id,),
    )
    completions = _rows(
        conn,
        "SELECT r.day, a.slug AS area, c.name_at_time AS activity, c.weight_at_time AS weight, "
        "c.done, c.target_at_time AS times_per_week, r.completed_at IS NOT NULL AS report_completed "
        "FROM completions c JOIN reports r ON r.id = c.report_id JOIN areas a ON a.id = c.area_id "
        "WHERE r.user_id = ? ORDER BY r.day, a.position, c.id",
        (user_id,),
    )
    scores = _rows(
        conn,
        "SELECT r.day, a.slug AS area, s.maximum, s.obtained, "
        "CASE WHEN s.maximum = 0 THEN NULL ELSE ROUND(100.0 * s.obtained / s.maximum, 1) END AS score "
        "FROM daily_scores s JOIN reports r ON r.id = s.report_id JOIN areas a ON a.id = s.area_id "
        "WHERE r.user_id = ? AND r.completed_at IS NOT NULL ORDER BY r.day, a.position",
        (user_id,),
    )
    notes = _rows(conn, "SELECT week_start, note, updated_at FROM weekly_reviews ORDER BY week_start")
    profile = conn.execute("SELECT display_name, about, birth_year FROM profile WHERE id = 1").fetchone()
    plugins = {}
    for item in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
        name = item["name"]
        if SAFE_TABLE.match(name):
            plugins[name] = _rows(conn, f'SELECT * FROM "{name}"')
    return {
        "activities": activities,
        "reports": reports,
        "completions": completions,
        "scores": scores,
        "weekly_notes": notes,
        "settings": {key: settings_module.get(conn, key) for key in SETTING_KEYS},
        "profile": dict(profile) if profile else None,
        "plugins": plugins,
    }


def build(conn: sqlite3.Connection, user_id: int, now: datetime) -> bytes:
    data = collect(conn, user_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", README)
        archive.writestr(
            "activities.csv",
            _csv(
                ["id", "area", "name", "description", "weight", "days", "times_per_week", "created_at", "archived_at"],
                data["activities"],
            ),
        )
        archive.writestr("reports.csv", _csv(["day", "completed_at", "reflection"], data["reports"]))
        archive.writestr(
            "completions.csv",
            _csv(["day", "area", "activity", "weight", "done", "times_per_week", "report_completed"], data["completions"]),
        )
        archive.writestr("scores.csv", _csv(["day", "area", "maximum", "obtained", "score"], data["scores"]))
        archive.writestr("weekly_notes.csv", _csv(["week_start", "note", "updated_at"], data["weekly_notes"]))
        for name, rows in data["plugins"].items():
            columns = list(rows[0].keys()) if rows else [
                item[1] for item in conn.execute(f'PRAGMA table_info("{name}")').fetchall()
            ]
            archive.writestr(f"plugins/{name}.csv", _csv(columns, rows))
        if "plg_journal_entries" in data["plugins"]:
            archive.writestr("journal.md", _journal(data["plugins"]["plg_journal_entries"]))
        payload = {"exported_at": now.isoformat(timespec="seconds"), **data}
        archive.writestr("data.json", json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return buffer.getvalue()
