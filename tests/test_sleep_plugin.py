import shutil
from pathlib import Path

import pytest

from tests.plugin_site import DAY, Site, activate, plugin_state

SLEEP = "/api/v1/plugins/sleep"
SOURCE = Path(__file__).resolve().parent.parent / "plugins" / "sleep"


@pytest.fixture
def sleep(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "sleep")
    with site.running() as client:
        assert activate(client, "sleep").status_code == 200
        yield client, site


def put(client, day, **body):
    return client.put(f"{SLEEP}/nights/{day}", json=body)


def test_the_manifest_is_valid_and_it_is_off_until_turned_on(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "sleep")
    with site.running() as client:
        assert plugin_state(client, "sleep")["state"] == "inactive"
        assert activate(client, "sleep").status_code == 200
        item = plugin_state(client, "sleep")
        assert item["permissions"] == ["api_routes", "ui_panel"]
        assert item["pages"] == ["nights"]
        assert item["widgets"] == ["battery"]
        assert item["report_sections"] == ["night"]


def test_the_plugin_cannot_read_reports_or_scores(sleep):
    client, _ = sleep
    permissions = plugin_state(client, "sleep")["permissions"]
    assert "read_reports" not in permissions and "read_scores" not in permissions


def test_a_night_that_crosses_midnight_counts_the_hours_between(sleep):
    client, _ = sleep
    result = put(client, DAY, lights_off="23:15", woke_up="06:45")
    assert result.status_code == 200
    assert result.json() == {"day": DAY, "lights_off": "23:15", "woke_up": "06:45", "minutes": 450}


def test_a_night_after_midnight_counts_the_hours_between(sleep):
    client, _ = sleep
    assert put(client, DAY, lights_off="00:30", woke_up="07:30").json()["minutes"] == 420


def test_a_night_with_only_one_moment_has_no_length_yet(sleep):
    client, _ = sleep
    assert put(client, DAY, woke_up="07:00").json() == {
        "day": DAY,
        "lights_off": None,
        "woke_up": "07:00",
        "minutes": None,
    }


def test_a_second_moment_is_added_to_the_first(sleep):
    client, _ = sleep
    put(client, DAY, lights_off="23:00")
    result = put(client, DAY, woke_up="06:30")
    assert result.json() == {"day": DAY, "lights_off": "23:00", "woke_up": "06:30", "minutes": 450}


def test_clearing_one_moment_keeps_the_other(sleep):
    client, _ = sleep
    put(client, DAY, lights_off="23:00", woke_up="06:30")
    result = put(client, DAY, woke_up=None)
    assert result.json() == {"day": DAY, "lights_off": "23:00", "woke_up": None, "minutes": None}


def test_clearing_both_moments_removes_the_night(sleep):
    client, _ = sleep
    put(client, DAY, lights_off="23:00", woke_up="06:30")
    put(client, DAY, lights_off=None, woke_up=None)
    assert client.get(f"{SLEEP}/nights").json()["nights"] == []


def test_an_empty_day_reads_as_empty_and_not_as_zero(sleep):
    client, _ = sleep
    assert client.get(f"{SLEEP}/nights/{DAY}").json() == {
        "day": DAY,
        "lights_off": None,
        "woke_up": None,
        "minutes": None,
    }


@pytest.mark.parametrize("value", ["24:00", "7:00", "07:60", "seven", "07:00:00", ""])
def test_a_bad_time_is_refused(sleep, value):
    client, _ = sleep
    assert put(client, DAY, lights_off=value).status_code == 422


def test_a_night_longer_than_sixteen_hours_is_refused(sleep):
    client, _ = sleep
    assert put(client, DAY, lights_off="12:00", woke_up="05:00").status_code == 422
    assert put(client, DAY, lights_off="21:00", woke_up="21:00").status_code == 422
    assert put(client, DAY, lights_off="21:00", woke_up="13:00").status_code == 200


def test_tomorrow_is_allowed_for_a_late_evening_but_not_later(sleep):
    client, _ = sleep
    assert put(client, "2026-10-21", lights_off="23:30").status_code == 200
    assert put(client, "2026-10-22", lights_off="23:30").status_code == 422


def test_the_list_is_newest_first_and_can_be_limited_to_a_range(sleep):
    client, _ = sleep
    for day in ("2026-10-17", "2026-10-18", "2026-10-19", "2026-10-20"):
        put(client, day, lights_off="23:00", woke_up="07:00")
    listing = client.get(f"{SLEEP}/nights").json()["nights"]
    assert [night["day"] for night in listing] == ["2026-10-20", "2026-10-19", "2026-10-18", "2026-10-17"]
    ranged = client.get(f"{SLEEP}/nights", params={"start": "2026-10-18", "end": "2026-10-19"}).json()["nights"]
    assert [night["day"] for night in ranged] == ["2026-10-19", "2026-10-18"]
    assert len(client.get(f"{SLEEP}/nights", params={"limit": 2}).json()["nights"]) == 2
    assert client.get(f"{SLEEP}/nights", params={"limit": 0}).status_code == 422


def test_a_night_is_deleted(sleep):
    client, _ = sleep
    put(client, DAY, lights_off="23:00", woke_up="07:00")
    assert client.delete(f"{SLEEP}/nights/{DAY}").status_code == 200
    assert client.delete(f"{SLEEP}/nights/{DAY}").status_code == 404


def test_the_target_starts_at_seven_hours_and_can_be_changed(sleep):
    client, _ = sleep
    assert client.get(f"{SLEEP}/settings").json() == {"target_minutes": 420}
    assert client.put(f"{SLEEP}/settings", json={"target_minutes": 480}).json() == {"target_minutes": 480}
    assert client.get(f"{SLEEP}/settings").json() == {"target_minutes": 480}


@pytest.mark.parametrize("value", [0, 239, 841, "eight"])
def test_a_silly_target_is_refused(sleep, value):
    client, _ = sleep
    assert client.put(f"{SLEEP}/settings", json={"target_minutes": value}).status_code == 422
