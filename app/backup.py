import json
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from . import __version__, config, db, settings

DB_NAME = "personal_os.db"
MANIFEST_NAME = "manifest.json"
DIRECTORY = "backups"
KINDS = {"auto": 7, "manual": 20, "before-restore": 5}
DEFAULT_TIME = "03:00"
MAX_UPLOAD_BYTES = 256 * 1024 * 1024
MAX_DATABASE_BYTES = 1024 * 1024 * 1024
NAME = re.compile(r"^personal-os-(auto|manual|before-restore)-(\d{8}-\d{6})\.zip$")


class InvalidBackup(Exception):
    pass


class BackupNotFound(KeyError):
    pass


def directory() -> Path:
    path = config.data_dir() / DIRECTORY
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _describe(path: Path) -> dict:
    match = NAME.match(path.name)
    created = datetime.strptime(match.group(2), "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
    return {
        "name": path.name,
        "kind": match.group(1),
        "size": path.stat().st_size,
        "created_at": created.isoformat(timespec="seconds"),
    }


def list_backups() -> list[dict]:
    items = [_describe(path) for path in directory().iterdir() if NAME.match(path.name)]
    return sorted(items, key=lambda item: item["created_at"], reverse=True)


def path_for(name: str) -> Path:
    if not NAME.match(name):
        raise BackupNotFound(name)
    path = directory() / name
    if not path.is_file():
        raise BackupNotFound(name)
    return path


def _snapshot(target: Path) -> list[str]:
    source = db.connect(config.db_path())
    copy = sqlite3.connect(target)
    try:
        source.backup(copy)
        versions = [row[0] for row in copy.execute("SELECT version FROM schema_migrations ORDER BY version")]
    finally:
        copy.close()
        source.close()
    return versions


def _prune(kind: str) -> None:
    kept = [item for item in list_backups() if item["kind"] == kind]
    for item in kept[KINDS[kind] :]:
        (directory() / item["name"]).unlink(missing_ok=True)


def create(kind: str, now: datetime) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown backup kind: {kind}")
    folder = directory()
    name = f"personal-os-{kind}-{_stamp(now)}.zip"
    final = folder / name
    work = Path(tempfile.mkdtemp(prefix=".work-", dir=folder))
    try:
        snapshot = work / DB_NAME
        versions = _snapshot(snapshot)
        manifest = {
            "app_version": __version__,
            "created_at": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
            "kind": kind,
            "migrations": versions,
        }
        partial = work / "backup.zip"
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot, DB_NAME)
            archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2))
        os.replace(partial, final)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    _prune(kind)
    return _describe(final)


def schedule(conn: sqlite3.Connection) -> dict:
    return {
        "auto": bool(settings.get(conn, "backup_auto", True)),
        "time": settings.get(conn, "backup_time", DEFAULT_TIME),
    }


def _latest_scheduled_moment(conn: sqlite3.Connection, now: datetime) -> datetime:
    zone = settings.day_rules(conn).zone
    local = now.astimezone(zone)
    moment = datetime.combine(local.date(), time.fromisoformat(schedule(conn)["time"]), tzinfo=zone)
    if moment > local:
        moment -= timedelta(days=1)
    return moment


def scheduled_due(conn: sqlite3.Connection, now: datetime) -> bool:
    if not schedule(conn)["auto"]:
        return False
    last = settings.get(conn, "last_auto_backup_at")
    return last is None or datetime.fromisoformat(last) < _latest_scheduled_moment(conn, now)


def run_scheduled(conn: sqlite3.Connection, now: datetime) -> dict | None:
    if not scheduled_due(conn, now):
        return None
    item = create("auto", now)
    settings.put(conn, "last_auto_backup_at", now.astimezone(timezone.utc).isoformat(timespec="seconds"))
    return item


def _extract_database(archive_path: Path, target: Path) -> None:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            try:
                info = archive.getinfo(DB_NAME)
            except KeyError:
                raise InvalidBackup("the file does not contain the database") from None
            if info.file_size > MAX_DATABASE_BYTES:
                raise InvalidBackup("the database in the file is too large")
            written = 0
            with archive.open(info) as source, open(target, "wb") as out:
                while chunk := source.read(1024 * 1024):
                    written += len(chunk)
                    if written > MAX_DATABASE_BYTES:
                        raise InvalidBackup("the database in the file is too large")
                    out.write(chunk)
    except zipfile.BadZipFile:
        raise InvalidBackup("the file is not a valid backup") from None


def _verify_database(path: Path) -> None:
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        raise InvalidBackup("the database in the file cannot be opened") from None
    try:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise InvalidBackup("the database in the file is damaged")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {"schema_migrations", "users", "reports", "activities"} <= tables:
            raise InvalidBackup("the file is not a Personal OS backup")
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    except sqlite3.Error:
        raise InvalidBackup("the database in the file cannot be read") from None
    finally:
        conn.close()
    known = {path.stem for path in db.MIGRATIONS_DIR.glob("*.sql")}
    if not applied <= known:
        raise InvalidBackup("the backup comes from a newer version of Personal OS")


def restore(archive_path: Path, now: datetime) -> dict:
    folder = directory()
    work = Path(tempfile.mkdtemp(prefix=".work-", dir=folder))
    try:
        candidate = work / DB_NAME
        _extract_database(archive_path, candidate)
        _verify_database(candidate)
        safety = create("before-restore", now)
        source = sqlite3.connect(candidate)
        live = db.connect(config.db_path())
        try:
            source.backup(live)
            db.migrate(live)
        finally:
            source.close()
            live.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return safety
