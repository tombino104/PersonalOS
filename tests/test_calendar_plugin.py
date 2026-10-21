import importlib.util
import shutil
from datetime import date
from pathlib import Path

import pytest

from tests.plugin_site import Site, activate, plugin_state

CALENDAR = "/api/v1/plugins/calendar"
SOURCE = Path(__file__).resolve().parent.parent / "plugins" / "calendar"


def load_recurrence():
    spec = importlib.util.spec_from_file_location("calendar_recurrence", SOURCE / "backend" / "recurrence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.occurrences


occurrences = load_recurrence()


def d(text):
    return date.fromisoformat(text)


def days(first, repeat, start, end, until=None):
    return [
        item.isoformat()
        for item in occurrences(d(first), repeat, d(until) if until else None, d(start), d(end))
    ]


def test_a_single_event_appears_only_inside_the_range():
    assert days("2026-10-20", "none", "2026-10-01", "2026-10-31") == ["2026-10-20"]
    assert days("2026-10-20", "none", "2026-11-01", "2026-11-30") == []


def test_daily_and_weekly_repeats_start_from_the_first_day():
    assert days("2026-10-20", "daily", "2026-10-18", "2026-10-22") == ["2026-10-20", "2026-10-21", "2026-10-22"]
    assert days("2026-10-06", "weekly", "2026-10-15", "2026-11-05") == ["2026-10-20", "2026-10-27", "2026-11-03"]


def test_a_repeat_stops_at_the_until_day_included():
    assert days("2026-10-20", "daily", "2026-10-01", "2026-10-31", until="2026-10-22") == [
        "2026-10-20",
        "2026-10-21",
        "2026-10-22",
    ]


def test_monthly_repeats_clamp_to_the_last_day_of_short_months():
    assert days("2026-01-31", "monthly", "2026-01-01", "2026-04-30") == [
        "2026-01-31",
        "2026-02-28",
        "2026-03-31",
        "2026-04-30",
    ]


def test_yearly_repeats_handle_leap_days_and_start_inside_the_range():
    assert days("2024-02-29", "yearly", "2026-01-01", "2028-12-31") == ["2026-02-28", "2027-02-28", "2028-02-29"]
    assert days("2020-10-21", "yearly", "2026-10-21", "2026-10-21") == ["2026-10-21"]
    assert days("2020-10-21", "yearly", "2026-10-22", "2027-10-20") == []


@pytest.fixture
def calendar(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "calendar")
    with site.running() as client:
        yield client, site


def event(**changes):
    body = {"title": "Dentist", "day": "2026-10-22", "time": "09:30", "category": "health"}
    body.update(changes)
    return body


def test_the_calendar_is_active_without_any_action(calendar):
    client, _ = calendar
    item = plugin_state(client, "calendar")
    assert item["state"] == "active"
    assert item["default_active"] is True
    assert item["entries"][0]["placement"] == "dock"
    assert sorted(item["permissions"]) == ["api_routes", "ui_panel"]


def test_turning_it_off_is_remembered_across_restarts(calendar, tmp_path, monkeypatch, clock):
    client, site = calendar
    assert client.post("/api/v1/plugins/calendar/deactivate").status_code == 200
    with site.running() as again:
        assert plugin_state(again, "calendar")["state"] == "inactive"


def test_an_event_is_created_read_updated_and_deleted(calendar):
    client, _ = calendar
    created = client.post(f"{CALENDAR}/events", json=event(notes="  bring the card  "))
    assert created.status_code == 201
    body = created.json()
    assert (body["title"], body["notes"], body["repeat"], body["until"]) == ("Dentist", "bring the card", "none", None)
    assert client.get(f"{CALENDAR}/events/{body['id']}").json() == body
    changed = client.put(f"{CALENDAR}/events/{body['id']}", json=event(title="Dentist, moved", time=None))
    assert (changed.json()["title"], changed.json()["time"]) == ("Dentist, moved", None)
    assert client.delete(f"{CALENDAR}/events/{body['id']}").status_code == 200
    assert client.get(f"{CALENDAR}/events/{body['id']}").status_code == 404
    assert client.delete(f"{CALENDAR}/events/{body['id']}").status_code == 404


def test_the_list_expands_repeats_and_sorts_all_day_first(calendar):
    client, _ = calendar
    client.post(f"{CALENDAR}/events", json=event(title="Late", time="21:00"))
    client.post(f"{CALENDAR}/events", json=event(title="All day", time=None))
    client.post(f"{CALENDAR}/events", json=event(title="Run", day="2026-10-20", time="07:00", repeat="weekly"))
    result = client.get(f"{CALENDAR}/events", params={"start": "2026-10-19", "end": "2026-11-01"}).json()
    found = [(item["day"], item["title"]) for item in result["occurrences"]]
    assert found == [
        ("2026-10-20", "Run"),
        ("2026-10-22", "All day"),
        ("2026-10-22", "Late"),
        ("2026-10-27", "Run"),
    ]
    assert all("event_id" in item for item in result["occurrences"])


def test_invalid_events_are_refused(calendar):
    client, _ = calendar
    url = f"{CALENDAR}/events"
    assert client.post(url, json=event(title="   ")).status_code == 422
    assert client.post(url, json=event(time="25:00")).status_code == 422
    assert client.post(url, json=event(category="gaming")).status_code == 422
    assert client.post(url, json=event(day="1800-01-01")).status_code == 422
    assert client.post(url, json=event(until="2026-12-01")).status_code == 422
    assert client.post(url, json=event(repeat="daily", until="2026-10-01")).status_code == 422
    assert client.post(url, json=event(repeat="daily", until="2026-12-01")).status_code == 201


def test_the_range_is_limited(calendar):
    client, _ = calendar
    url = f"{CALENDAR}/events"
    assert client.get(url, params={"start": "2026-10-01", "end": "2026-09-01"}).status_code == 422
    assert client.get(url, params={"start": "2026-01-01", "end": "2026-12-31"}).status_code == 422


def test_it_needs_a_login(calendar):
    client, _ = calendar
    client.post("/api/v1/auth/logout")
    assert client.get(f"{CALENDAR}/events", params={"start": "2026-10-01", "end": "2026-10-31"}).status_code == 401


def test_the_calendar_cannot_touch_scores_or_reports(calendar):
    client, site = calendar
    client.post(f"{CALENDAR}/events", json=event())
    assert site.rows("SELECT COUNT(*) AS n FROM daily_scores")[0]["n"] == 0


def test_turning_it_on_twice_is_harmless(calendar):
    client, _ = calendar
    assert activate(client, "calendar").status_code == 200
    assert plugin_state(client, "calendar")["state"] == "active"
