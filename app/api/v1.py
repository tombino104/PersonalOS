import sqlite3
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Response

from .. import __version__, activities, reports, settings
from ..logical_day import logical_day
from .deps import get_conn, get_now, get_user_id
from .errors import ApiError
from .schemas import (
    ActivityCreate,
    ActivityUpdate,
    DoneUpdate,
    ReflectionUpdate,
    ReportOpen,
    SettingsUpdate,
)

router = APIRouter(prefix="/api/v1")

MAX_RANGE_DAYS = 366
DEFAULT_RANGE_DAYS = 90


def _resolve_range(
    conn: sqlite3.Connection, now: datetime, start: date | None, end: date | None
) -> tuple[date, date]:
    end = end or logical_day(now, settings.day_rules(conn))
    start = start or end - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if start > end:
        raise ApiError(422, "invalid_range", "'from' must not be after 'to'")
    if (end - start).days >= MAX_RANGE_DAYS:
        raise ApiError(422, "invalid_range", f"range cannot exceed {MAX_RANGE_DAYS} days")
    return start, end


def _report_id(conn: sqlite3.Connection, user_id: int, day: date) -> int:
    report_id = reports.report_id_for_day(conn, user_id, day)
    if report_id is None:
        raise ApiError(404, "not_found", f"no report for {day.isoformat()}")
    return report_id


@router.get("/info")
def info() -> dict:
    return {"api": "1", "version": __version__}


@router.get("/areas")
def list_areas(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    rows = conn.execute(
        "SELECT id, slug, name, position, color_token FROM areas ORDER BY position"
    ).fetchall()
    return {"areas": [dict(row) for row in rows]}


@router.get("/activities")
def list_activities(
    include_archived: bool = False, conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    return {
        "activities": activities.list_activities(conn, include_archived),
        "warnings": activities.warnings(conn),
    }


@router.post("/activities", status_code=201)
def create_activity(
    body: ActivityCreate,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    activity = activities.create(conn, body.area, body.name, body.weight, now)
    return {"activity": activity, "warnings": activities.warnings(conn)}


@router.patch("/activities/{activity_id}")
def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise ApiError(422, "validation_error", "fields cannot be null")
    activity = activities.update(conn, activity_id, changes, now)
    return {"activity": activity, "warnings": activities.warnings(conn)}


@router.post("/reports")
def open_report(
    body: ReportOpen,
    response: Response,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    existing = reports.report_id_for_day(conn, user_id, body.day)
    report_id = reports.open_report(conn, user_id, body.day, now, settings.day_rules(conn))
    response.status_code = 200 if existing else 201
    return reports.report_detail(conn, report_id, now)


@router.get("/reports")
def list_reports(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    start, end = _resolve_range(conn, now, start, end)
    return {"reports": reports.list_reports(conn, user_id, start, end, now)}


@router.get("/reports/{day}")
def get_report(
    day: date,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    return reports.report_detail(conn, _report_id(conn, user_id, day), now)


@router.put("/reports/{day}/completions/{activity_id}")
def set_completion(
    day: date,
    activity_id: int,
    body: DoneUpdate,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    report_id = _report_id(conn, user_id, day)
    reports.set_done(conn, report_id, activity_id, body.done, now)
    return {"activity_id": activity_id, "done": body.done}


@router.put("/reports/{day}/reflection")
def set_reflection(
    day: date,
    body: ReflectionUpdate,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    report_id = _report_id(conn, user_id, day)
    reports.set_reflection(conn, report_id, body.text, now)
    return {"reflection": body.text}


@router.post("/reports/{day}/sync")
def sync_report(
    day: date,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    report_id = _report_id(conn, user_id, day)
    reports.sync_draft(conn, report_id, now)
    return reports.report_detail(conn, report_id, now)


@router.post("/reports/{day}/complete")
def complete_report(
    day: date,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    report_id = _report_id(conn, user_id, day)
    reports.complete_report(conn, report_id, now)
    return reports.report_detail(conn, report_id, now)


@router.get("/scores")
def get_scores(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    start, end = _resolve_range(conn, now, start, end)
    return {"days": reports.scores_range(conn, user_id, start, end)}


@router.get("/settings")
def get_settings(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    rules = settings.day_rules(conn)
    return {"timezone": rules.timezone, "day_cutoff": rules.cutoff.strftime("%H:%M")}


@router.patch("/settings")
def update_settings(body: SettingsUpdate, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise ApiError(422, "validation_error", "fields cannot be null")
    if "timezone" in changes:
        try:
            ZoneInfo(changes["timezone"])
        except (KeyError, ValueError, OSError):
            raise ApiError(422, "invalid_timezone", "unknown timezone") from None
        settings.put(conn, "timezone", changes["timezone"])
    if "day_cutoff" in changes:
        try:
            time.fromisoformat(changes["day_cutoff"])
        except ValueError:
            raise ApiError(422, "invalid_day_cutoff", "expected a time like 04:00") from None
        settings.put(conn, "day_cutoff", changes["day_cutoff"])
    return get_settings(conn)
