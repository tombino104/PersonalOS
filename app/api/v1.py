import sqlite3
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from .. import __version__, activities, backup, reports, review, settings
from ..logical_day import logical_day
from ..plugins.manifest import RESERVED_PATHS
from . import backup_routes, profile_routes
from .auth_routes import protected_router
from .deps import get_conn, get_now, get_user_id, verify_origin
from .errors import ApiError
from .plugin_gateway import AsgiProxy
from .schemas import (
    ActivityCreate,
    ActivityUpdate,
    DoneUpdate,
    PluginActivation,
    PluginDataRemoval,
    ReviewNote,
    ReflectionUpdate,
    ReportOpen,
    SettingsUpdate,
)

router = APIRouter(
    prefix="/api/v1", dependencies=[Depends(verify_origin), Depends(get_user_id)]
)
router.include_router(protected_router)
router.include_router(backup_routes.router)
router.include_router(profile_routes.router)

MAX_RANGE_DAYS = 366
MAX_DOCK = 7
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


def _emit(request: Request, background: BackgroundTasks, event: str, payload: dict, now: datetime) -> None:
    registry = getattr(request.app.state, "plugins", None)
    if registry is not None:
        background.add_task(registry.dispatch, event, payload, now)


def _report_payload(detail: dict) -> dict:
    return {
        "day": detail["day"],
        "completions": detail["completions"],
        "reflection": detail["reflection"],
        "scores": detail["scores"],
        "overall": detail["overall"],
    }


def _report_id(conn: sqlite3.Connection, user_id: int, day: date) -> int:
    report_id = reports.report_id_for_day(conn, user_id, day)
    if report_id is None:
        raise ApiError(404, "not_found", f"no report for {day.isoformat()}")
    return report_id


@router.get("/info")
def info() -> dict:
    return {"api": "1", "version": __version__}


@router.get("/today")
def today(
    conn: sqlite3.Connection = Depends(get_conn), now: datetime = Depends(get_now)
) -> dict:
    day = logical_day(now, settings.day_rules(conn))
    moment = reports.opens_at(conn, day)
    locked = moment is not None and now < moment
    return {
        "day": day.isoformat(),
        "report_opens_at": moment.strftime("%H:%M") if locked else None,
    }


@router.get("/stats/areas")
def area_stats(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    start, end = _resolve_range(conn, now, start, end)
    return reports.area_averages(conn, user_id, start, end)


@router.get("/stats/activities")
def activity_stats(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    start, end = _resolve_range(conn, now, start, end)
    return {"activities": reports.activity_stats(conn, user_id, start, end)}


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
    request: Request,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    activity = activities.create(
        conn, body.area, body.name, body.weight, now, body.days, body.description, body.times_per_week
    )
    _emit(request, background, "activity.created", {"activity": activity}, now)
    return {"activity": activity, "warnings": activities.warnings(conn)}


@router.patch("/activities/{activity_id}")
def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    request: Request,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise ApiError(422, "validation_error", "fields cannot be null")
    before = activities.get(conn, activity_id)
    activity = activities.update(conn, activity_id, changes, now)
    archived_now = activity["archived_at"] is not None and before["archived_at"] is None
    event = "activity.archived" if archived_now else "activity.modified"
    _emit(request, background, event, {"activity": activity}, now)
    return {"activity": activity, "warnings": activities.warnings(conn)}


@router.delete("/activities/{activity_id}")
def delete_activity(
    activity_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    return activities.delete(conn, activity_id, now)


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
    request: Request,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    report_id = _report_id(conn, user_id, day)
    reports.set_done(conn, report_id, activity_id, body.done, now)
    detail = reports.report_detail(conn, report_id, now)
    if detail["completed"]:
        _emit(request, background, "report.modified", _report_payload(detail), now)
    return {"activity_id": activity_id, "done": body.done}


@router.put("/reports/{day}/reflection")
def set_reflection(
    day: date,
    body: ReflectionUpdate,
    request: Request,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    report_id = _report_id(conn, user_id, day)
    reports.set_reflection(conn, report_id, body.text, now)
    detail = reports.report_detail(conn, report_id, now)
    if detail["completed"]:
        _emit(request, background, "report.modified", _report_payload(detail), now)
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
    request: Request,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    report_id = _report_id(conn, user_id, day)
    was_completed = reports.report_detail(conn, report_id, now)["completed"]
    reports.complete_report(conn, report_id, now)
    detail = reports.report_detail(conn, report_id, now)
    event = "report.modified" if was_completed else "report.completed"
    _emit(request, background, event, _report_payload(detail), now)
    return detail


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


@router.get("/reviews/{week_start}")
def get_review(
    week_start: date,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
) -> dict:
    today = logical_day(now, settings.day_rules(conn))
    return review.summary(conn, user_id, week_start, today)


@router.put("/reviews/{week_start}/note")
def put_review_note(
    week_start: date,
    body: ReviewNote,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    today = logical_day(now, settings.day_rules(conn))
    return {"note": review.save_note(conn, week_start, today, body.text, now)}


@router.get("/settings")
def get_settings(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    rules = settings.day_rules(conn)
    return {
        "timezone": rules.timezone,
        "day_cutoff": rules.cutoff.strftime("%H:%M"),
        "report_lock": bool(settings.get(conn, "report_lock", False)),
        "report_time": settings.get(conn, "report_time", "20:00"),
        "backup_auto": backup.schedule(conn)["auto"],
        "backup_time": backup.schedule(conn)["time"],
        "home_period": settings.get(conn, "home_period", "week"),
        "home_areas": settings.get(conn, "home_areas", "all"),
        "theme": settings.get(conn, "theme"),
        "language": settings.get(conn, "language"),
        "dock": settings.get(conn, "dock"),
    }


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
    if "report_time" in changes:
        try:
            time.fromisoformat(changes["report_time"])
        except ValueError:
            raise ApiError(422, "invalid_report_time", "expected a time like 20:00") from None
        settings.put(conn, "report_time", changes["report_time"])
    if "report_lock" in changes:
        settings.put(conn, "report_lock", changes["report_lock"])
    if "backup_time" in changes:
        try:
            time.fromisoformat(changes["backup_time"])
        except ValueError:
            raise ApiError(422, "invalid_backup_time", "expected a time like 03:00") from None
        settings.put(conn, "backup_time", changes["backup_time"])
    if "backup_auto" in changes:
        settings.put(conn, "backup_auto", changes["backup_auto"])
    if "dock" in changes:
        keys = changes["dock"]
        if keys and (
            len(set(keys)) != len(keys)
            or len(keys) > MAX_DOCK
            or "questionnaire" not in keys
            or keys[-1] != "more"
            or keys.count("more") != 1
        ):
            raise ApiError(
                422,
                "invalid_dock",
                f"the dock holds at most {MAX_DOCK} different items, with the questionnaire in it and more last",
            )
        settings.put(conn, "dock", keys or None)
    for key in ("home_period", "home_areas", "theme", "language"):
        if key in changes:
            settings.put(conn, key, changes[key])
    return get_settings(conn)


def _registry(request: Request):
    registry = getattr(request.app.state, "plugins", None)
    if registry is None:
        raise ApiError(503, "plugins_unavailable", "the plugin system is not running")
    return registry


@router.get("/plugins")
def list_plugins(request: Request, conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    return {"plugins": _registry(request).describe(conn)}


@router.post("/plugins/{plugin_id}/activate")
def activate_plugin(
    plugin_id: str,
    body: PluginActivation,
    request: Request,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    registry = _registry(request)
    registry.activate(conn, plugin_id, body.accept_permissions, now)
    _emit(request, background, "plugin.activated", {"plugin": plugin_id}, now)
    return {"plugins": registry.describe(conn)}


@router.post("/plugins/{plugin_id}/deactivate")
def deactivate_plugin(
    plugin_id: str,
    request: Request,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    registry = _registry(request)
    registry.deactivate(conn, plugin_id, now)
    _emit(request, background, "plugin.deactivated", {"plugin": plugin_id}, now)
    return {"plugins": registry.describe(conn)}


@router.post("/plugins/{plugin_id}/remove-data")
def remove_plugin_data(
    plugin_id: str,
    body: PluginDataRemoval,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
) -> dict:
    registry = _registry(request)
    registry.remove_data(conn, plugin_id, body.confirm, now)
    return {"plugins": registry.describe(conn)}


@router.api_route(
    "/plugins/{plugin_id}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def plugin_gateway(
    plugin_id: str,
    path: str,
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    user_id: int = Depends(get_user_id),
    now: datetime = Depends(get_now),
):
    registry = _registry(request)
    loaded = registry.get(plugin_id)
    first_segment = path.split("/", 1)[0]
    active = loaded is not None and await run_in_threadpool(registry.is_active, conn, plugin_id)
    if not active or loaded.app is None or first_segment in RESERVED_PATHS:
        raise ApiError(404, "plugin_inactive", "this plugin is not active")
    request.scope["plugin_now"] = now
    request.scope["plugin_user_id"] = user_id
    return AsgiProxy(loaded.app, "/" + path)
