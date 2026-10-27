import shutil
from pathlib import Path

import pytest

from tests.plugin_site import DAY, Site, activate

HEALTH = "/api/v1/plugins/health"
INGEST = "/api/v1/ingest/health"
SOURCE = Path(__file__).resolve().parent.parent / "plugins" / "health"


@pytest.fixture
def health(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "health")
    with site.running() as client:
        assert activate(client, "health").status_code == 200
        yield client, site


def make_token(client, name="iPhone"):
    response = client.post("/api/v1/tokens", json={"name": name, "plugin": "health"})
    assert response.status_code == 201, response.text
    return response.json()


def send(client, payload, secret, **kwargs):
    headers = {"Authorization": f"Bearer {secret}"}
    return client.post(INGEST, json=payload, headers=headers, **kwargs)


def stored(client):
    return {item["day"]: item["steps"] for item in client.get(f"{HEALTH}/days").json()["days"]}


def test_the_manifest_is_valid_and_it_is_off_until_turned_on(tmp_path, monkeypatch, clock):
    site = Site(tmp_path, monkeypatch, clock)
    shutil.copytree(SOURCE, site.plugins / "health")
    with site.running() as client:
        item = next(p for p in client.get("/api/v1/plugins").json()["plugins"] if p["id"] == "health")
        assert item["state"] == "inactive"
        assert item["permissions"] == ["api_routes", "ingest", "ui_panel"]


def test_a_token_is_shown_once_and_never_listed_again(health):
    client, site = health
    created = make_token(client)
    assert created["token"].startswith("pos_") and created["plugin"] == "health"
    listing = client.get("/api/v1/tokens", params={"plugin": "health"}).json()["tokens"]
    assert [item["name"] for item in listing] == ["iPhone"]
    assert "token" not in listing[0] and "token_hash" not in listing[0]
    assert created["token"] not in str(site.rows("SELECT * FROM api_tokens"))


def test_a_token_needs_a_plugin_that_accepts_data(health):
    client, _ = health
    assert client.post("/api/v1/tokens", json={"name": "x", "plugin": "nothing"}).status_code == 422
    assert client.post("/api/v1/tokens", json={"name": "  ", "plugin": "health"}).status_code == 422


def test_there_is_a_limit_to_active_tokens(health):
    client, _ = health
    for index in range(20):
        make_token(client, f"phone {index}")
    assert client.post("/api/v1/tokens", json={"name": "one more", "plugin": "health"}).status_code == 409


def test_steps_are_stored_with_a_valid_token(health):
    client, _ = health
    secret = make_token(client)["token"]
    assert send(client, {"day": "2026-10-19", "steps": 8421}, secret).json() == {"ok": True}
    assert stored(client) == {"2026-10-19": 8421}


def test_the_day_defaults_to_today_and_the_key_header_works(health):
    client, _ = health
    secret = make_token(client)["token"]
    response = client.post(INGEST, json={"steps": 1200}, headers={"X-Api-Key": secret})
    assert response.status_code == 200
    assert stored(client) == {DAY: 1200}


def test_no_token_and_a_session_alone_are_refused(health):
    client, _ = health
    assert client.post(INGEST, json={"steps": 10}).status_code == 401
    assert send(client, {"steps": 10}, "pos_wrong").status_code == 401
    assert stored(client) == {}


def test_a_revoked_token_stops_working(health):
    client, _ = health
    created = make_token(client)
    assert send(client, {"steps": 10}, created["token"]).status_code == 200
    assert client.delete(f"/api/v1/tokens/{created['id']}").status_code == 200
    assert send(client, {"steps": 20}, created["token"]).status_code == 401
    assert client.delete(f"/api/v1/tokens/{created['id']}").status_code == 404
    assert client.get("/api/v1/tokens").json()["tokens"] == []


def test_a_token_only_works_for_its_own_plugin(health):
    client, _ = health
    secret = make_token(client)["token"]
    response = client.post("/api/v1/ingest/journal", json={"steps": 10}, headers={"Authorization": f"Bearer {secret}"})
    assert response.status_code == 401


def test_using_a_token_records_when(health):
    client, _ = health
    secret = make_token(client)["token"]
    assert client.get("/api/v1/tokens").json()["tokens"][0]["last_used_at"] is None
    send(client, {"steps": 10}, secret)
    assert client.get("/api/v1/tokens").json()["tokens"][0]["last_used_at"] is not None


def test_a_day_keeps_the_highest_count_it_received(health):
    client, _ = health
    secret = make_token(client)["token"]
    send(client, {"day": DAY, "steps": 5000}, secret)
    send(client, {"day": DAY, "steps": 3000}, secret)
    assert stored(client) == {DAY: 5000}
    send(client, {"day": DAY, "steps": 7000}, secret)
    assert stored(client) == {DAY: 7000}


def test_several_days_can_be_sent_at_once(health):
    client, _ = health
    secret = make_token(client)["token"]
    payload = {"days": [{"day": "2026-10-17", "steps": 100}, {"day": "2026-10-18", "steps": 200}]}
    assert send(client, payload, secret).status_code == 200
    assert stored(client) == {"2026-10-17": 100, "2026-10-18": 200}


def export(*samples, name="step_count"):
    return {"data": {"metrics": [{"name": name, "units": "count", "data": list(samples)}]}}


def test_the_health_auto_export_format_is_understood(health):
    client, _ = health
    secret = make_token(client)["token"]
    payload = export(
        {"qty": 4000, "date": "2026-10-19 08:00:00 +0200"},
        {"qty": 4421.4, "date": "2026-10-19 18:30:00 +0200"},
        {"qty": 900, "date": "2026-10-20 09:00:00 +0200"},
    )
    assert send(client, payload, secret).status_code == 200
    assert stored(client) == {"2026-10-19": 8421, "2026-10-20": 900}


def test_other_metrics_are_ignored_but_an_export_without_steps_is_refused(health):
    client, _ = health
    secret = make_token(client)["token"]
    mixed = export({"qty": 70, "date": "2026-10-19 08:00:00 +0200"}, name="heart_rate")
    mixed["data"]["metrics"].append(export({"qty": 50, "date": "2026-10-19 08:00:00 +0200"})["data"]["metrics"][0])
    assert send(client, mixed, secret).status_code == 200
    assert stored(client) == {"2026-10-19": 50}
    only_other = export({"qty": 70, "date": "2026-10-19 08:00:00 +0200"}, name="heart_rate")
    assert send(client, only_other, secret).status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"steps": -1},
        {"steps": "many"},
        {"steps": True},
        {"steps": 250000},
        {"day": "2026-10-23", "steps": 10},
        {"day": "yesterday", "steps": 10},
        {"day": "1960-01-01", "steps": 10},
        {"days": "no"},
        {"days": [1]},
        {"data": {"metrics": "no"}},
        {"data": {"metrics": [{"name": "step_count", "data": [{"qty": 1}]}]}},
    ],
)
def test_bad_payloads_store_nothing(health, payload):
    client, _ = health
    secret = make_token(client)["token"]
    assert send(client, payload, secret).status_code == 422
    assert stored(client) == {}


def test_one_bad_item_stores_nothing_from_the_same_request(health):
    client, _ = health
    secret = make_token(client)["token"]
    payload = {"days": [{"day": "2026-10-18", "steps": 200}, {"day": "2026-10-19", "steps": -5}]}
    assert send(client, payload, secret).status_code == 422
    assert stored(client) == {}


def test_a_body_that_is_not_json_or_is_too_large_is_refused(health):
    client, _ = health
    secret = make_token(client)["token"]
    headers = {"Authorization": f"Bearer {secret}"}
    assert client.post(INGEST, content=b"not json", headers=headers).status_code == 422
    assert client.post(INGEST, content=b"x" * 1_000_001, headers=headers).status_code == 413


def test_turning_the_plugin_off_stops_the_intake(health):
    client, _ = health
    secret = make_token(client)["token"]
    assert client.post("/api/v1/plugins/health/deactivate").status_code == 200
    assert send(client, {"steps": 10}, secret).status_code == 404
    assert activate(client, "health").status_code == 200
    assert send(client, {"steps": 10}, secret).status_code == 200


def test_days_can_be_listed_and_removed(health):
    client, _ = health
    secret = make_token(client)["token"]
    send(client, {"days": [{"day": f"2026-10-1{n}", "steps": 100 * n} for n in range(1, 4)]}, secret)
    assert [item["day"] for item in client.get(f"{HEALTH}/days", params={"limit": 2}).json()["days"]] == [
        "2026-10-13",
        "2026-10-12",
    ]
    ranged = client.get(f"{HEALTH}/days", params={"start": "2026-10-11", "end": "2026-10-12"}).json()
    assert [item["day"] for item in ranged["days"]] == ["2026-10-12", "2026-10-11"]
    assert client.delete(f"{HEALTH}/days/2026-10-12").status_code == 200
    assert client.delete(f"{HEALTH}/days/2026-10-12").status_code == 404
    assert "2026-10-12" not in stored(client)


def test_the_plugin_cannot_read_reports_or_scores(health):
    client, _ = health
    item = next(p for p in client.get("/api/v1/plugins").json()["plugins"] if p["id"] == "health")
    assert not {"read_reports", "read_scores", "read_activities"} & set(item["permissions"])
