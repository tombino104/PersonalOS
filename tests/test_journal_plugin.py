import shutil
from pathlib import Path

import pytest

from tests.plugin_site import DAY, Site, activate, plugin_state

JOURNAL = "/api/v1/plugins/journal"
SOURCE = Path(__file__).resolve().parent.parent / "plugins" / "journal"


@pytest.fixture
def journal(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "journal")
    with site.running() as client:
        assert activate(client, "journal").status_code == 200
        yield client, site


def write(client, body="A quiet day.", **extra):
    response = client.post(f"{JOURNAL}/entries", json={"body": body, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_the_manifest_is_valid_and_it_is_off_until_turned_on(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "journal")
    with site.running() as client:
        item = plugin_state(client, "journal")
        assert item["state"] == "inactive"
        assert item["default_active"] is False
        assert activate(client, "journal").status_code == 200
        item = plugin_state(client, "journal")
        assert item["state"] == "active"
        assert item["permissions"] == ["api_routes", "ui_panel"]
        assert item["entries"][0]["placement"] == "dock"
        assert item["pages"] == ["entries"]


def test_the_plugin_cannot_read_reports_or_scores(journal):
    client, _ = journal
    permissions = plugin_state(client, "journal")["permissions"]
    assert "read_scores" not in permissions
    assert "read_reports" not in permissions


def test_an_entry_defaults_to_today_and_is_trimmed(journal):
    client, _ = journal
    entry = write(client, "  Slept well.  ", title="  Morning  ")
    assert entry["day"] == DAY
    assert (entry["title"], entry["body"]) == ("Morning", "Slept well.")


def test_a_title_is_optional_and_an_empty_one_is_dropped(journal):
    client, _ = journal
    assert write(client, "No title")["title"] is None
    assert write(client, "Blank title", title="   ")["title"] is None


def test_an_empty_entry_is_refused(journal):
    client, _ = journal
    assert client.post(f"{JOURNAL}/entries", json={"body": "   "}).status_code == 422
    assert client.post(f"{JOURNAL}/entries", json={}).status_code == 422


def test_limits_and_dates_are_checked(journal):
    client, _ = journal
    assert client.post(f"{JOURNAL}/entries", json={"body": "x" * 20001}).status_code == 422
    assert client.post(f"{JOURNAL}/entries", json={"body": "x", "title": "t" * 121}).status_code == 422
    assert client.post(f"{JOURNAL}/entries", json={"body": "x", "day": "2026-10-21"}).status_code == 422
    assert client.post(f"{JOURNAL}/entries", json={"body": "x", "day": "1969-01-01"}).status_code == 422
    assert client.post(f"{JOURNAL}/entries", json={"body": "x", "day": "2026-10-19"}).status_code == 201


def test_several_entries_can_share_a_day_and_the_newest_comes_first(journal):
    client, _ = journal
    older = write(client, "Older day", day="2026-10-10")
    first = write(client, "First today")
    second = write(client, "Second today")
    listing = client.get(f"{JOURNAL}/entries").json()
    assert listing["total"] == 3
    assert [item["id"] for item in listing["entries"]] == [second["id"], first["id"], older["id"]]


def test_an_entry_is_read_changed_and_deleted(journal):
    client, _ = journal
    entry = write(client, "Draft")
    assert client.get(f"{JOURNAL}/entries/{entry['id']}").json()["body"] == "Draft"
    changed = client.put(
        f"{JOURNAL}/entries/{entry['id']}", json={"body": "Final", "title": "Done", "day": "2026-10-18"}
    )
    assert changed.status_code == 200
    assert (changed.json()["body"], changed.json()["title"], changed.json()["day"]) == ("Final", "Done", "2026-10-18")
    kept = client.put(f"{JOURNAL}/entries/{entry['id']}", json={"body": "Same day"})
    assert kept.json()["day"] == "2026-10-18"
    assert client.delete(f"{JOURNAL}/entries/{entry['id']}").json() == {"ok": True}
    assert client.get(f"{JOURNAL}/entries/{entry['id']}").status_code == 404
    assert client.put(f"{JOURNAL}/entries/{entry['id']}", json={"body": "x"}).status_code == 404
    assert client.delete(f"{JOURNAL}/entries/{entry['id']}").status_code == 404


def test_an_entry_cannot_be_moved_to_the_future(journal):
    client, _ = journal
    entry = write(client)
    assert client.put(f"{JOURNAL}/entries/{entry['id']}", json={"body": "x", "day": "2026-10-30"}).status_code == 422


def test_search_matches_title_and_body_and_treats_wildcards_literally(journal):
    client, _ = journal
    write(client, "Went for a run by the river")
    write(client, "Nothing special", title="River thoughts")
    write(client, "Reached 100% of the plan")
    write(client, "Another day")
    found = client.get(f"{JOURNAL}/entries", params={"q": "river"}).json()
    assert found["total"] == 2
    assert client.get(f"{JOURNAL}/entries", params={"q": "100%"}).json()["total"] == 1
    assert client.get(f"{JOURNAL}/entries", params={"q": "%"}).json()["total"] == 1
    assert client.get(f"{JOURNAL}/entries", params={"q": "_"}).json()["total"] == 0


def test_the_list_can_be_paged_and_limited_to_a_range(journal):
    client, _ = journal
    for index in range(5):
        write(client, f"Entry {index}", day=f"2026-10-1{index}")
    page = client.get(f"{JOURNAL}/entries", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 5 and len(page["entries"]) == 2
    ranged = client.get(f"{JOURNAL}/entries", params={"start": "2026-10-11", "end": "2026-10-12"}).json()
    assert [item["day"] for item in ranged["entries"]] == ["2026-10-12", "2026-10-11"]
    assert client.get(f"{JOURNAL}/entries", params={"limit": 101}).status_code == 422


def test_turning_it_off_keeps_the_entries_and_off_means_no_routes(journal):
    client, _ = journal
    write(client, "Kept")
    assert client.post("/api/v1/plugins/journal/deactivate").status_code == 200
    assert client.get(f"{JOURNAL}/entries").status_code == 404
    assert activate(client, "journal").status_code == 200
    assert client.get(f"{JOURNAL}/entries").json()["total"] == 1
