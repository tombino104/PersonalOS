import pytest

from app.scoring import Item, tally, weekly_forced
from tests.conftest import utc

ACTIVITIES = "/api/v1/activities"
MONDAY = "2026-10-19"
DAYS = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24", "2026-10-25"]


def clear_samples(client):
    for item in client.get(ACTIVITIES).json()["activities"]:
        client.patch(f"{ACTIVITIES}/{item['id']}", json={"archived": True})


def make(client, times=3, **extra):
    created = client.post(
        ACTIVITIES, json={"area": "physical", "name": "Gym", "weight": 2, "times_per_week": times, **extra}
    )
    assert created.status_code == 201
    return created.json()["activity"]


def record(client, clock, day, activity_id, done):
    index = DAYS.index(day)
    clock.now = utc(2026, 10, 19 + index, 20, 0)
    assert client.post("/api/v1/reports", json={"day": day}).status_code in (200, 201)
    client.put(f"/api/v1/reports/{day}/completions/{activity_id}", json={"done": done})
    return client.post(f"/api/v1/reports/{day}/complete").json()


def physical(report):
    return next(entry for entry in report["scores"] if entry["area"] == "physical")


def test_the_pure_rules():
    assert weekly_forced(3, 0, 7) is False
    assert weekly_forced(3, 0, 3) is True
    assert weekly_forced(3, 2, 2) is False
    assert weekly_forced(3, 2, 1) is True
    assert weekly_forced(1, 1, 1) is False
    assert tally([Item(2, False, optional=True), Item(3, True, optional=True), Item(1, False)]) == (4, 3)


def test_the_target_is_saved_changed_and_cleared(client):
    activity = make(client, times=3)
    assert activity["times_per_week"] == 3
    changed = client.patch(f"{ACTIVITIES}/{activity['id']}", json={"times_per_week": 5})
    assert changed.json()["activity"]["times_per_week"] == 5
    cleared = client.patch(f"{ACTIVITIES}/{activity['id']}", json={"times_per_week": 0})
    assert cleared.json()["activity"]["times_per_week"] is None
    assert make(client, times=0)["times_per_week"] is None


@pytest.mark.parametrize("value", [8, -1, 2.5])
def test_a_bad_target_is_refused(client, value):
    response = client.post(ACTIVITIES, json={"area": "physical", "name": "X", "weight": 1, "times_per_week": value})
    assert response.status_code == 422


def test_skipping_early_in_the_week_is_free(client, clock):
    clear_samples(client)
    gym = make(client, times=3)
    report = record(client, clock, "2026-10-19", gym["id"], done=False)
    assert physical(report)["maximum"] == 0
    assert physical(report)["score"] is None
    assert report["overall"] is None


def test_a_day_that_is_done_always_counts(client, clock):
    clear_samples(client)
    gym = make(client, times=3)
    report = record(client, clock, "2026-10-19", gym["id"], done=True)
    assert (physical(report)["maximum"], physical(report)["obtained"]) == (2, 2)


def test_it_counts_against_you_only_when_the_target_can_no_longer_be_met(client, clock):
    clear_samples(client)
    gym = make(client, times=3)
    for day in DAYS[:4]:
        assert physical(record(client, clock, day, gym["id"], done=False))["maximum"] == 0
    friday = record(client, clock, "2026-10-23", gym["id"], done=False)
    assert (physical(friday)["maximum"], physical(friday)["obtained"]) == (2, 0)
    assert physical(friday)["score"] == 0.0


def test_progress_is_reported_in_the_report(client, clock):
    clear_samples(client)
    gym = make(client, times=3)
    record(client, clock, "2026-10-19", gym["id"], done=True)
    record(client, clock, "2026-10-20", gym["id"], done=False)
    clock.now = utc(2026, 10, 21, 20, 0)
    wednesday = client.post("/api/v1/reports", json={"day": "2026-10-21"}).json()
    assert wednesday["completions"][0]["weekly"] == {"target": 3, "done_before": 1, "forced": False}


def test_a_week_without_a_target_is_unchanged(client, clock):
    clear_samples(client)
    plain = client.post(ACTIVITIES, json={"area": "physical", "name": "Walk", "weight": 2}).json()["activity"]
    report = record(client, clock, "2026-10-19", plain["id"], done=False)
    assert (physical(report)["maximum"], physical(report)["score"]) == (2, 0.0)
    assert client.get("/api/v1/reports/2026-10-19").json()["completions"][0]["weekly"] is None


def test_the_target_is_a_snapshot_of_the_day_it_was_recorded(client, clock):
    clear_samples(client)
    gym = make(client, times=3)
    first = record(client, clock, "2026-10-19", gym["id"], done=False)
    client.patch(f"{ACTIVITIES}/{gym['id']}", json={"times_per_week": 0})
    assert client.get("/api/v1/reports/2026-10-19").json()["scores"] == first["scores"]
    assert client.get("/api/v1/reports/2026-10-19").json()["completions"][0]["weekly"]["target"] == 3


def test_editing_an_earlier_day_rescores_the_later_days_of_the_week(client, clock):
    clear_samples(client)
    gym = make(client, times=2, days=[0, 1, 2])
    record(client, clock, "2026-10-19", gym["id"], done=False)
    tuesday = record(client, clock, "2026-10-20", gym["id"], done=False)
    assert (physical(tuesday)["maximum"], physical(tuesday)["obtained"]) == (2, 0)
    clock.now = utc(2026, 10, 20, 21, 0)
    client.put(f"/api/v1/reports/2026-10-19/completions/{gym['id']}", json={"done": True})
    assert physical(client.get("/api/v1/reports/2026-10-20").json())["maximum"] == 0


def test_weekly_days_are_respected(client, clock):
    clear_samples(client)
    gym = make(client, times=2, days=[0, 1, 2])
    assert physical(record(client, clock, "2026-10-19", gym["id"], done=False))["maximum"] == 0
    assert physical(record(client, clock, "2026-10-20", gym["id"], done=False))["maximum"] == 2
    clock.now = utc(2026, 10, 22, 20, 0)
    thursday = client.post("/api/v1/reports", json={"day": "2026-10-22"}).json()
    assert thursday["completions"] == []
