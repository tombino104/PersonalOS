import json
import sqlite3
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app import auth, db
from app.api.deps import get_now
from app.main import app
from tests.conftest import PASSWORD, USER

DAY = "2026-10-20"

GOOD_BACKEND = '''
def setup(api):
    @api.router.get("/hello")
    def hello(ctx=api.ctx):
        return {"plugin": ctx.plugin_id, "today": ctx.today}

    @api.router.put("/notes/{report_id}")
    def put_note(report_id: int, body: dict, ctx=api.ctx):
        ctx.db.execute(
            "INSERT OR REPLACE INTO plg___ID___notes (report_id, text) VALUES (?, ?)",
            (report_id, body["text"]),
        )
        return {"ok": True}

    @api.router.get("/notes/{report_id}")
    def get_note(report_id: int, ctx=api.ctx):
        row = ctx.db.execute(
            "SELECT text FROM plg___ID___notes WHERE report_id = ?", (report_id,)
        ).fetchone()
        return {"text": row["text"] if row else None}

    @api.router.delete("/notes/{report_id}")
    def delete_note(report_id: int, ctx=api.ctx):
        ctx.db.execute("DELETE FROM plg___ID___notes WHERE report_id = ?", (report_id,))
        return {"ok": True}

    @api.router.get("/boom")
    def boom():
        raise RuntimeError("the plugin is broken")

    @api.router.post("/announce")
    def announce():
        api.emit("__ID__.announced", {"hello": "world"})
        return {"ok": True}

    def record(ctx, payload):
        ctx.db.execute(
            "INSERT INTO plg___ID___events (event, keys) VALUES (?, ?)",
            ("seen", ",".join(sorted(payload))),
        )

    for event in LISTENS:
        api.on(event)(record)


LISTENS = __LISTENS__
'''

GOOD_MIGRATION = """
CREATE TABLE plg___ID___notes (
    report_id INTEGER PRIMARY KEY REFERENCES reports (id),
    text TEXT NOT NULL
);
CREATE TABLE plg___ID___events (
    id INTEGER PRIMARY KEY,
    event TEXT NOT NULL,
    keys TEXT NOT NULL
);
"""


def manifest(plugin_id, **extra):
    data = {
        "id": plugin_id,
        "name": plugin_id.title(),
        "version": "0.1.0",
        "description": "A plugin used by the tests",
        "core_api": "1.x",
        "permissions": ["api_routes", "listen_events"],
        "listens": [],
        "emits": [f"{plugin_id}.announced"],
        "migrations": "backend/migrations",
    }
    data.update(extra)
    return data


class Site:
    def __init__(self, tmp_path, monkeypatch, clock):
        self.root = tmp_path
        self.plugins = tmp_path / "plugins"
        self.plugins.mkdir()
        self.clock = clock
        monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("PLUGINS_DIR", str(self.plugins))

    @property
    def db_path(self):
        return self.root / "data" / "personal_os.db"

    def add(self, plugin_id, listens=(), permissions=None, extra=None, backend=None, migrations=None):
        folder = self.plugins / plugin_id
        (folder / "backend" / "migrations").mkdir(parents=True)
        data = manifest(plugin_id, listens=list(listens), **(extra or {}))
        if permissions is not None:
            data["permissions"] = permissions
        (folder / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
        code = backend if backend is not None else GOOD_BACKEND
        code = code.replace("__ID__", plugin_id).replace("__LISTENS__", repr(list(listens)))
        (folder / "backend" / "__init__.py").write_text(code, encoding="utf-8")
        scripts = migrations if migrations is not None else {"001_init": GOOD_MIGRATION}
        for name, sql in scripts.items():
            (folder / "backend" / "migrations" / f"{name}.sql").write_text(
                sql.replace("__ID__", plugin_id), encoding="utf-8"
            )
        return folder

    @contextmanager
    def running(self):
        app.dependency_overrides[get_now] = lambda: self.clock.now
        with TestClient(app) as client:
            conn = db.connect(self.db_path)
            if auth.setup_required(conn):
                auth.create_user(conn, USER, PASSWORD)
            conn.close()
            response = client.post("/api/v1/auth/login", json={"name": USER, "password": PASSWORD})
            assert response.status_code == 200
            yield client
        app.dependency_overrides.clear()

    def rows(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            return [dict(row) for row in conn.execute(sql, params)]
        finally:
            conn.close()

    def report_id(self, day=DAY):
        return self.rows("SELECT id FROM reports WHERE day = ?", (day,))[0]["id"]


def activate(client, plugin_id, accept=True):
    return client.post(f"/api/v1/plugins/{plugin_id}/activate", json={"accept_permissions": accept})


def plugin_state(client, plugin_id):
    plugins = client.get("/api/v1/plugins").json()["plugins"]
    return next(item for item in plugins if item["id"] == plugin_id)
