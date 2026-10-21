import importlib.util
import logging
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool

from .. import audit, config, db, settings
import re

from .access import open_context, table_prefix
from .manifest import (
    CORE_API_VERSION,
    Manifest,
    ManifestError,
    core_compatible,
    load_manifest,
)
from .migrate import MigrationError, apply_migrations

logger = logging.getLogger("uvicorn.error")

MAX_CONSECUTIVE_ERRORS = 5
SAFE_TABLE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
RESTRICTED_KEYS = {
    "completions": "read_reports",
    "reflection": "read_reports",
    "scores": "read_scores",
    "overall": "read_scores",
    "activity": "read_activities",
}


class PluginNotFound(KeyError):
    pass


class PluginUnavailable(Exception):
    pass


class PermissionsNotAccepted(Exception):
    pass


class PluginActive(Exception):
    pass


class ConfirmationMismatch(Exception):
    pass


def handler_timeout() -> float:
    return float(os.environ.get("PLUGIN_HANDLER_TIMEOUT", "5"))


def filter_payload(payload: dict, permissions) -> dict:
    return {
        key: value
        for key, value in payload.items()
        if RESTRICTED_KEYS.get(key) is None or RESTRICTED_KEYS[key] in permissions
    }


@dataclass
class Loaded:
    id: str
    folder: Path
    manifest: Manifest | None = None
    error: str | None = None
    error_kind: str | None = None
    handlers: dict = field(default_factory=dict)
    app: FastAPI | None = None


def _guarded_route(registry, plugin_id: str):
    class GuardedRoute(APIRoute):
        def get_route_handler(self):
            original = super().get_route_handler()

            async def handler(request: Request):
                try:
                    response = await original(request)
                except (HTTPException, RequestValidationError):
                    raise
                except sqlite3.IntegrityError as error:
                    if "report is closed" in str(error):
                        return JSONResponse(
                            {"error": {"code": "report_closed", "message": "the report is closed"}},
                            status_code=409,
                        )
                    await run_in_threadpool(
                        registry.record_error, plugin_id, f"{request.method} {request.url.path}", error
                    )
                    return JSONResponse(
                        {"error": {"code": "plugin_error", "message": "the plugin failed"}}, status_code=500
                    )
                except Exception as error:
                    if error.__class__.__name__ == "ApiError":
                        raise
                    await run_in_threadpool(
                        registry.record_error, plugin_id, f"{request.method} {request.url.path}", error
                    )
                    return JSONResponse(
                        {"error": {"code": "plugin_error", "message": "the plugin failed"}}, status_code=500
                    )
                if response.status_code < 500:
                    await run_in_threadpool(registry.record_success, plugin_id)
                return response

            return handler

    return GuardedRoute


class PluginApi:
    def __init__(self, registry, loaded: Loaded):
        self.id = loaded.id
        self._registry = registry
        self._loaded = loaded
        self.router = APIRouter(route_class=_guarded_route(registry, loaded.id))
        self.ctx = Depends(self._open_context)

    def on(self, event: str, handler=None):
        manifest = self._loaded.manifest

        def register(function):
            if "listen_events" not in manifest.permissions:
                raise ValueError("listening to events needs the 'listen_events' permission")
            if event not in manifest.listens:
                raise ValueError(f"event '{event}' is not declared in 'listens'")
            self._loaded.handlers.setdefault(event, []).append(function)
            return function

        return register(handler) if handler is not None else register

    def emit(self, event: str, payload: dict | None = None) -> None:
        if event not in self._loaded.manifest.emits:
            raise ValueError(f"event '{event}' is not declared in 'emits'")
        self._registry.dispatch(event, payload or {}, datetime.now(timezone.utc))

    def _open_context(self, request: Request):
        manifest = self._loaded.manifest
        context = open_context(manifest.id, manifest.permissions, request.scope["plugin_now"])
        try:
            yield context
        finally:
            context.close()


class Registry:
    def __init__(self):
        self.plugins: dict[str, Loaded] = {}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="plugin")

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def load(self, plugins_dir: Path, now: datetime) -> None:
        self.plugins = {}
        if plugins_dir.is_dir():
            folders = sorted(
                path
                for path in plugins_dir.iterdir()
                if path.is_dir() and not path.name.startswith(("_", "."))
            )
            for folder in folders:
                self.plugins[folder.name] = self._load_one(folder)
        self._upgrade_installed(now)

    def _load_one(self, folder: Path) -> Loaded:
        loaded = Loaded(id=folder.name, folder=folder)
        try:
            loaded.manifest = load_manifest(folder)
        except ManifestError as error:
            loaded.error, loaded.error_kind = str(error), "invalid"
            return loaded
        manifest = loaded.manifest
        if not core_compatible(manifest.core_api):
            loaded.error = f"it needs core API {manifest.core_api}, this app provides {CORE_API_VERSION}"
            loaded.error_kind = "incompatible"
            return loaded
        try:
            self._import_backend(loaded)
        except Exception as error:
            logger.exception("plugin %s failed to load", loaded.id)
            loaded.handlers = {}
            loaded.app = None
            loaded.error = f"it failed to load: {type(error).__name__}: {error}"[:500]
            loaded.error_kind = "broken"
        return loaded

    def _import_backend(self, loaded: Loaded) -> None:
        init = loaded.folder / "backend" / "__init__.py"
        if not init.is_file():
            return
        name = f"personal_os_plugin_{loaded.id}"
        for module_name in [m for m in sys.modules if m == name or m.startswith(f"{name}.")]:
            del sys.modules[module_name]
        spec = importlib.util.spec_from_file_location(
            name, init, submodule_search_locations=[str(init.parent)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            api = PluginApi(self, loaded)
            setup = getattr(module, "setup", None)
            if setup is not None:
                setup(api)
        except BaseException:
            sys.modules.pop(name, None)
            raise
        if api.router.routes:
            if "api_routes" not in loaded.manifest.permissions:
                raise ValueError("routes need the 'api_routes' permission")
            from ..api import errors

            sub = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
            errors.install(sub)
            sub.include_router(api.router)
            loaded.app = sub

    def _upgrade_installed(self, now: datetime) -> None:
        conn = db.connect(config.db_path())
        try:
            installed = {row["id"]: row for row in conn.execute("SELECT * FROM plugins")}
        finally:
            conn.close()
        for plugin_id, row in installed.items():
            loaded = self.plugins.get(plugin_id)
            if loaded is None or loaded.error:
                continue
            try:
                apply_migrations(loaded.manifest, loaded.folder, now)
            except MigrationError as error:
                loaded.error = f"migration failed: {error}"[:500]
                loaded.error_kind = "broken"
                continue
            if row["version"] != loaded.manifest.version or row["name"] != loaded.manifest.name:
                conn = db.connect(config.db_path())
                try:
                    with conn:
                        conn.execute(
                            "UPDATE plugins SET name = ?, version = ? WHERE id = ?",
                            (loaded.manifest.name, loaded.manifest.version, plugin_id),
                        )
                finally:
                    conn.close()

    def refresh(self, now: datetime) -> None:
        self._upgrade_installed(now)
        self.apply_defaults(now)

    def apply_defaults(self, now: datetime) -> None:
        conn = db.connect(config.db_path())
        try:
            applied = settings.get(conn, "default_plugins_applied", [])
            for plugin_id, loaded in self.plugins.items():
                if loaded.error or loaded.manifest is None or not loaded.manifest.default_active:
                    continue
                if plugin_id in applied:
                    continue
                try:
                    self.activate(conn, plugin_id, True, now)
                except (PluginUnavailable, PluginNotFound) as error:
                    logger.warning("default plugin %s could not be activated: %s", plugin_id, error)
                    continue
                applied.append(plugin_id)
            settings.put(conn, "default_plugins_applied", applied)
        finally:
            conn.close()

    def get(self, plugin_id: str) -> Loaded | None:
        return self.plugins.get(plugin_id)

    def is_active(self, conn: sqlite3.Connection, plugin_id: str) -> bool:
        row = conn.execute("SELECT active FROM plugins WHERE id = ?", (plugin_id,)).fetchone()
        return bool(row and row["active"])

    def describe(self, conn: sqlite3.Connection) -> list[dict]:
        rows = {row["id"]: row for row in conn.execute("SELECT * FROM plugins")}
        result = []
        for plugin_id in sorted(set(self.plugins) | set(rows)):
            loaded = self.plugins.get(plugin_id)
            row = rows.get(plugin_id)
            item = {
                "id": plugin_id,
                "name": plugin_id,
                "version": row["version"] if row else None,
                "description": "",
                "core_api": None,
                "permissions": [],
                "questionnaire_blocks": [],
                "report_sections": [],
                "widgets": [],
                "pages": [],
                "entries": [],
                "settings": False,
                "installed": row is not None,
                "active": bool(row and row["active"]),
                "consecutive_errors": row["consecutive_errors"] if row else 0,
                "message": row["last_error"] if row else None,
            }
            if row:
                item["name"] = row["name"]
            if loaded is not None and loaded.manifest is not None:
                item.update(loaded.manifest.to_public())
            if loaded is None:
                item["state"] = "missing"
            elif loaded.error:
                item["state"] = loaded.error_kind
                item["message"] = loaded.error
                item["active"] = False
            elif row and row["status"] == "error":
                item["state"] = "error"
            elif row and row["active"]:
                item["state"] = "active"
            else:
                item["state"] = "inactive"
            result.append(item)
        return result

    def activate(self, conn: sqlite3.Connection, plugin_id: str, accept: bool, now: datetime) -> None:
        loaded = self.plugins.get(plugin_id)
        if loaded is None:
            raise PluginNotFound(f"plugin {plugin_id} not found")
        if loaded.error:
            raise PluginUnavailable(loaded.error)
        if not accept:
            raise PermissionsNotAccepted("the permissions must be accepted to activate a plugin")
        manifest = loaded.manifest
        try:
            apply_migrations(manifest, loaded.folder, now)
        except MigrationError as error:
            loaded.error = f"migration failed: {error}"[:500]
            loaded.error_kind = "broken"
            raise PluginUnavailable(loaded.error) from None
        moment = now.astimezone(timezone.utc).isoformat(timespec="seconds")
        with conn:
            conn.execute(
                "INSERT INTO plugins (id, name, version, active, status, consecutive_errors, "
                "last_error, installed_at) VALUES (?, ?, ?, 1, 'ok', 0, NULL, ?) "
                "ON CONFLICT (id) DO UPDATE SET name = excluded.name, version = excluded.version, "
                "active = 1, status = 'ok', consecutive_errors = 0, last_error = NULL",
                (manifest.id, manifest.name, manifest.version, moment),
            )
            audit.log(conn, "user", "plugin.activated", {"plugin": plugin_id}, now)

    def deactivate(self, conn: sqlite3.Connection, plugin_id: str, now: datetime) -> None:
        row = conn.execute("SELECT id FROM plugins WHERE id = ?", (plugin_id,)).fetchone()
        if row is None:
            raise PluginNotFound(f"plugin {plugin_id} is not installed")
        with conn:
            conn.execute("UPDATE plugins SET active = 0 WHERE id = ?", (plugin_id,))
            audit.log(conn, "user", "plugin.deactivated", {"plugin": plugin_id}, now)

    def remove_data(self, conn: sqlite3.Connection, plugin_id: str, confirm: str, now: datetime) -> None:
        row = conn.execute("SELECT active FROM plugins WHERE id = ?", (plugin_id,)).fetchone()
        if row is None:
            raise PluginNotFound(f"plugin {plugin_id} has no data to remove")
        if row["active"]:
            raise PluginActive("turn the plugin off before removing its data")
        if confirm != plugin_id:
            raise ConfirmationMismatch("type the plugin id to confirm")
        core = db.connect(config.db_path())
        try:
            core.execute("PRAGMA foreign_keys = OFF")
            prefix = table_prefix(plugin_id)
            names = [
                item[0]
                for item in core.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
                if item[0].startswith(prefix) and SAFE_TABLE_NAME.match(item[0])
            ]
            for name in names:
                core.execute(f'DROP TABLE IF EXISTS "{name}"')
            with core:
                core.execute("DELETE FROM plugin_migrations WHERE plugin = ?", (plugin_id,))
                core.execute("DELETE FROM plugins WHERE id = ?", (plugin_id,))
                audit.log(core, "user", "plugin.data_removed", {"plugin": plugin_id, "tables": names}, now)
        finally:
            core.close()

    def record_success(self, plugin_id: str) -> None:
        conn = db.connect(config.db_path())
        try:
            with conn:
                conn.execute(
                    "UPDATE plugins SET status = 'ok', consecutive_errors = 0 "
                    "WHERE id = ? AND (status != 'ok' OR consecutive_errors > 0)",
                    (plugin_id,),
                )
        finally:
            conn.close()

    def record_error(self, plugin_id: str, where: str, error: BaseException) -> None:
        message = f"{type(error).__name__}: {error}"[:500]
        logger.warning("plugin %s failed in %s: %s", plugin_id, where, message)
        conn = db.connect(config.db_path())
        try:
            with conn:
                row = conn.execute(
                    "SELECT consecutive_errors, active FROM plugins WHERE id = ?", (plugin_id,)
                ).fetchone()
                if row is None:
                    return
                count = row["consecutive_errors"] + 1
                disable = bool(row["active"]) and count >= MAX_CONSECUTIVE_ERRORS
                conn.execute(
                    "UPDATE plugins SET status = 'error', consecutive_errors = ?, last_error = ?, "
                    "active = ? WHERE id = ?",
                    (count, message, 0 if disable else row["active"], plugin_id),
                )
                audit.log(conn, f"plugin:{plugin_id}", "error", {"where": where, "error": message})
                if disable:
                    audit.log(conn, "system", "plugin.auto_disabled", {"plugin": plugin_id, "errors": count})
        finally:
            conn.close()

    def dispatch(self, event: str, payload: dict, now: datetime) -> None:
        for loaded in list(self.plugins.values()):
            handlers = loaded.handlers.get(event)
            if not handlers or loaded.manifest is None or loaded.error:
                continue
            conn = db.connect(config.db_path())
            try:
                active = self.is_active(conn, loaded.id)
            finally:
                conn.close()
            if not active:
                continue
            data = filter_payload(payload, loaded.manifest.permissions)
            for handler in handlers:
                self._run_handler(loaded, event, handler, data, now)

    def _run_handler(self, loaded: Loaded, event: str, handler, data: dict, now: datetime) -> None:
        context = open_context(loaded.id, loaded.manifest.permissions, now)
        future = self._executor.submit(handler, context, data)
        try:
            future.result(timeout=handler_timeout())
            context.commit()
        except FutureTimeout:
            self.record_error(loaded.id, f"event {event}", TimeoutError("the handler took too long"))
            return
        except Exception as error:
            try:
                context.rollback()
            except sqlite3.Error:
                pass
            self.record_error(loaded.id, f"event {event}", error)
            return
        finally:
            try:
                context.close()
            except sqlite3.Error:
                pass
        self.record_success(loaded.id)
