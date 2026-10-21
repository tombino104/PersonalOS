import pytest

ACTIVITIES = "/api/v1/activities"
DAY = "2026-10-20"


def make(client, **extra):
    body = {"area": "physical", "name": "Stretch", "weight": 1, **extra}
    created = client.post(ACTIVITIES, json=body)
    assert created.status_code == 201
    return created.json()["activity"]


def test_an_activity_has_no_description_by_default(client):
    assert make(client)["description"] is None


def test_a_description_is_saved_trimmed_and_changed(client):
    activity = make(client, description="  Ten minutes after waking up  ")
    assert activity["description"] == "Ten minutes after waking up"
    changed = client.patch(f"{ACTIVITIES}/{activity['id']}", json={"description": "Hips and back"})
    assert changed.json()["activity"]["description"] == "Hips and back"


def test_an_empty_description_clears_it(client):
    activity = make(client, description="Something")
    cleared = client.patch(f"{ACTIVITIES}/{activity['id']}", json={"description": "   "})
    assert cleared.status_code == 200
    assert cleared.json()["activity"]["description"] is None


def test_a_description_that_is_too_long_is_refused(client):
    response = client.post(ACTIVITIES, json={"area": "physical", "name": "X", "weight": 1, "description": "a" * 301})
    assert response.status_code == 422


@pytest.mark.parametrize("value", [None, 5])
def test_a_description_must_be_text(client, value):
    activity = make(client)
    assert client.patch(f"{ACTIVITIES}/{activity['id']}", json={"description": value}).status_code == 422


def test_the_report_shows_the_current_description(client):
    activity = make(client, description="First version")
    client.post("/api/v1/reports", json={"day": DAY})
    client.patch(f"{ACTIVITIES}/{activity['id']}", json={"description": "Second version"})
    detail = client.get(f"/api/v1/reports/{DAY}").json()
    item = next(entry for entry in detail["completions"] if entry["activity_id"] == activity["id"])
    assert item["description"] == "Second version"
