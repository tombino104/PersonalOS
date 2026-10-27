from datetime import datetime, timezone

import pytest

from app import db
from tests.conftest import USER

DAY = "2026-10-20"


def activity_ids(client, area=None):
    items = client.get("/api/v1/activities").json()["activities"]
    return [a["id"] for a in items if area is None or a["area"] == area]


def open_day(client, day=DAY):
    response = client.post("/api/v1/reports", json={"day": day})
    assert response.status_code in (200, 201), response.text
    return response.json()


def test_info(client):
    assert client.get("/api/v1/info").json()["api"] == "1"


def test_areas_are_the_six_fixed_ones(client):
    areas = client.get("/api/v1/areas").json()["areas"]
    assert [a["slug"] for a in areas] == [
        "physical", "discipline", "social", "intellect", "career", "mindset",
    ]


def test_activities_list_and_create(client):
    created = client.post(
        "/api/v1/activities", json={"area": "mindset", "name": "  Stretch  ", "weight": 2}
    )
    assert created.status_code == 201
    activity = created.json()["activity"]
    assert activity["name"] == "Stretch" and activity["area"] == "mindset"
    assert activity["id"] in activity_ids(client, "mindset")


@pytest.mark.parametrize(
    "payload",
    [
        {"area": "mindset", "name": "x", "weight": 4},
        {"area": "mindset", "name": "", "weight": 1},
        {"area": "mindset", "name": "x"},
        {"area": "mindset", "name": "x", "weight": 1, "extra": 1},
    ],
)
def test_create_validation_uses_uniform_error_format(client, payload):
    response = client.post("/api/v1/activities", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_in_unknown_area_is_rejected(client):
    response = client.post("/api/v1/activities", json={"area": "nope", "name": "x", "weight": 1})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_area"


def test_update_rename_reweight_move_archive_unarchive(client):
    activity_id = activity_ids(client, "physical")[0]
    url = f"/api/v1/activities/{activity_id}"
    updated = client.patch(url, json={"name": "Renamed", "weight": 1, "area": "career"})
    assert updated.status_code == 200
    body = updated.json()["activity"]
    assert (body["name"], body["weight"], body["area"]) == ("Renamed", 1, "career")

    archived = client.patch(url, json={"archived": True}).json()["activity"]
    assert archived["archived_at"] is not None
    assert activity_id not in activity_ids(client)
    listed = client.get("/api/v1/activities", params={"include_archived": True}).json()
    assert activity_id in [a["id"] for a in listed["activities"]]

    restored = client.patch(url, json={"archived": False}).json()["activity"]
    assert restored["archived_at"] is None
    assert activity_id in activity_ids(client)


def test_update_unknown_activity_and_null_fields(client):
    assert client.patch("/api/v1/activities/9999", json={"name": "x"}).status_code == 404
    activity_id = activity_ids(client)[0]
    response = client.patch(f"/api/v1/activities/{activity_id}", json={"name": None})
    assert response.status_code == 422


def test_an_active_activity_cannot_be_deleted(client):
    activity_id = activity_ids(client)[0]
    response = client.delete(f"/api/v1/activities/{activity_id}")
    assert (response.status_code, response.json()["error"]["code"]) == (409, "activity_not_archived")


def test_warning_when_an_area_has_more_than_five_activities(client):
    assert client.get("/api/v1/activities").json()["warnings"] == []
    for index in range(2):
        response = client.post(
            "/api/v1/activities", json={"area": "physical", "name": f"Extra {index}", "weight": 1}
        )
    warning = response.json()["warnings"][0]
    assert warning["code"] == "too_many_activities"
    assert warning["area"] == "physical" and warning["count"] == 6


def test_open_report_creates_then_reuses(client):
    first = client.post("/api/v1/reports", json={"day": DAY})
    second = client.post("/api/v1/reports", json={"day": DAY})
    assert (first.status_code, second.status_code) == (201, 200)
    body = first.json()
    assert body["status"] == "open" and body["editable"] is True
    assert body["completed"] is False and body["scores"] is None
    assert len(body["completions"]) == len(activity_ids(client))


def test_missing_report_is_404_and_empty_days_are_absent(client):
    response = client.get(f"/api/v1/reports/{DAY}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert client.get("/api/v1/reports").json() == {"reports": []}
    assert client.get("/api/v1/scores").json() == {"days": []}


def test_future_and_expired_days_are_refused(client):
    future = client.post("/api/v1/reports", json={"day": "2026-10-25"})
    assert (future.status_code, future.json()["error"]["code"]) == (422, "future_day")
    old = client.post("/api/v1/reports", json={"day": "2026-10-10"})
    assert (old.status_code, old.json()["error"]["code"]) == (409, "report_closed")


def test_bad_date_is_a_validation_error(client):
    response = client.get("/api/v1/reports/not-a-date")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_full_evening_flow_with_scores(client):
    report = open_day(client)
    physical = [c for c in report["completions"] if c["area"] == "physical"]
    for completion in physical:
        response = client.put(
            f"/api/v1/reports/{DAY}/completions/{completion['activity_id']}", json={"done": True}
        )
        assert response.status_code == 200
    client.put(f"/api/v1/reports/{DAY}/reflection", json={"text": "A calm day."})

    draft = client.get(f"/api/v1/reports/{DAY}").json()
    assert draft["scores"] is None and draft["reflection"] == "A calm day."
    assert client.get("/api/v1/scores").json() == {"days": []}

    done = client.post(f"/api/v1/reports/{DAY}/complete")
    assert done.status_code == 200
    scores = {s["area"]: s for s in done.json()["scores"]}
    assert scores["physical"]["score"] == 100.0
    assert scores["social"]["score"] == 0.0

    days = client.get("/api/v1/scores", params={"from": DAY, "to": DAY}).json()["days"]
    assert [d["day"] for d in days] == [DAY]
    listing = client.get("/api/v1/reports").json()["reports"]
    assert listing[0]["day"] == DAY and listing[0]["completed"] is True


def test_area_without_activities_has_null_score(client):
    for activity_id in activity_ids(client, "mindset"):
        client.patch(f"/api/v1/activities/{activity_id}", json={"archived": True})
    open_day(client)
    scores = client.post(f"/api/v1/reports/{DAY}/complete").json()["scores"]
    mindset = next(s for s in scores if s["area"] == "mindset")
    assert mindset == {"area": "mindset", "maximum": 0, "obtained": 0, "score": None}


def test_set_completion_for_unknown_activity_is_404(client):
    open_day(client)
    response = client.put(f"/api/v1/reports/{DAY}/completions/9999", json={"done": True})
    assert response.status_code == 404


def test_changing_activities_after_completion_does_not_change_the_report(client):
    open_day(client)
    client.post(f"/api/v1/reports/{DAY}/complete")
    before = client.get(f"/api/v1/reports/{DAY}").json()
    for activity_id in activity_ids(client):
        client.patch(f"/api/v1/activities/{activity_id}", json={"name": "Changed", "weight": 3})
    client.post("/api/v1/activities", json={"area": "career", "name": "New", "weight": 3})
    assert client.get(f"/api/v1/reports/{DAY}").json() == before


def test_sync_brings_a_draft_up_to_date_and_keeps_ticks(client):
    report = open_day(client)
    kept = report["completions"][0]
    client.put(f"/api/v1/reports/{DAY}/completions/{kept['activity_id']}", json={"done": True})
    added = client.post(
        "/api/v1/activities", json={"area": "career", "name": "Added late", "weight": 2}
    ).json()["activity"]
    removed = report["completions"][-1]["activity_id"]
    client.patch(f"/api/v1/activities/{removed}", json={"archived": True})
    client.patch(f"/api/v1/activities/{kept['activity_id']}", json={"name": "Renamed"})

    assert added["id"] not in [c["activity_id"] for c in client.get(f"/api/v1/reports/{DAY}").json()["completions"]]
    synced = client.post(f"/api/v1/reports/{DAY}/sync")
    assert synced.status_code == 200
    items = {c["activity_id"]: c for c in synced.json()["completions"]}
    assert added["id"] in items and removed not in items
    assert items[kept["activity_id"]]["name"] == "Renamed"
    assert items[kept["activity_id"]]["done"] is True


def test_sync_updates_a_completed_report_and_its_scores(client):
    report = open_day(client)
    first = report["completions"][0]
    client.put(f"/api/v1/reports/{DAY}/completions/{first['activity_id']}", json={"done": True})
    before = client.post(f"/api/v1/reports/{DAY}/complete").json()
    client.patch(f"/api/v1/activities/{first['activity_id']}", json={"weight": 3, "name": "Renamed"})
    client.post("/api/v1/activities", json={"area": "mindset", "name": "Late", "weight": 3})
    synced = client.post(f"/api/v1/reports/{DAY}/sync")
    assert synced.status_code == 200
    after = client.get(f"/api/v1/reports/{DAY}").json()
    assert after["completed"] is True
    names = {item["name"]: item for item in after["completions"]}
    assert names["Renamed"]["done"] is True and names["Late"]["done"] is False
    mindset_before = next(s for s in before["scores"] if s["area"] == "mindset")
    mindset_after = next(s for s in after["scores"] if s["area"] == "mindset")
    assert mindset_after["maximum"] == mindset_before["maximum"] + 3


def test_yesterday_stays_editable_until_the_deadline(client, clock):
    report = open_day(client)
    activity_id = report["completions"][0]["activity_id"]
    client.post(f"/api/v1/reports/{DAY}/complete")

    clock.now = datetime(2026, 10, 21, 20, 0, tzinfo=timezone.utc)
    ok = client.put(f"/api/v1/reports/{DAY}/completions/{activity_id}", json={"done": True})
    assert ok.status_code == 200

    clock.now = datetime(2026, 10, 22, 2, 0, tzinfo=timezone.utc)
    locked = client.put(f"/api/v1/reports/{DAY}/completions/{activity_id}", json={"done": False})
    assert (locked.status_code, locked.json()["error"]["code"]) == (409, "report_closed")
    detail = client.get(f"/api/v1/reports/{DAY}").json()
    assert detail["status"] == "closed" and detail["editable"] is False
    reflection = client.put(f"/api/v1/reports/{DAY}/reflection", json={"text": "late"})
    assert reflection.status_code == 409


def test_range_validation(client):
    reversed_range = client.get("/api/v1/scores", params={"from": "2026-10-20", "to": "2026-10-01"})
    assert reversed_range.status_code == 422
    assert reversed_range.json()["error"]["code"] == "invalid_range"
    too_long = client.get("/api/v1/reports", params={"from": "2025-01-01", "to": "2026-10-20"})
    assert too_long.status_code == 422


def test_settings_roundtrip_and_validation(client):
    assert client.get("/api/v1/settings").json() == {
        "timezone": "Europe/Rome",
        "day_cutoff": "04:00",
        "backup_auto": True,
        "backup_time": "03:00",
        "report_lock": False,
        "report_time": "20:00",
        "reminder_enabled": False,
        "reminder_time": "21:00",
        "home_period": "week",
        "home_areas": "all",
        "theme": None,
        "language": None,
        "dock": None,
    }
    bad_zone = client.patch("/api/v1/settings", json={"timezone": "Mars/Base"})
    assert (bad_zone.status_code, bad_zone.json()["error"]["code"]) == (422, "invalid_timezone")
    bad_time = client.patch("/api/v1/settings", json={"day_cutoff": "25:99"})
    assert (bad_time.status_code, bad_time.json()["error"]["code"]) == (422, "invalid_day_cutoff")
    assert client.patch("/api/v1/settings", json={"day_cutoff": "4am"}).status_code == 422
    assert client.get("/api/v1/settings").json()["timezone"] == "Europe/Rome"


def test_theme_and_language_are_kept_on_the_server(client):
    saved = client.patch("/api/v1/settings", json={"theme": "dark", "language": "it"})
    assert (saved.json()["theme"], saved.json()["language"]) == ("dark", "it")
    assert client.get("/api/v1/settings").json()["theme"] == "dark"
    assert client.patch("/api/v1/settings", json={"theme": "purple"}).status_code == 422
    assert client.patch("/api/v1/settings", json={"language": "fr"}).status_code == 422
    assert client.patch("/api/v1/settings", json={"theme": None}).status_code == 422
    assert client.get("/api/v1/settings").json()["language"] == "it"


def test_the_home_view_is_remembered(client):
    saved = client.patch("/api/v1/settings", json={"home_period": "month", "home_areas": "second"})
    assert (saved.json()["home_period"], saved.json()["home_areas"]) == ("month", "second")
    assert client.get("/api/v1/settings").json()["home_areas"] == "second"
    assert client.patch("/api/v1/settings", json={"home_areas": "third"}).status_code == 422
    assert client.patch("/api/v1/settings", json={"home_period": "year"}).status_code == 422


def test_settings_change_applies_to_new_reports_only(client, clock):
    clock.now = datetime(2026, 10, 20, 1, 30, tzinfo=timezone.utc)
    assert client.post("/api/v1/reports", json={"day": DAY}).status_code == 422
    updated = client.patch("/api/v1/settings", json={"timezone": "UTC", "day_cutoff": "00:00"})
    assert (updated.json()["timezone"], updated.json()["day_cutoff"]) == ("UTC", "00:00")
    assert client.post("/api/v1/reports", json={"day": DAY}).status_code == 201
    stored = client.get(f"/api/v1/reports/{DAY}").json()["editable_until"]
    assert stored.startswith("2026-10-22T00:00")


def test_reports_belong_to_the_logged_in_user(client, tmp_path):
    open_day(client)
    conn = db.connect(tmp_path / "personal_os.db")
    owner = conn.execute(
        "SELECT user_id, name FROM reports r JOIN users u ON u.id = r.user_id"
    ).fetchone()
    conn.close()
    assert owner["name"] == USER


def test_today_follows_the_day_cutoff(client, clock):
    assert client.get("/api/v1/today").json() == {"day": "2026-10-20", "report_opens_at": None, "first_day": None}
    clock.now = datetime(2026, 10, 21, 1, 30, tzinfo=timezone.utc)
    assert client.get("/api/v1/today").json() == {"day": "2026-10-20", "report_opens_at": None, "first_day": None}
    clock.now = datetime(2026, 10, 21, 2, 0, tzinfo=timezone.utc)
    assert client.get("/api/v1/today").json() == {"day": "2026-10-21", "report_opens_at": None, "first_day": None}


def test_overall_and_stats_over_the_api(client):
    report = open_day(client)
    physical = [c for c in report["completions"] if c["area"] == "physical"]
    for completion in physical:
        client.put(f"/api/v1/reports/{DAY}/completions/{completion['activity_id']}", json={"done": True})
    done = client.post(f"/api/v1/reports/{DAY}/complete").json()
    assert done["overall"] == pytest.approx(100 / 6)

    days = client.get("/api/v1/scores", params={"from": DAY, "to": DAY}).json()["days"]
    assert days[0]["overall"] == pytest.approx(100 / 6)

    averages = client.get("/api/v1/stats/areas", params={"from": DAY, "to": DAY}).json()
    assert averages["filled_days"] == 1
    assert averages["areas"][0] == {"area": "physical", "average": 100.0}

    stats = client.get("/api/v1/stats/activities", params={"from": DAY, "to": DAY}).json()["activities"]
    assert len(stats) == len(report["completions"])
    first = stats[0]
    assert (first["done"], first["total"]) == (1, 1)


def test_stats_validate_the_range(client):
    for path in ("/api/v1/stats/areas", "/api/v1/stats/activities"):
        response = client.get(path, params={"from": "2026-10-20", "to": "2026-10-01"})
        assert (response.status_code, response.json()["error"]["code"]) == (422, "invalid_range")


def test_today_reports_the_first_completed_day_and_stats_cover_years(client, clock):
    clock.now = datetime(2026, 10, 20, 20, 0, tzinfo=timezone.utc)
    client.post("/api/v1/reports", json={"day": "2026-10-20"})
    client.post("/api/v1/reports/2026-10-20/complete")
    assert client.get("/api/v1/today").json()["first_day"] == "2026-10-20"
    assert client.get("/api/v1/stats/areas", params={"from": "2022-01-01", "to": "2026-10-20"}).status_code == 200
    assert client.get("/api/v1/stats/activities", params={"from": "2022-01-01", "to": "2026-10-20"}).status_code == 200
    assert client.get("/api/v1/scores", params={"from": "2022-01-01", "to": "2026-10-20"}).status_code == 422
