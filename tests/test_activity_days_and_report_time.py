from datetime import datetime

import pytest

from app import activities, reports
from tests.conftest import EVENING, utc

MONDAY = "2026-10-19"
TUESDAY = "2026-10-20"
THURSDAY = "2026-10-22"
ACTIVITIES = "/api/v1/activities"
SETTINGS = "/api/v1/settings"


def make_activity(client, name, days=None, area="physical"):
    body = {"area": area, "name": name, "weight": 2}
    if days is not None:
        body["days"] = days
    created = client.post(ACTIVITIES, json=body)
    assert created.status_code == 201
    return created.json()["activity"]


def names_in(client, day):
    detail = client.get(f"/api/v1/reports/{day}").json()
    return {item["name"] for item in detail["completions"]}


def clear_samples(client):
    for item in client.get(ACTIVITIES).json()["activities"]:
        client.patch(f"{ACTIVITIES}/{item['id']}", json={"archived": True})


def test_an_activity_is_scheduled_every_day_by_default(client):
    activity = make_activity(client, "Daily habit")
    assert activity["days"] == [0, 1, 2, 3, 4, 5, 6]


def test_days_are_saved_and_can_be_changed(client):
    activity = make_activity(client, "Gym", days=[0, 3, 5])
    assert activity["days"] == [0, 3, 5]
    changed = client.patch(f"{ACTIVITIES}/{activity['id']}", json={"days": [6, 1]})
    assert changed.json()["activity"]["days"] == [1, 6]


@pytest.mark.parametrize("days", [[], [7], [-1], [1, 1], list(range(8))])
def test_invalid_days_are_refused(client, days):
    response = client.post(ACTIVITIES, json={"area": "physical", "name": "X", "weight": 1, "days": days})
    assert response.status_code == 422


def test_a_report_lists_only_the_activities_of_that_weekday(client, clock):
    clear_samples(client)
    make_activity(client, "Gym", days=[0, 3])
    make_activity(client, "Sleep")
    clock.now = utc(2026, 10, 19, 20, 0)
    assert client.post("/api/v1/reports", json={"day": MONDAY}).status_code in (200, 201)
    assert names_in(client, MONDAY) == {"Gym", "Sleep"}
    clock.now = utc(2026, 10, 20, 20, 0)
    assert client.post("/api/v1/reports", json={"day": TUESDAY}).status_code in (200, 201)
    assert names_in(client, TUESDAY) == {"Sleep"}
    clock.now = utc(2026, 10, 22, 20, 0)
    client.post("/api/v1/reports", json={"day": THURSDAY})
    assert names_in(client, THURSDAY) == {"Gym", "Sleep"}


def test_an_area_with_nothing_scheduled_that_day_is_empty_not_zero(client, clock):
    clear_samples(client)
    make_activity(client, "Gym", days=[0])
    make_activity(client, "Reading", days=[0, 1], area="intellect")
    clock.now = utc(2026, 10, 20, 20, 0)
    client.post("/api/v1/reports", json={"day": TUESDAY})
    activity_id = next(i["id"] for i in client.get(ACTIVITIES).json()["activities"] if i["name"] == "Reading")
    client.put(f"/api/v1/reports/{TUESDAY}/completions/{activity_id}", json={"done": True})
    client.post(f"/api/v1/reports/{TUESDAY}/complete")
    scores = {item["area"]: item["score"] for item in client.get(f"/api/v1/reports/{TUESDAY}").json()["scores"]}
    assert scores["physical"] is None
    assert scores["intellect"] == 100.0


def test_syncing_a_draft_follows_the_weekday(client, clock):
    clear_samples(client)
    clock.now = utc(2026, 10, 20, 20, 0)
    client.post("/api/v1/reports", json={"day": TUESDAY})
    make_activity(client, "Gym", days=[0])
    make_activity(client, "Sleep")
    assert client.post(f"/api/v1/reports/{TUESDAY}/sync").status_code == 200
    assert names_in(client, TUESDAY) == {"Sleep"}
    gym = next(i for i in client.get(ACTIVITIES).json()["activities"] if i["name"] == "Gym")
    client.patch(f"{ACTIVITIES}/{gym['id']}", json={"days": [1]})
    client.post(f"/api/v1/reports/{TUESDAY}/sync")
    assert names_in(client, TUESDAY) == {"Gym", "Sleep"}


def test_a_past_report_keeps_what_it_had_when_the_days_change(client, clock):
    clear_samples(client)
    gym = make_activity(client, "Gym", days=[1])
    clock.now = utc(2026, 10, 20, 20, 0)
    client.post("/api/v1/reports", json={"day": TUESDAY})
    client.post(f"/api/v1/reports/{TUESDAY}/complete")
    client.patch(f"{ACTIVITIES}/{gym['id']}", json={"days": [0]})
    assert names_in(client, TUESDAY) == {"Gym"}


def lock(client, time_text="20:00"):
    saved = client.patch(SETTINGS, json={"report_lock": True, "report_time": time_text})
    assert saved.status_code == 200
    return saved.json()


def test_the_lock_is_off_by_default_and_validated(client):
    settings = client.get(SETTINGS).json()
    assert (settings["report_lock"], settings["report_time"]) == (False, "20:00")
    assert client.patch(SETTINGS, json={"report_time": "25:00"}).status_code == 422
    assert client.patch(SETTINGS, json={"report_time": "8pm"}).status_code == 422
    assert client.patch(SETTINGS, json={"report_lock": None}).status_code == 422


def test_before_the_time_today_s_report_cannot_be_opened_or_changed(client, clock):
    lock(client, "22:30")
    clock.now = utc(2026, 10, 20, 15, 0)
    today = client.get("/api/v1/today").json()
    assert today == {"day": "2026-10-20", "report_opens_at": "22:30", "first_day": None}
    refused = client.post("/api/v1/reports", json={"day": TUESDAY})
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "report_not_open")
    assert "22:30" in refused.json()["error"]["message"]


def test_after_the_time_the_report_works_normally(client, clock):
    lock(client, "20:00")
    clock.now = utc(2026, 10, 20, 17, 59)
    assert client.post("/api/v1/reports", json={"day": TUESDAY}).status_code == 409
    clock.now = utc(2026, 10, 20, 18, 0)
    assert client.post("/api/v1/reports", json={"day": TUESDAY}).status_code in (200, 201)
    assert client.get("/api/v1/today").json()["report_opens_at"] is None


def test_an_existing_draft_cannot_be_ticked_before_the_time(client, clock):
    clock.now = utc(2026, 10, 20, 12, 0)
    client.post("/api/v1/reports", json={"day": TUESDAY})
    first = client.get(ACTIVITIES).json()["activities"][0]
    lock(client, "20:00")
    refused = client.put(f"/api/v1/reports/{TUESDAY}/completions/{first['id']}", json={"done": True})
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "report_not_open")
    assert client.put(f"/api/v1/reports/{TUESDAY}/reflection", json={"text": "x"}).status_code == 409
    assert client.post(f"/api/v1/reports/{TUESDAY}/complete").status_code == 409
    assert client.get(f"/api/v1/reports/{TUESDAY}").status_code == 200


def test_yesterday_stays_editable_and_early_morning_counts_as_after_the_time(client, clock):
    lock(client, "20:00")
    clock.now = utc(2026, 10, 20, 20, 0)
    client.post("/api/v1/reports", json={"day": TUESDAY})
    clock.now = utc(2026, 10, 21, 8, 0)
    first = client.get(ACTIVITIES).json()["activities"][0]
    assert client.get("/api/v1/today").json() == {"day": "2026-10-21", "report_opens_at": "20:00", "first_day": None}
    done = client.put(f"/api/v1/reports/{TUESDAY}/completions/{first['id']}", json={"done": True})
    assert done.status_code == 200
    clock.now = utc(2026, 10, 21, 1, 0)
    assert client.get("/api/v1/today").json()["day"] == "2026-10-20"
    assert client.get("/api/v1/today").json()["report_opens_at"] is None


def test_turning_the_lock_off_or_moving_the_time_opens_the_report(client, clock):
    lock(client, "22:00")
    clock.now = utc(2026, 10, 20, 15, 0)
    assert client.post("/api/v1/reports", json={"day": TUESDAY}).status_code == 409
    client.patch(SETTINGS, json={"report_time": "14:00"})
    assert client.post("/api/v1/reports", json={"day": TUESDAY}).status_code in (200, 201)
    client.patch(SETTINGS, json={"report_time": "23:00"})
    assert client.get("/api/v1/today").json()["report_opens_at"] == "23:00"
    client.patch(SETTINGS, json={"report_lock": False})
    assert client.get("/api/v1/today").json()["report_opens_at"] is None


def test_the_time_is_read_in_the_configured_timezone(client, clock):
    client.patch(SETTINGS, json={"timezone": "UTC", "day_cutoff": "00:00"})
    lock(client, "20:00")
    clock.now = utc(2026, 10, 20, 19, 0)
    assert client.post("/api/v1/reports", json={"day": TUESDAY}).status_code == 409
    clock.now = utc(2026, 10, 20, 20, 5)
    assert client.post("/api/v1/reports", json={"day": TUESDAY}).status_code in (200, 201)


def test_the_core_helpers_agree_with_the_api(conn, user_id, rules):
    activities.create(conn, "physical", "Gym", 2, EVENING, days=[1])
    report_id = reports.open_report(conn, user_id, datetime(2026, 10, 20).date(), EVENING, rules)
    names = {row["name_at_time"] for row in conn.execute("SELECT name_at_time FROM completions WHERE report_id = ?", (report_id,))}
    assert names == {"Gym"}
    assert activities.mask_to_days(activities.days_to_mask([0, 2, 6])) == [0, 2, 6]
