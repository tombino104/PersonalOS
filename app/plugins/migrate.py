import re
import sqlite3
from datetime import datetime
from pathlib import Path

from .. import config, db
from .access import install_report_guards, iso, migration_authorizer
from .manifest import Manifest

_VERSION_NAME = re.compile(r"^[0-9A-Za-z_.-]+$")


class MigrationError(Exception):
    pass


def apply_migrations(manifest: Manifest, folder: Path, now: datetime) -> list[str]:
    core = db.connect(config.db_path())
    applied_now: list[str] = []
    try:
        if manifest.migrations:
            directory = (folder / manifest.migrations).resolve()
            if not directory.is_relative_to(folder.resolve()):
                raise MigrationError("the migrations folder is outside the plugin")
            files = sorted(directory.glob("*.sql")) if directory.is_dir() else []
            done = {
                row[0]
                for row in core.execute(
                    "SELECT version FROM plugin_migrations WHERE plugin = ?", (manifest.id,)
                )
            }
            for path in files:
                if path.stem in done:
                    continue
                if not _VERSION_NAME.match(path.stem):
                    raise MigrationError(f"invalid migration name: {path.name}")
                _run(manifest, path, now)
                applied_now.append(path.stem)
        install_report_guards(core, manifest.id)
    finally:
        core.close()
    return applied_now


def _run(manifest: Manifest, path: Path, now: datetime) -> None:
    conn = db.connect(config.db_path())
    conn.create_function("app_now", 0, lambda: iso(now))
    conn.set_authorizer(migration_authorizer(manifest.id))
    script = path.read_text(encoding="utf-8")
    try:
        conn.executescript(
            f"BEGIN;\n{script}\n"
            "INSERT INTO plugin_migrations (plugin, version, applied_at) "
            f"VALUES ('{manifest.id}', '{path.stem}', '{iso(now)}');\nCOMMIT;"
        )
    except sqlite3.Error as error:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise MigrationError(f"{path.name}: {error}") from None
    finally:
        conn.close()
