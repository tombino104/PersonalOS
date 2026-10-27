import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from tests.conftest import EVENING
from tests.plugin_site import DAY, Site, activate, plugin_state

MOOD = "/api/v1/plugins/mood"
SOURCE = Path(__file__).resolve().parent.parent / "plugins" / "mood"


@pytest.fixture
def mood(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "mood")
    with site.running() as client:
        assert activate(client, "mood").status_code == 200
        yield client, site


def open_day(client, day=DAY):
    assert client.post("/api/v1/reports", json={"day": day}).status_code in (200, 201)


def test_the_manifest_is_valid_and_lists_what_it_adds(mood):
    client, _ = mood
    item = plugin_state(client, "mood")
    assert item["state"] == "active"
    assert item["permissions"] == ["api_routes", "listen_events", "questionnaire_block", "ui_panel"]
    assert item["questionnaire_blocks"] == ["mood"]
    assert item["report_sections"] == ["mood"]
    assert item["entries"][0]["placement"] == "more"


def test_the_plugin_cannot_read_scores_or_reports(mood):
    client, _ = mood
    permissions = plugin_state(client, "mood")["permissions"]
    assert "read_scores" not in permissions
    assert "read_reports" not in permissions


def test_no_entry_means_empty_values(mood):
    client, _ = mood
    open_day(client)
    assert client.get(f"{MOOD}/entries/{DAY}").json() == {"value": None, "note": None}


def test_a_value_and_a_note_are_saved_and_read_back(mood):
    client, _ = mood
    open_day(client)
    saved = client.put(f"{MOOD}/entries/{DAY}", json={"value": 4, "note": "  A calm day  "})
    assert saved.json() == {"value": 4, "note": "A calm day"}
    assert client.get(f"{MOOD}/entries/{DAY}").json() == {"value": 4, "note": "A calm day"}


def test_a_note_alone_is_allowed_and_a_second_save_replaces_the_first(mood):
    client, _ = mood
    open_day(client)
    client.put(f"{MOOD}/entries/{DAY}", json={"value": None, "note": "just words"})
    assert client.get(f"{MOOD}/entries/{DAY}").json() == {"value": None, "note": "just words"}
    client.put(f"{MOOD}/entries/{DAY}", json={"value": 2, "note": None})
    assert client.get(f"{MOOD}/entries/{DAY}").json() == {"value": 2, "note": None}


def test_clearing_both_fields_removes_the_entry(mood):
    client, site = mood
    open_day(client)
    client.put(f"{MOOD}/entries/{DAY}", json={"value": 3, "note": "x"})
    client.put(f"{MOOD}/entries/{DAY}", json={"value": None, "note": "   "})
    assert site.rows("SELECT * FROM plg_mood_entries") == []


@pytest.mark.parametrize("payload", [{"value": 0}, {"value": 6}, {"value": "high"}, {"note": "x" * 301}])
def test_invalid_entries_are_rejected_and_are_not_plugin_faults(mood, payload):
    client, _ = mood
    open_day(client)
    response = client.put(f"{MOOD}/entries/{DAY}", json=payload)
    assert response.status_code == 422
    assert plugin_state(client, "mood")["consecutive_errors"] == 0


def test_there_is_no_entry_for_a_day_without_a_report(mood):
    client, _ = mood
    response = client.put(f"{MOOD}/entries/2026-10-19", json={"value": 3})
    assert (response.status_code, response.json()["error"]["code"]) == (404, "not_found")


def test_the_entry_cannot_change_once_the_report_is_closed(mood):
    client, site = mood
    open_day(client)
    client.put(f"{MOOD}/entries/{DAY}", json={"value": 5, "note": "before"})
    site.clock.now = EVENING + timedelta(days=2)
    late = client.put(f"{MOOD}/entries/{DAY}", json={"value": 1, "note": "after"})
    assert (late.status_code, late.json()["error"]["code"]) == (409, "report_closed")
    assert client.get(f"{MOOD}/entries/{DAY}").json() == {"value": 5, "note": "before"}


def test_the_summary_counts_values_and_lists_recent_notes(mood):
    client, site = mood
    values = {"2026-10-14": 3, "2026-10-15": 4, "2026-10-16": 4, "2026-10-18": 5, "2026-10-20": 2}
    for day, value in values.items():
        site.clock.now = EVENING - timedelta(days=20 - int(day[-2:]))
        open_day(client, day)
        client.put(f"{MOOD}/entries/{day}", json={"value": value, "note": f"note {day[-2:]}"})
    site.clock.now = EVENING
    result = client.get(f"{MOOD}/summary", params={"days": 14}).json()
    assert result["from"] == "2026-10-07" and result["to"] == "2026-10-20"
    assert result["distribution"] == [0, 1, 1, 2, 1]
    assert [entry["day"] for entry in result["entries"]] == sorted(values)
    assert result["notes"][0]["day"] == "2026-10-20"
    assert len(result["notes"]) == 5


def test_days_without_an_entry_are_absent_not_zero(mood):
    client, _ = mood
    open_day(client)
    result = client.get(f"{MOOD}/summary", params={"days": 7}).json()
    assert result["entries"] == [] and result["distribution"] == [0, 0, 0, 0, 0]


@pytest.mark.parametrize("days", [0, 6, 367])
def test_the_summary_validates_the_period(mood, days):
    client, _ = mood
    assert client.get(f"{MOOD}/summary", params={"days": days}).status_code == 422


def test_turning_it_off_hides_the_routes_and_keeps_the_data(mood):
    client, site = mood
    open_day(client)
    client.put(f"{MOOD}/entries/{DAY}", json={"value": 4})
    client.post("/api/v1/plugins/mood/deactivate")
    assert client.get(f"{MOOD}/entries/{DAY}").status_code == 404
    assert site.rows("SELECT value FROM plg_mood_entries") == [{"value": 4}]


def test_mood_never_changes_the_scores(mood):
    client, _ = mood
    open_day(client)
    before = client.post(f"/api/v1/reports/{DAY}/complete").json()
    client.put(f"{MOOD}/entries/{DAY}", json={"value": 1, "note": "heavy"})
    after = client.post(f"/api/v1/reports/{DAY}/complete").json()
    assert after["scores"] == before["scores"] and after["overall"] == before["overall"]
