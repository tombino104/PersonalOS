import sqlite3

import pytest

from app import config

ACTIVITIES = "/api/v1/activities"
SETTINGS = "/api/v1/settings"
DAY = "2026-10-20"


def make(client, name="Stretch", **extra):
    created = client.post(ACTIVITIES, json={"area": "physical", "name": name, "weight": 1, **extra})
    assert created.status_code == 201
    return created.json()["activity"]


def archive(client, activity):
    assert client.patch(f"{ACTIVITIES}/{activity['id']}", json={"archived": True}).status_code == 200


def rows(sql, *params):
    conn = sqlite3.connect(config.db_path())
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def test_only_an_archived_activity_can_be_deleted(client):
    activity = make(client)
    refused = client.delete(f"{ACTIVITIES}/{activity['id']}")
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "activity_not_archived")
    archive(client, activity)
    assert client.delete(f"{ACTIVITIES}/{activity['id']}").status_code == 200


def test_an_activity_never_used_in_a_report_is_erased_for_real(client):
    activity = make(client)
    archive(client, activity)
    result = client.delete(f"{ACTIVITIES}/{activity['id']}").json()
    assert result == {"id": activity["id"], "kept_in_history": False}
    assert rows("SELECT 1 FROM activities WHERE id = ?", activity["id"]) == []
    listed = client.get(ACTIVITIES, params={"include_archived": True}).json()["activities"]
    assert activity["id"] not in [item["id"] for item in listed]


def test_an_activity_in_a_report_disappears_but_the_history_stays(client):
    activity = make(client, name="Journaling")
    client.post("/api/v1/reports", json={"day": DAY})
    client.put(f"/api/v1/reports/{DAY}/completions/{activity['id']}", json={"done": True})
    client.post(f"/api/v1/reports/{DAY}/complete")
    archive(client, activity)
    before = client.get(f"/api/v1/reports/{DAY}").json()
    result = client.delete(f"{ACTIVITIES}/{activity['id']}").json()
    assert result == {"id": activity["id"], "kept_in_history": True}
    assert rows("SELECT deleted_at FROM activities WHERE id = ?", activity["id"])[0][0] is not None
    listed = client.get(ACTIVITIES, params={"include_archived": True}).json()["activities"]
    assert activity["id"] not in [item["id"] for item in listed]
    assert client.get(f"/api/v1/reports/{DAY}").json() == before
    stats = client.get("/api/v1/stats/activities", params={"from": DAY, "to": DAY}).json()["activities"]
    assert activity["id"] in [item["activity_id"] for item in stats]


def test_a_deleted_activity_cannot_be_changed_or_deleted_again(client):
    activity = make(client)
    client.post("/api/v1/reports", json={"day": DAY})
    archive(client, activity)
    client.delete(f"{ACTIVITIES}/{activity['id']}")
    assert client.patch(f"{ACTIVITIES}/{activity['id']}", json={"archived": False}).status_code == 404
    assert client.delete(f"{ACTIVITIES}/{activity['id']}").status_code == 404
    assert client.delete(f"{ACTIVITIES}/9999").status_code == 404


def test_the_database_still_refuses_to_delete_an_activity_with_history(client):
    activity = make(client)
    client.post("/api/v1/reports", json={"day": DAY})
    conn = sqlite3.connect(config.db_path())
    try:
        with pytest.raises(sqlite3.DatabaseError, match="never deleted"):
            conn.execute("DELETE FROM activities WHERE id = ?", (activity["id"],))
    finally:
        conn.close()


def test_the_dock_is_the_default_until_it_is_changed(client):
    assert client.get(SETTINGS).json()["dock"] is None


def test_a_dock_is_saved_and_read_back(client):
    keys = ["questionnaire", "home", "calendar:calendar", "more"]
    saved = client.patch(SETTINGS, json={"dock": keys})
    assert saved.status_code == 200
    assert saved.json()["dock"] == keys
    assert client.get(SETTINGS).json()["dock"] == keys


def test_an_empty_dock_goes_back_to_the_default(client):
    client.patch(SETTINGS, json={"dock": ["questionnaire", "more"]})
    reset = client.patch(SETTINGS, json={"dock": []})
    assert reset.status_code == 200
    assert reset.json()["dock"] is None


@pytest.mark.parametrize(
    "keys",
    [
        ["home", "more"],
        ["questionnaire", "more", "home"],
        ["questionnaire", "home", "home", "more"],
        ["questionnaire"] + [f"a{index}" for index in range(7)] + ["more"],
        ["questionnaire", "Bad Key", "more"],
        ["questionnaire", "a:b:c", "more"],
        ["questionnaire", "more", "more"],
    ],
)
def test_an_invalid_dock_is_refused(client, keys):
    assert client.patch(SETTINGS, json={"dock": keys}).status_code == 422
    assert client.get(SETTINGS).json()["dock"] is None


def test_the_dock_holds_at_most_seven_items(client):
    keys = ["home", "stella", "questionnaire", "a:a", "b:b", "c:c", "more"]
    assert client.patch(SETTINGS, json={"dock": keys}).status_code == 200
    assert client.patch(SETTINGS, json={"dock": ["d:d", *keys]}).status_code == 422
    assert client.patch(SETTINGS, json={"dock": None}).status_code == 422
