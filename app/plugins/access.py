import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

from .. import config, db, settings
from ..logical_day import logical_day

OK = sqlite3.SQLITE_OK
DENY = sqlite3.SQLITE_DENY
GUARD_PREFIX = "plgguard_"

_ALWAYS_ALLOWED = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_TRANSACTION,
    sqlite3.SQLITE_SAVEPOINT,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}
_WRITES = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
_READS_AND_WRITES = _WRITES | {sqlite3.SQLITE_READ}
_INDEXES = {sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX}
_CREATES_WITH_TABLE = {sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_DROP_TRIGGER}
_OBJECTS = {sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE}
_MASTER = {"sqlite_master", "sqlite_temp_master", "sqlite_schema", "sqlite_temp_schema"}
_FOREIGN_KEY_TARGETS = {"reports", "activities", "areas"}
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_]+$")


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def table_prefix(plugin_id: str) -> str:
    return f"plg_{plugin_id}_"


def readable_tables(permissions) -> set:
    tables: set = set()
    if "read_activities" in permissions:
        tables |= {"activities", "areas"}
    if "read_reports" in permissions:
        tables |= {"reports", "completions", "areas"}
    if "read_scores" in permissions:
        tables |= {"daily_scores", "areas"}
    return tables


def runtime_authorizer(plugin_id: str, permissions):
    prefix = table_prefix(plugin_id)
    readable = readable_tables(permissions)

    def authorize(action, arg1, arg2, database, source):
        if action in _ALWAYS_ALLOWED:
            return OK
        if action == sqlite3.SQLITE_READ:
            if arg1.startswith(prefix) or arg1 in readable:
                return OK
            if source and source.startswith(GUARD_PREFIX) and arg1 == "reports":
                return OK
            if arg1 in _FOREIGN_KEY_TARGETS and arg2 == "id":
                return OK
            return DENY
        if action in _WRITES:
            return OK if arg1.startswith(prefix) else DENY
        return DENY

    return authorize


def migration_authorizer(plugin_id: str):
    prefix = table_prefix(plugin_id)

    def authorize(action, arg1, arg2, database, source):
        if action in _ALWAYS_ALLOWED:
            return OK
        if action in _READS_AND_WRITES:
            if arg1 in _MASTER or arg1.startswith(prefix):
                return OK
            if arg1 == "plugin_migrations" and action != sqlite3.SQLITE_DELETE:
                return OK
            return DENY
        if action in _OBJECTS:
            return OK if arg1.startswith(prefix) else DENY
        if action in _INDEXES:
            owned = arg1.startswith(prefix) or arg1.startswith(f"sqlite_autoindex_{prefix}")
            return OK if owned and (arg2 or "").startswith(prefix) else DENY
        if action == sqlite3.SQLITE_REINDEX:
            return OK if arg1.startswith(prefix) else DENY
        if action in _CREATES_WITH_TABLE:
            return OK if arg1.startswith(prefix) and (arg2 or "").startswith(prefix) else DENY
        if action == sqlite3.SQLITE_ALTER_TABLE:
            return OK if (arg2 or "").startswith(prefix) else DENY
        return DENY

    return authorize


def install_report_guards(conn: sqlite3.Connection, plugin_id: str) -> None:
    prefix = table_prefix(plugin_id)
    tables = [
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        if row[0].startswith(prefix) and _SAFE_NAME.match(row[0])
    ]
    open_report = (
        "SELECT 1 FROM reports WHERE id = {ref}.report_id "
        "AND status = 'open' AND editable_until > app_now()"
    )
    for table in tables:
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        if "report_id" not in columns:
            continue
        for suffix in ("ins", "upd", "del"):
            conn.execute(f"DROP TRIGGER IF EXISTS {GUARD_PREFIX}{table}_{suffix}")
        message = "'report is closed or does not exist'"
        conn.execute(
            f"CREATE TRIGGER {GUARD_PREFIX}{table}_ins BEFORE INSERT ON {table} BEGIN "
            f"SELECT RAISE(ABORT, {message}) WHERE NOT EXISTS ({open_report.format(ref='NEW')}); END"
        )
        conn.execute(
            f"CREATE TRIGGER {GUARD_PREFIX}{table}_upd BEFORE UPDATE ON {table} BEGIN "
            f"SELECT RAISE(ABORT, {message}) WHERE NOT EXISTS ({open_report.format(ref='NEW')}) "
            f"OR NOT EXISTS ({open_report.format(ref='OLD')}); END"
        )
        conn.execute(
            f"CREATE TRIGGER {GUARD_PREFIX}{table}_del BEFORE DELETE ON {table} BEGIN "
            f"SELECT RAISE(ABORT, {message}) WHERE NOT EXISTS ({open_report.format(ref='OLD')}); END"
        )
    conn.commit()


@dataclass
class PluginContext:
    plugin_id: str
    db: sqlite3.Connection
    now: datetime
    today: str

    def report_id(self, day: str) -> int | None:
        core = db.connect(config.db_path())
        try:
            row = core.execute("SELECT id FROM reports WHERE day = ?", (day,)).fetchone()
        finally:
            core.close()
        return None if row is None else row["id"]

    def commit(self) -> None:
        if self.db.in_transaction:
            self.db.execute("COMMIT")

    def rollback(self) -> None:
        if self.db.in_transaction:
            self.db.execute("ROLLBACK")

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield self.db
        except BaseException:
            self.rollback()
            raise
        self.commit()

    def close(self) -> None:
        self.db.close()


def open_context(plugin_id: str, permissions, now: datetime) -> PluginContext:
    conn = db.connect(config.db_path(), check_same_thread=False)
    today = logical_day(now, settings.day_rules(conn)).isoformat()
    conn.isolation_level = None
    conn.create_function("app_now", 0, lambda: iso(now))
    conn.set_authorizer(runtime_authorizer(plugin_id, permissions))
    return PluginContext(plugin_id=plugin_id, db=conn, now=now, today=today)
