import shutil
from pathlib import Path

import pytest

from tests.plugin_site import DAY, Site, activate, plugin_state

JOURNAL = "/api/v1/plugins/journal"
MOOD = "/api/v1/plugins/mood"
ROOT = Path(__file__).resolve().parent.parent / "plugins"


@pytest.fixture
def both(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    for name in ("journal", "mood"):
        shutil.copytree(ROOT / name, site.plugins / name)
    with site.running() as client:
        assert activate(client, "journal").status_code == 200
        assert activate(client, "mood").status_code == 200
        yield client, site


def write(client, mood=None, **extra):
    response = client.post(f"{JOURNAL}/entries", json={"body": "A day.", "mood": mood, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def summary(client):
    return client.get(f"{MOOD}/summary", params={"days": 14}).json()


def set_day_mood(client, value, day=DAY):
    client.post("/api/v1/reports", json={"day": day})
    assert client.put(f"{MOOD}/entries/{day}", json={"value": value}).status_code == 200


def test_an_entry_can_carry_a_mood_and_it_is_read_back(both):
    client, _ = both
    entry = write(client, mood=4)
    assert entry["mood"] == 4
    assert client.get(f"{JOURNAL}/entries/{entry['id']}").json()["mood"] == 4
    assert write(client)["mood"] is None


@pytest.mark.parametrize("mood", [0, 6, "x"])
def test_an_invalid_mood_is_refused(both, mood):
    client, _ = both
    assert client.post(f"{JOURNAL}/entries", json={"body": "A day.", "mood": mood}).status_code == 422


def test_an_entry_mood_alone_makes_a_mood_for_that_day(both):
    client, _ = both
    write(client, mood=2, day=DAY)
    assert summary(client)["entries"] == [{"day": DAY, "value": 2.0, "journal_entries": 1}]


def test_the_entry_mood_weighs_less_than_the_mood_of_the_day(both):
    client, _ = both
    set_day_mood(client, 4)
    write(client, mood=1, day=DAY)
    result = summary(client)
    assert result["entries"] == [{"day": DAY, "value": 3.0, "journal_entries": 1}]
    assert result["distribution"] == [0, 0, 1, 0, 0]


def test_several_entries_of_a_day_count_as_one_average(both):
    client, _ = both
    set_day_mood(client, 5)
    write(client, mood=1, day=DAY)
    write(client, mood=3, day=DAY)
    assert summary(client)["entries"][0]["value"] == 4.0
    assert summary(client)["entries"][0]["journal_entries"] == 2


def test_changing_and_clearing_a_mood_follows_the_entry(both):
    client, _ = both
    entry = write(client, mood=5, day=DAY)
    client.put(f"{JOURNAL}/entries/{entry['id']}", json={"body": "A day.", "mood": 3})
    assert summary(client)["entries"][0]["value"] == 3.0
    client.put(f"{JOURNAL}/entries/{entry['id']}", json={"body": "A day."})
    assert summary(client)["entries"] == []


def test_deleting_an_entry_removes_its_mood(both):
    client, _ = both
    entry = write(client, mood=5, day=DAY)
    assert client.delete(f"{JOURNAL}/entries/{entry['id']}").status_code == 200
    assert summary(client)["entries"] == []


def test_the_mood_follows_an_entry_moved_to_another_day(both):
    client, _ = both
    entry = write(client, mood=5, day=DAY)
    client.put(f"{JOURNAL}/entries/{entry['id']}", json={"body": "A day.", "mood": 5, "day": "2026-10-19"})
    assert [item["day"] for item in summary(client)["entries"]] == ["2026-10-19"]


def test_turning_the_mood_tracker_on_later_catches_up(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    for name in ("journal", "mood"):
        shutil.copytree(ROOT / name, site.plugins / name)
    with site.running() as client:
        assert activate(client, "journal").status_code == 200
        write(client, mood=4, day=DAY)
        write(client, mood=2, day="2026-10-19")
        assert activate(client, "mood").status_code == 200
        assert [(item["day"], item["value"]) for item in summary(client)["entries"]] == [
            ("2026-10-19", 2.0),
            (DAY, 4.0),
        ]


def test_the_journal_works_without_the_mood_tracker(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(ROOT / "journal", site.plugins / "journal")
    with site.running() as client:
        assert activate(client, "journal").status_code == 200
        entry = write(client, mood=3)
        assert entry["mood"] == 3
        assert plugin_state(client, "journal")["state"] == "active"


def test_a_journal_mood_never_changes_the_scores(both):
    client, _ = both
    before = client.get("/api/v1/scores", params={"from": "2026-10-01", "to": DAY}).json()
    write(client, mood=1, day=DAY)
    assert client.get("/api/v1/scores", params={"from": "2026-10-01", "to": DAY}).json() == before
