from tests.conftest import utc

REVIEWS = "/api/v1/reviews"
MONDAY = "2026-10-19"
PREVIOUS = "2026-10-12"


def record(client, clock, day, hour_day, ticks=None, reflection=None):
    clock.now = utc(2026, 10, hour_day, 20, 0)
    client.post("/api/v1/reports", json={"day": day})
    for activity_id in ticks or []:
        client.put(f"/api/v1/reports/{day}/completions/{activity_id}", json={"done": True})
    if reflection:
        client.put(f"/api/v1/reports/{day}/reflection", json={"text": reflection})
    client.post(f"/api/v1/reports/{day}/complete")


def first_ids(client, count):
    detail = client.get("/api/v1/activities").json()["activities"]
    return [item["id"] for item in detail][:count]


def test_a_week_with_nothing_is_empty_not_zero(client, clock):
    clock.now = utc(2026, 10, 22, 12, 0)
    week = client.get(f"{REVIEWS}/{MONDAY}").json()
    assert week["filled_days"] == 0
    assert all(item["average"] is None for item in week["areas"])
    assert [day["day"] for day in week["days"]][0] == MONDAY
    assert len(week["days"]) == 7
    assert week["is_current"] is True
    assert week["note"] is None and week["activities"] == []


def test_the_summary_shows_days_areas_activities_and_reflections(client, clock):
    ids = first_ids(client, 2)
    record(client, clock, "2026-10-19", 19, ticks=ids, reflection="A calm start")
    record(client, clock, "2026-10-20", 20)
    clock.now = utc(2026, 10, 22, 12, 0)
    week = client.get(f"{REVIEWS}/{MONDAY}").json()
    assert week["filled_days"] == 2
    monday = week["days"][0]
    assert (monday["completed"], monday["reflection"]) == (True, "A calm start")
    assert monday["overall"] is not None
    assert week["days"][2]["completed"] is False and week["days"][2]["overall"] is None
    physical = next(item for item in week["areas"] if item["area"] == "physical")
    assert physical["average"] is not None and physical["previous"] is None
    assert week["activities"] and {"activity_id", "done", "total", "name"} <= set(week["activities"][0])


def test_the_previous_week_is_there_for_comparison(client, clock):
    ids = first_ids(client, 3)
    record(client, clock, "2026-10-12", 12, ticks=ids)
    record(client, clock, "2026-10-19", 19, ticks=ids[:1])
    clock.now = utc(2026, 10, 22, 12, 0)
    week = client.get(f"{REVIEWS}/{MONDAY}").json()
    assert week["previous_filled_days"] == 1
    physical = next(item for item in week["areas"] if item["area"] == "physical")
    assert physical["previous"] is not None


def test_a_note_is_saved_trimmed_and_removed(client, clock):
    clock.now = utc(2026, 10, 22, 12, 0)
    saved = client.put(f"{REVIEWS}/{MONDAY}/note", json={"text": "  Keep the mornings  "})
    assert saved.json() == {"note": "Keep the mornings"}
    assert client.get(f"{REVIEWS}/{MONDAY}").json()["note"] == "Keep the mornings"
    assert client.get(f"{REVIEWS}/{PREVIOUS}").json()["note"] is None
    client.put(f"{REVIEWS}/{MONDAY}/note", json={"text": "Changed"})
    assert client.get(f"{REVIEWS}/{MONDAY}").json()["note"] == "Changed"
    assert client.put(f"{REVIEWS}/{MONDAY}/note", json={"text": "  "}).json() == {"note": None}
    assert client.get(f"{REVIEWS}/{MONDAY}").json()["note"] is None


def test_the_week_must_start_on_a_monday_and_not_in_the_future(client, clock):
    clock.now = utc(2026, 10, 22, 12, 0)
    refused = client.get(f"{REVIEWS}/2026-10-20")
    assert (refused.status_code, refused.json()["error"]["code"]) == (422, "invalid_week")
    future = client.get(f"{REVIEWS}/2026-10-26")
    assert (future.status_code, future.json()["error"]["code"]) == (422, "future_week")
    assert client.put(f"{REVIEWS}/2026-10-26/note", json={"text": "x"}).status_code == 422
    assert client.put(f"{REVIEWS}/{MONDAY}/note", json={"text": "x" * 5001}).status_code == 422


def test_a_past_week_is_not_current(client, clock):
    clock.now = utc(2026, 10, 22, 12, 0)
    assert client.get(f"{REVIEWS}/{PREVIOUS}").json()["is_current"] is False
