import shutil
from datetime import date, timedelta
from pathlib import Path

import pytest

from tests.plugin_site import DAY, Site, activate, plugin_state

PEOPLE = "/api/v1/plugins/people"
SOURCE = Path(__file__).resolve().parent.parent / "plugins" / "people"


@pytest.fixture
def people(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "people")
    with site.running() as client:
        assert activate(client, "people").status_code == 200
        yield client, site


def add(client, name="Alex", **extra):
    response = client.post(f"{PEOPLE}/people", json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def mmdd(day: date) -> str:
    return f"{day.month:02d}-{day.day:02d}"


def test_the_manifest_is_valid_and_it_is_off_until_turned_on(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "people")
    with site.running() as client:
        assert plugin_state(client, "people")["state"] == "inactive"
        assert activate(client, "people").status_code == 200
        item = plugin_state(client, "people")
        assert item["permissions"] == ["api_routes", "ui_panel"]
        assert item["pages"] == ["list"]
        assert item["entries"][0]["placement"] == "more"


def test_the_plugin_cannot_read_reports_or_scores(people):
    client, _ = people
    permissions = plugin_state(client, "people")["permissions"]
    assert "read_reports" not in permissions and "read_scores" not in permissions


def test_a_person_needs_a_name_and_the_name_is_trimmed(people):
    client, _ = people
    assert add(client, "  Sam  ")["name"] == "Sam"
    assert client.post(f"{PEOPLE}/people", json={"name": "   "}).status_code == 422
    assert client.post(f"{PEOPLE}/people", json={"name": "x" * 101}).status_code == 422


def test_a_birthday_may_have_or_lack_a_year(people):
    client, _ = people
    without = add(client, "A", birthday="03-14")
    with_year = add(client, "B", birthday="1990-03-14")
    assert without["birthday"] == "03-14" and without["turning"] is None
    assert with_year["birthday"] == "1990-03-14" and with_year["turning"] is not None
    assert add(client, "C")["birthday"] is None


@pytest.mark.parametrize(
    "value", ["13-01", "02-30", "00-10", "1990-13-01", "1850-05-05", "5-5", "march", "2021-02-29"]
)
def test_a_bad_birthday_is_refused(people, value):
    client, _ = people
    assert client.post(f"{PEOPLE}/people", json={"name": "X", "birthday": value}).status_code == 422


def test_the_leap_day_is_accepted(people):
    client, _ = people
    assert add(client, "Leap", birthday="02-29")["birthday"] == "02-29"
    assert add(client, "Leap year", birthday="2000-02-29")["birthday"] == "2000-02-29"


def test_the_list_starts_with_the_next_birthdays_and_ends_with_people_without_one(people):
    client, _ = people
    today = date.fromisoformat(DAY)
    add(client, "Nobody")
    add(client, "Later", birthday=mmdd(today + timedelta(days=40)))
    add(client, "Today", birthday=mmdd(today))
    add(client, "Soon", birthday=mmdd(today + timedelta(days=3)))
    listing = client.get(f"{PEOPLE}/people").json()["people"]
    assert [p["name"] for p in listing] == ["Today", "Soon", "Later", "Nobody"]
    assert [p["days_until"] for p in listing] == [0, 3, 40, None]


def test_a_birthday_that_has_passed_this_year_comes_next_year(people):
    client, _ = people
    today = date.fromisoformat(DAY)
    person = add(client, "Past", birthday=mmdd(today - timedelta(days=1)))
    assert person["days_until"] >= 364
    assert date.fromisoformat(person["next_birthday"]) > today


def test_a_person_is_changed_and_deleted(people):
    client, _ = people
    person = add(client, "Old name", birthday="03-14")
    changed = client.put(f"{PEOPLE}/people/{person['id']}", json={"name": "New name", "birthday": None})
    assert changed.status_code == 200
    assert changed.json()["name"] == "New name" and changed.json()["birthday"] is None
    assert client.delete(f"{PEOPLE}/people/{person['id']}").status_code == 200
    assert client.get(f"{PEOPLE}/people").json()["people"] == []
    assert client.put(f"{PEOPLE}/people/{person['id']}", json={"name": "x"}).status_code == 404
    assert client.delete(f"{PEOPLE}/people/{person['id']}").status_code == 404
