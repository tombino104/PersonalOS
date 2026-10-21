import sqlite3

import pytest

from app.plugins.access import open_context
from app.plugins.manifest import ManifestError, parse_manifest
from tests.conftest import EVENING
from tests.plugin_site import DAY, Site, activate, manifest, plugin_state

PLUGINS = "/api/v1/plugins"


@pytest.fixture
def site(tmp_path, monkeypatch, clock):
    return Site(tmp_path, monkeypatch, clock)


def open_day(client):
    assert client.post("/api/v1/reports", json={"day": DAY}).status_code in (200, 201)


class TestReportIdHelper:
    def test_plugins_find_a_report_without_reading_reports(self, site):
        site.add("good")
        with site.running() as client:
            activate(client, "good")
            open_day(client)
            rid = site.report_id()
            ctx = open_context("good", frozenset(), EVENING)
            assert ctx.report_id(DAY) == rid
            assert ctx.report_id("2026-01-01") is None
            with pytest.raises(sqlite3.DatabaseError):
                ctx.db.execute("SELECT id FROM reports WHERE day = ?", (DAY,)).fetchall()
            ctx.close()


class TestReportSections:
    def test_report_sections_are_parsed_and_need_the_ui_permission(self):
        data = manifest("demo", permissions=["ui_panel"], adds={"report_sections": ["mood"]})
        assert parse_manifest(data, "demo").report_sections == ("mood",)
        data["permissions"] = []
        with pytest.raises(ManifestError):
            parse_manifest(data, "demo")

    def test_report_sections_are_exposed(self, site):
        site.add("good", permissions=["api_routes", "ui_panel"], extra={"adds": {"report_sections": ["mood"]}})
        with site.running() as client:
            assert plugin_state(client, "good")["report_sections"] == ["mood"]


class TestDataRemoval:
    def remove(self, client, plugin_id, confirm):
        return client.post(f"{PLUGINS}/{plugin_id}/remove-data", json={"confirm": confirm})

    def installed_with_data(self, client, site):
        activate(client, "good")
        open_day(client)
        client.put(f"{PLUGINS}/good/notes/{site.report_id()}", json={"text": "precious"})

    def test_data_is_removed_only_when_the_plugin_is_off_and_confirmed(self, site):
        site.add("good")
        with site.running() as client:
            self.installed_with_data(client, site)
            active = self.remove(client, "good", "good")
            assert (active.status_code, active.json()["error"]["code"]) == (409, "plugin_active")
            client.post(f"{PLUGINS}/good/deactivate")
            wrong = self.remove(client, "good", "nope")
            assert (wrong.status_code, wrong.json()["error"]["code"]) == (422, "confirmation_mismatch")
            assert site.rows("SELECT text FROM plg_good_notes") == [{"text": "precious"}]

            done = self.remove(client, "good", "good")
            assert done.status_code == 200
            names = {r["name"] for r in site.rows("SELECT name FROM sqlite_master")}
            assert not {n for n in names if n.startswith("plg_good_")}
            assert not {n for n in names if n.startswith("plgguard_plg_good_")}
            assert site.rows("SELECT * FROM plugin_migrations WHERE plugin = 'good'") == []
            assert site.rows("SELECT * FROM plugins WHERE id = 'good'") == []
            assert site.rows("SELECT action FROM audit_log WHERE action = 'plugin.data_removed'")
            item = plugin_state(client, "good")
            assert item["state"] == "inactive" and item["installed"] is False

    def test_the_plugin_can_be_installed_again_from_scratch(self, site):
        site.add("good")
        with site.running() as client:
            self.installed_with_data(client, site)
            client.post(f"{PLUGINS}/good/deactivate")
            self.remove(client, "good", "good")
            assert activate(client, "good").status_code == 200
            assert site.rows("SELECT * FROM plg_good_notes") == []

    def test_core_data_is_never_touched(self, site):
        site.add("good")
        with site.running() as client:
            self.installed_with_data(client, site)
            client.post(f"{PLUGINS}/good/deactivate")
            self.remove(client, "good", "good")
            assert site.rows("SELECT COUNT(*) AS n FROM reports")[0]["n"] == 1
            assert site.rows("SELECT COUNT(*) AS n FROM users")[0]["n"] == 1

    def test_other_plugins_keep_their_data(self, site):
        site.add("good")
        site.add("other")
        with site.running() as client:
            activate(client, "other")
            activate(client, "good")
            open_day(client)
            client.put(f"{PLUGINS}/other/notes/{site.report_id()}", json={"text": "mine"})
            client.post(f"{PLUGINS}/good/deactivate")
            self.remove(client, "good", "good")
            assert site.rows("SELECT text FROM plg_other_notes") == [{"text": "mine"}]

    def test_nothing_to_remove_for_a_plugin_that_was_never_installed(self, site):
        site.add("good")
        with site.running() as client:
            assert self.remove(client, "good", "good").status_code == 404

    def test_the_route_needs_a_session(self, site):
        site.add("good")
        with site.running() as client:
            client.post("/api/v1/auth/logout")
            assert self.remove(client, "good", "good").status_code == 401

    def test_installed_flag_follows_the_lifecycle(self, site):
        site.add("good")
        with site.running() as client:
            assert plugin_state(client, "good")["installed"] is False
            activate(client, "good")
            assert plugin_state(client, "good")["installed"] is True
