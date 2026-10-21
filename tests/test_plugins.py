import sqlite3
import time
from datetime import timedelta

import pytest

from app import auth, db
from app.plugins import scheduler
from app.plugins.access import open_context
from app.plugins.manifest import ManifestError, parse_manifest
from tests.conftest import EVENING
from tests.plugin_site import DAY, Site, activate, manifest, plugin_state

PLUGINS = "/api/v1/plugins"


@pytest.fixture
def site(tmp_path, monkeypatch, clock):
    return Site(tmp_path, monkeypatch, clock)


def open_day(client):
    response = client.post("/api/v1/reports", json={"day": DAY})
    assert response.status_code in (200, 201)


class TestManifest:
    def parse(self, **changes):
        data = manifest("demo")
        data.update(changes)
        return parse_manifest(data, "demo")

    def test_a_minimal_manifest_is_valid(self):
        parsed = self.parse()
        assert parsed.id == "demo"
        assert parsed.permissions == {"api_routes", "listen_events"}

    @pytest.mark.parametrize(
        "changes",
        [
            {"id": "Demo"},
            {"id": "other"},
            {"version": "1.0"},
            {"core_api": "latest"},
            {"permissions": ["fly"]},
            {"adds": {"questionnaire_blocks": ["mood"]}},
            {"adds": {"widgets": ["w"]}},
            {"adds": {"surprise": []}},
            {"listens": ["report.completed"], "permissions": []},
            {"emits": ["other.thing"]},
            {"migrations": "../outside"},
            {"adds": {"entries": [{"id": "e", "label": "E", "icon": "home", "page": "p"}], "pages": []},
             "permissions": ["ui_panel"]},
            {"name": ""},
        ],
    )
    def test_invalid_manifests_are_rejected(self, changes):
        with pytest.raises(ManifestError):
            self.parse(**changes)

    def test_entries_and_blocks_are_parsed(self):
        parsed = self.parse(
            permissions=["questionnaire_block", "ui_panel"],
            adds={
                "questionnaire_blocks": ["mood"],
                "pages": ["trend"],
                "entries": [{"id": "mood", "label": "Mood", "icon": "smile", "placement": "dock", "page": "trend"}],
            },
        )
        assert parsed.questionnaire_blocks == ("mood",)
        assert parsed.entries[0].placement == "dock"


class TestDiscovery:
    def test_every_kind_of_plugin_is_listed_with_its_state(self, site):
        site.add("good")
        site.add("future", extra={"core_api": "2.x"})
        (site.plugins / "nomanifest").mkdir()
        (site.plugins / "badjson").mkdir()
        (site.plugins / "badjson" / "manifest.json").write_text("{nope", encoding="utf-8")
        site.add("crashing", backend="raise RuntimeError('boom at import')")
        site.add("syntax", backend="def setup(:")
        with site.running() as client:
            states = {item["id"]: item for item in client.get(PLUGINS).json()["plugins"]}
        assert states["good"]["state"] == "inactive"
        assert states["future"]["state"] == "incompatible"
        assert "core API" in states["future"]["message"]
        assert states["nomanifest"]["state"] == "invalid"
        assert states["badjson"]["state"] == "invalid"
        assert states["crashing"]["state"] == "broken"
        assert "boom at import" in states["crashing"]["message"]
        assert states["syntax"]["state"] == "broken"

    def test_listing_requires_a_session(self, site):
        site.add("good")
        with site.running() as client:
            client.post("/api/v1/auth/logout")
            assert client.get(PLUGINS).status_code == 401

    def test_declared_blocks_and_entries_are_exposed(self, site):
        site.add(
            "mood",
            permissions=["api_routes", "questionnaire_block", "ui_panel"],
            extra={
                "adds": {
                    "questionnaire_blocks": ["mood"],
                    "pages": ["trend"],
                    "entries": [{"id": "mood", "label": "Mood", "icon": "smile", "page": "trend"}],
                }
            },
        )
        with site.running() as client:
            item = plugin_state(client, "mood")
        assert item["questionnaire_blocks"] == ["mood"]
        assert item["entries"][0]["placement"] == "more"
        assert item["permissions"] == ["api_routes", "questionnaire_block", "ui_panel"]

    def test_plugins_that_declare_things_they_cannot_do_are_broken(self, site):
        site.add("unlisted", listens=[], backend="def setup(api):\n    api.on('report.completed')(lambda c, p: None)")
        site.add(
            "silent",
            permissions=["api_routes"],
            backend="def setup(api):\n    api.emit('silent.announced', {})\n    api.emit('silent.other', {})",
        )
        site.add(
            "noperm",
            permissions=[],
            extra={"emits": []},
            backend="from fastapi import Depends\ndef setup(api):\n    @api.router.get('/x')\n    def x():\n        return {}",
        )
        with site.running() as client:
            states = {i["id"]: i for i in client.get(PLUGINS).json()["plugins"]}
        assert states["unlisted"]["state"] == "broken"
        assert states["noperm"]["state"] == "broken"
        assert "api_routes" in states["noperm"]["message"]


class TestLifecycle:
    def test_activation_needs_the_permissions_to_be_accepted(self, site):
        site.add("good")
        with site.running() as client:
            response = activate(client, "good", accept=False)
            assert (response.status_code, response.json()["error"]["code"]) == (422, "permissions_not_accepted")
            assert plugin_state(client, "good")["state"] == "inactive"
            assert site.rows("SELECT name FROM sqlite_master WHERE name LIKE 'plg_good_%'") == []

    def test_activation_installs_the_plugin(self, site):
        site.add("good")
        with site.running() as client:
            response = activate(client, "good")
            assert response.status_code == 200
            assert plugin_state(client, "good")["state"] == "active"
            tables = {r["name"] for r in site.rows("SELECT name FROM sqlite_master WHERE type='table'")}
            assert {"plg_good_notes", "plg_good_events"} <= tables
            assert site.rows("SELECT version FROM plugin_migrations WHERE plugin = 'good'") == [
                {"version": "001_init"}
            ]
            assert site.rows("SELECT actor, action FROM audit_log WHERE action = 'plugin.activated'") == [
                {"actor": "user", "action": "plugin.activated"}
            ]

    def test_activating_twice_is_harmless(self, site):
        site.add("good")
        with site.running() as client:
            assert activate(client, "good").status_code == 200
            assert activate(client, "good").status_code == 200
            assert len(site.rows("SELECT * FROM plugin_migrations")) == 1

    def test_unknown_and_unusable_plugins_cannot_be_activated(self, site):
        site.add("crashing", backend="raise RuntimeError('boom')")
        with site.running() as client:
            assert activate(client, "nope").status_code == 404
            response = activate(client, "crashing")
            assert (response.status_code, response.json()["error"]["code"]) == (409, "plugin_unavailable")

    def test_a_broken_plugin_does_not_stop_the_others(self, site):
        site.add("crashing", backend="raise RuntimeError('boom')")
        site.add("good")
        with site.running() as client:
            assert activate(client, "good").status_code == 200
            assert client.get(f"{PLUGINS}/good/hello").json()["plugin"] == "good"
            assert client.get("/api/v1/areas").status_code == 200

    def test_deactivating_keeps_the_data_and_hides_the_routes(self, site):
        site.add("good")
        with site.running() as client:
            activate(client, "good")
            open_day(client)
            rid = site.report_id()
            assert client.put(f"{PLUGINS}/good/notes/{rid}", json={"text": "kept"}).status_code == 200

            response = client.post(f"{PLUGINS}/good/deactivate")
            assert response.status_code == 200
            assert plugin_state(client, "good")["state"] == "inactive"
            gone = client.get(f"{PLUGINS}/good/notes/{rid}")
            assert (gone.status_code, gone.json()["error"]["code"]) == (404, "plugin_inactive")
            assert site.rows("SELECT text FROM plg_good_notes") == [{"text": "kept"}]

            activate(client, "good")
            assert client.get(f"{PLUGINS}/good/notes/{rid}").json() == {"text": "kept"}

    def test_routes_of_inactive_or_unknown_plugins_are_404(self, site):
        site.add("good")
        with site.running() as client:
            assert client.get(f"{PLUGINS}/good/hello").status_code == 404
            assert client.get(f"{PLUGINS}/nope/hello").status_code == 404

    def test_plugin_routes_need_a_session(self, site):
        site.add("good")
        with site.running() as client:
            activate(client, "good")
            client.post("/api/v1/auth/logout")
            assert client.get(f"{PLUGINS}/good/hello").status_code == 401

    def test_deactivating_something_never_installed_is_404(self, site):
        site.add("good")
        with site.running() as client:
            assert client.post(f"{PLUGINS}/good/deactivate").status_code == 404

    def test_new_migrations_are_applied_when_the_app_starts(self, site):
        site.add("good")
        with site.running() as client:
            activate(client, "good")
        (site.plugins / "good" / "backend" / "migrations" / "002_more.sql").write_text(
            "CREATE TABLE plg_good_extra (id INTEGER PRIMARY KEY);", encoding="utf-8"
        )
        with site.running():
            tables = {r["name"] for r in site.rows("SELECT name FROM sqlite_master WHERE type='table'")}
            assert "plg_good_extra" in tables

    def test_a_migration_touching_foreign_tables_is_refused_and_rolled_back(self, site):
        site.add(
            "greedy",
            migrations={"001_bad": "CREATE TABLE plg_greedy_ok (id INTEGER); CREATE TABLE stolen (id INTEGER);"},
        )
        with site.running() as client:
            response = activate(client, "greedy")
            assert (response.status_code, response.json()["error"]["code"]) == (409, "plugin_unavailable")
            names = {r["name"] for r in site.rows("SELECT name FROM sqlite_master")}
            assert "stolen" not in names and "plg_greedy_ok" not in names
            assert plugin_state(client, "greedy")["state"] == "broken"

    @pytest.mark.parametrize(
        "sql",
        [
            "DROP TABLE activities;",
            "ALTER TABLE users ADD COLUMN x TEXT;",
            "DELETE FROM users;",
            "CREATE INDEX plg_greedy_i ON users (name);",
            "CREATE TRIGGER plg_greedy_t AFTER INSERT ON activities BEGIN SELECT 1; END;",
            "ATTACH DATABASE ':memory:' AS other;",
            "PRAGMA writable_schema = 1;",
        ],
    )
    def test_migrations_cannot_reach_core_objects(self, site, sql):
        site.add("greedy", migrations={"001_bad": sql})
        with site.running() as client:
            assert activate(client, "greedy").status_code == 409
            assert site.rows("SELECT COUNT(*) AS n FROM users")[0]["n"] == 1


class TestSandbox:
    def context(self, site, plugin_id, permissions):
        return open_context(plugin_id, frozenset(permissions), EVENING)

    @pytest.fixture
    def installed(self, site):
        site.add("good")
        site.add("other")
        with site.running() as client:
            activate(client, "good")
            activate(client, "other")
            yield site

    @pytest.mark.parametrize("table", ["users", "sessions", "settings", "plugins", "audit_log", "sqlite_master"])
    def test_private_tables_are_never_readable(self, installed, table):
        ctx = self.context(installed, "good", {"read_activities", "read_reports", "read_scores"})
        with pytest.raises(sqlite3.DatabaseError):
            ctx.db.execute(f"SELECT * FROM {table}").fetchall()

    @pytest.mark.parametrize(
        "table,permission",
        [
            ("activities", "read_activities"),
            ("areas", "read_activities"),
            ("reports", "read_reports"),
            ("completions", "read_reports"),
            ("daily_scores", "read_scores"),
        ],
    )
    def test_core_tables_need_the_matching_permission(self, installed, table, permission):
        denied = self.context(installed, "good", set())
        with pytest.raises(sqlite3.DatabaseError):
            denied.db.execute(f"SELECT * FROM {table}").fetchall()
        allowed = self.context(installed, "good", {permission})
        allowed.db.execute(f"SELECT * FROM {table}").fetchall()

    def test_scores_stay_hidden_without_the_scores_permission(self, installed):
        ctx = self.context(installed, "good", {"read_reports", "read_activities"})
        with pytest.raises(sqlite3.DatabaseError):
            ctx.db.execute("SELECT * FROM daily_scores").fetchall()

    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO activities (area_id, name, weight) VALUES (1, 'x', 1)",
            "UPDATE reports SET status = 'open'",
            "DELETE FROM completions",
            "DROP TABLE plg_good_notes",
            "CREATE TABLE plg_good_new (id INTEGER)",
            "ALTER TABLE plg_good_notes ADD COLUMN x TEXT",
            "PRAGMA table_info(users)",
            "ATTACH DATABASE ':memory:' AS other",
            "INSERT INTO plg_other_events (event, keys) VALUES ('x', 'y')",
            "SELECT * FROM plg_other_events",
        ],
    )
    def test_writes_ddl_and_foreign_tables_are_refused(self, installed, sql):
        ctx = self.context(installed, "good", {"read_activities", "read_reports", "read_scores"})
        with pytest.raises(sqlite3.DatabaseError):
            ctx.db.execute(sql).fetchall()

    def test_own_tables_are_fully_usable(self, installed):
        ctx = self.context(installed, "good", set())
        ctx.db.execute("INSERT INTO plg_good_events (event, keys) VALUES ('a', 'b')")
        assert ctx.db.execute("SELECT COUNT(*) FROM plg_good_events").fetchone()[0] == 1
        ctx.db.execute("UPDATE plg_good_events SET keys = 'c'")
        ctx.db.execute("DELETE FROM plg_good_events")
        ctx.close()


class TestClosedReports:
    @pytest.fixture
    def running(self, site):
        site.add("good")
        with site.running() as client:
            activate(client, "good")
            open_day(client)
            yield client, site

    def test_writes_to_an_open_report_work(self, running):
        client, site = running
        rid = site.report_id()
        assert client.put(f"{PLUGINS}/good/notes/{rid}", json={"text": "hi"}).status_code == 200
        assert client.put(f"{PLUGINS}/good/notes/{rid}", json={"text": "again"}).status_code == 200
        assert client.get(f"{PLUGINS}/good/notes/{rid}").json() == {"text": "again"}

    def test_every_kind_of_write_is_refused_once_the_report_is_closed(self, running):
        client, site = running
        rid = site.report_id()
        client.put(f"{PLUGINS}/good/notes/{rid}", json={"text": "before"})
        site.clock.now = EVENING + timedelta(days=2)
        for response in (
            client.put(f"{PLUGINS}/good/notes/{rid}", json={"text": "after"}),
            client.delete(f"{PLUGINS}/good/notes/{rid}"),
        ):
            assert (response.status_code, response.json()["error"]["code"]) == (409, "report_closed")
        assert client.get(f"{PLUGINS}/good/notes/{rid}").json() == {"text": "before"}
        assert plugin_state(client, "good")["consecutive_errors"] == 0

    def test_reports_that_do_not_exist_cannot_hold_plugin_data(self, running):
        client, _ = running
        response = client.put(f"{PLUGINS}/good/notes/9999", json={"text": "x"})
        assert (response.status_code, response.json()["error"]["code"]) == (409, "report_closed")

    def test_the_boundary_is_the_edit_deadline(self, running):
        client, site = running
        rid = site.report_id()
        site.clock.now = EVENING + timedelta(hours=29, minutes=59)
        assert client.put(f"{PLUGINS}/good/notes/{rid}", json={"text": "last"}).status_code == 200
        site.clock.now = EVENING + timedelta(hours=30)
        assert client.put(f"{PLUGINS}/good/notes/{rid}", json={"text": "late"}).status_code == 409

    def test_tables_without_a_report_are_not_restricted(self, site):
        site.add("good", listens=["report.closed"])
        with site.running() as client:
            activate(client, "good")
            open_day(client)
            later = EVENING + timedelta(days=2)
            scheduler.tick(client.app.state.plugins, later)
            assert site.rows("SELECT event FROM plg_good_events") == [{"event": "seen"}]


class TestEvents:
    def complete(self, client):
        open_day(client)
        return client.post(f"/api/v1/reports/{DAY}/complete")

    def keys(self, site, plugin_id):
        return [row["keys"] for row in site.rows(f"SELECT keys FROM plg_{plugin_id}_events ORDER BY id")]

    def test_handlers_run_after_the_report_is_saved(self, site):
        site.add("good", listens=["report.completed"], permissions=["api_routes", "listen_events", "read_reports"])
        with site.running() as client:
            activate(client, "good")
            assert self.complete(client).status_code == 200
            assert len(self.keys(site, "good")) == 1

    def test_payloads_are_filtered_by_permission(self, site):
        site.add("plain", listens=["report.completed"], permissions=["api_routes", "listen_events"])
        site.add("reader", listens=["report.completed"], permissions=["api_routes", "listen_events", "read_reports"])
        site.add(
            "scorer",
            listens=["report.completed"],
            permissions=["api_routes", "listen_events", "read_reports", "read_scores"],
        )
        with site.running() as client:
            for plugin_id in ("plain", "reader", "scorer"):
                activate(client, plugin_id)
            self.complete(client)
            assert self.keys(site, "plain") == ["day"]
            assert self.keys(site, "reader") == ["completions,day,reflection"]
            assert self.keys(site, "scorer") == ["completions,day,overall,reflection,scores"]

    def test_completed_is_sent_once_and_later_changes_are_modifications(self, site):
        site.add("good", listens=["report.completed", "report.modified"])
        with site.running() as client:
            activate(client, "good")
            self.complete(client)
            client.post(f"/api/v1/reports/{DAY}/complete")
            client.put(f"/api/v1/reports/{DAY}/reflection", json={"text": "note"})
            events = site.rows("SELECT event FROM plg_good_events")
            assert len(events) == 3

    def test_drafts_do_not_trigger_modifications(self, site):
        site.add("good", listens=["report.modified"])
        with site.running() as client:
            activate(client, "good")
            open_day(client)
            client.put(f"/api/v1/reports/{DAY}/reflection", json={"text": "draft"})
            assert site.rows("SELECT * FROM plg_good_events") == []

    def test_inactive_plugins_receive_nothing(self, site):
        site.add("good", listens=["report.completed"])
        with site.running() as client:
            activate(client, "good")
            client.post(f"{PLUGINS}/good/deactivate")
            self.complete(client)
            assert site.rows("SELECT * FROM plg_good_events") == []

    def test_activity_events_reach_plugins_that_may_read_activities(self, site):
        site.add(
            "watcher",
            listens=["activity.created", "activity.archived"],
            permissions=["api_routes", "listen_events", "read_activities"],
        )
        site.add("blind", listens=["activity.created"])
        with site.running() as client:
            activate(client, "watcher")
            activate(client, "blind")
            created = client.post("/api/v1/activities", json={"area": "social", "name": "Call", "weight": 1})
            activity_id = created.json()["activity"]["id"]
            client.patch(f"/api/v1/activities/{activity_id}", json={"archived": True})
            assert self.keys(site, "watcher") == ["activity", "activity"]
            assert self.keys(site, "blind") == [""]

    def test_plugin_events_reach_other_plugins(self, site):
        site.add("speaker")
        site.add("listener", listens=["speaker.announced"])
        with site.running() as client:
            activate(client, "speaker")
            activate(client, "listener")
            assert client.post(f"{PLUGINS}/speaker/announce").status_code == 200
            assert self.keys(site, "listener") == ["hello"]

    def test_activating_a_plugin_notifies_the_active_ones_itself_included(self, site):
        site.add("watcher", listens=["plugin.activated"])
        site.add("newcomer")
        with site.running() as client:
            activate(client, "watcher")
            activate(client, "newcomer")
            assert self.keys(site, "watcher") == ["plugin", "plugin"]


class TestFaultIsolation:
    FAILING = (
        "def setup(api):\n"
        "    @api.on('report.modified')\n"
        "    def fail(ctx, payload):\n"
        "        raise ValueError('handler failed')\n"
    )

    def failing_plugin(self, site, backend=None):
        site.add(
            "fragile",
            listens=["report.modified"],
            backend=backend or self.FAILING,
            extra={"emits": []},
        )

    def modify(self, client):
        client.put(f"/api/v1/reports/{DAY}/reflection", json={"text": "x"})

    def prepare(self, client):
        open_day(client)
        client.post(f"/api/v1/reports/{DAY}/complete")

    def test_a_failing_handler_never_fails_the_save(self, site):
        self.failing_plugin(site)
        with site.running() as client:
            activate(client, "fragile")
            self.prepare(client)
            response = client.put(f"/api/v1/reports/{DAY}/reflection", json={"text": "kept"})
            assert response.status_code == 200
            assert client.get(f"/api/v1/reports/{DAY}").json()["reflection"] == "kept"

    def test_errors_are_recorded_and_shown(self, site):
        self.failing_plugin(site)
        with site.running() as client:
            activate(client, "fragile")
            self.prepare(client)
            self.modify(client)
            item = plugin_state(client, "fragile")
            assert item["state"] == "error" and item["active"] is True
            assert item["consecutive_errors"] == 1
            assert "handler failed" in item["message"]
            log = site.rows("SELECT actor, action FROM audit_log WHERE action = 'error'")
            assert log == [{"actor": "plugin:fragile", "action": "error"}]

    def test_five_errors_in_a_row_switch_the_plugin_off(self, site):
        self.failing_plugin(site)
        with site.running() as client:
            activate(client, "fragile")
            self.prepare(client)
            for _ in range(5):
                self.modify(client)
            item = plugin_state(client, "fragile")
            assert item["active"] is False and item["state"] == "error"
            assert site.rows("SELECT action FROM audit_log WHERE action = 'plugin.auto_disabled'")
            self.modify(client)
            assert plugin_state(client, "fragile")["consecutive_errors"] == 5

    def test_a_switched_off_plugin_can_be_turned_back_on(self, site):
        self.failing_plugin(site)
        with site.running() as client:
            activate(client, "fragile")
            self.prepare(client)
            for _ in range(5):
                self.modify(client)
            assert activate(client, "fragile").status_code == 200
            item = plugin_state(client, "fragile")
            assert item["state"] == "active" and item["consecutive_errors"] == 0

    def test_a_success_resets_the_error_count(self, site):
        backend = (
            "COUNT = {'n': 0}\n"
            "def setup(api):\n"
            "    @api.on('report.modified')\n"
            "    def sometimes(ctx, payload):\n"
            "        COUNT['n'] += 1\n"
            "        if COUNT['n'] != 3:\n"
            "            raise ValueError('not yet')\n"
        )
        self.failing_plugin(site, backend)
        with site.running() as client:
            activate(client, "fragile")
            self.prepare(client)
            self.modify(client)
            self.modify(client)
            assert plugin_state(client, "fragile")["consecutive_errors"] == 2
            self.modify(client)
            item = plugin_state(client, "fragile")
            assert item["consecutive_errors"] == 0 and item["state"] == "active"

    def test_a_slow_handler_is_reported_as_a_timeout(self, site, monkeypatch):
        monkeypatch.setenv("PLUGIN_HANDLER_TIMEOUT", "0.2")
        backend = (
            "import time\n"
            "def setup(api):\n"
            "    @api.on('report.modified')\n"
            "    def slow(ctx, payload):\n"
            "        time.sleep(1.0)\n"
        )
        self.failing_plugin(site, backend)
        with site.running() as client:
            activate(client, "fragile")
            self.prepare(client)
            started = time.monotonic()
            response = client.put(f"/api/v1/reports/{DAY}/reflection", json={"text": "x"})
            assert response.status_code == 200
            assert time.monotonic() - started < 0.9
            item = plugin_state(client, "fragile")
            assert item["state"] == "error" and "TimeoutError" in item["message"]

    def test_a_handler_that_breaks_the_rules_is_stopped_by_the_sandbox(self, site):
        backend = (
            "def setup(api):\n"
            "    @api.on('report.modified')\n"
            "    def sneaky(ctx, payload):\n"
            "        ctx.db.execute('DELETE FROM users')\n"
        )
        self.failing_plugin(site, backend)
        with site.running() as client:
            activate(client, "fragile")
            self.prepare(client)
            self.modify(client)
            assert site.rows("SELECT COUNT(*) AS n FROM users")[0]["n"] == 1
            assert plugin_state(client, "fragile")["state"] == "error"

    def test_a_failing_route_returns_a_clean_error_and_the_app_keeps_working(self, site):
        site.add("good")
        site.add("other")
        with site.running() as client:
            activate(client, "good")
            activate(client, "other")
            response = client.get(f"{PLUGINS}/good/boom")
            assert (response.status_code, response.json()["error"]["code"]) == (500, "plugin_error")
            assert client.get("/api/v1/areas").status_code == 200
            assert client.get(f"{PLUGINS}/other/hello").status_code == 200
            item = plugin_state(client, "good")
            assert item["state"] == "error" and "the plugin is broken" in item["message"]
            assert plugin_state(client, "other")["state"] == "active"

    def test_a_good_request_clears_the_error_state(self, site):
        site.add("good")
        with site.running() as client:
            activate(client, "good")
            client.get(f"{PLUGINS}/good/boom")
            assert plugin_state(client, "good")["state"] == "error"
            assert client.get(f"{PLUGINS}/good/hello").status_code == 200
            assert plugin_state(client, "good")["state"] == "active"

    def test_validation_errors_in_plugin_routes_are_not_plugin_faults(self, site):
        site.add("good")
        with site.running() as client:
            activate(client, "good")
            response = client.put(f"{PLUGINS}/good/notes/not-a-number", json={"text": "x"})
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "validation_error"
            assert plugin_state(client, "good")["consecutive_errors"] == 0


class TestScheduler:
    def test_closing_reports_notifies_plugins_once(self, site):
        site.add("good", listens=["report.closed"], permissions=["api_routes", "listen_events", "read_reports"])
        with site.running() as client:
            activate(client, "good")
            open_day(client)
            registry = client.app.state.plugins
            assert scheduler.tick(registry, EVENING + timedelta(hours=29)) == []
            later = EVENING + timedelta(days=2)
            expired = scheduler.tick(registry, later)
            assert [item["day"] for item in expired] == [DAY]
            assert scheduler.tick(registry, later) == []
            assert site.rows("SELECT keys FROM plg_good_events") == [{"keys": "day,report_id"}]
            assert site.rows("SELECT status FROM reports") == [{"status": "closed"}]
