import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    newly_applied = []
    for path in sorted(directory.glob("*.sql")):
        if path.stem in applied:
            continue
        script = path.read_text(encoding="utf-8")
        try:
            conn.executescript(
                f"BEGIN;\n{script}\n"
                "INSERT INTO schema_migrations (version, applied_at) "
                f"VALUES ('{path.stem}', datetime('now'));\nCOMMIT;"
            )
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        newly_applied.append(path.stem)
    return newly_applied
