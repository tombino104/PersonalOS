import pytest

from app import recap
from tests.conftest import utc

RECAPS = "/api/v1/recaps"


def record(client, clock, year, month, day, ticks=None, reflection=None):
    clock.now = utc(year, month, day, 20, 0)
    iso = f"{year}-{month:02d}-{day:02d}"
    client.post("/api/v1/reports", json={"day": iso})
    for activity_id in ticks or []:
        client.put(f"/api/v1/reports/{iso}/completions/{activity_id}", json={"done": True})
    if reflection:
        client.put(f"/api/v1/reports/{iso}/reflection", json={"text": reflection})
    client.post(f"/api/v1/reports/{iso}/complete")


def first_ids(client, count):
    return [item["id"] for item in client.get("/api/v1/activities").json()["activities"]][:count]


@pytest.mark.parametrize(
    "period, kind, start, end",
    [
        ("2026-10", "month", "2026-10-01", "2026-10-31"),
        ("2026-02", "month", "2026-02-01", "2026-02-28"),
        ("2024-02", "month", "2024-02-01", "2024-02-29"),
        ("2026", "year", "2026-01-01", "2026-12-31"),
    ],
)
def test_periods_are_parsed(period, kind, start, end):
    parsed = recap.parse_period(period)
    assert (parsed[0], parsed[1].isoformat(), parsed[2].isoformat()) == (kind, start, end)


@pytest.mark.parametrize("period", ["", "2026-13", "2026-00", "26", "2026-1", "20x6", "2026-10-01", "+202", "abcd-ef"])
def test_bad_periods_are_refused(client, clock, period):
    clock.now = utc(2026, 10, 22, 12, 0)
    assert client.get(f"{RECAPS}/{period or 'x'}").status_code in (404, 422)
    with pytest.raises(recap.InvalidPeriod):
        recap.parse_period(period)


def test_the_api_reports_invalid_and_future_periods(client, clock):
    clock.now = utc(2026, 10, 22, 12, 0)
    assert client.get(f"{RECAPS}/2026-13").json()["error"]["code"] == "invalid_period"
    assert client.get(f"{RECAPS}/2026-11").json()["error"]["code"] == "future_period"
    assert client.get(f"{RECAPS}/2027").json()["error"]["code"] == "future_period"
    assert client.get(f"{RECAPS}/2026-10").status_code == 200


def test_a_month_with_nothing_is_empty_not_zero(client, clock):
    clock.now = utc(2026, 10, 22, 12, 0)
    month = client.get(f"{RECAPS}/2026-10").json()
    assert month["kind"] == "month" and month["is_current"] is True
    assert month["filled_days"] == 0 and month["overall"] is None
    assert all(item["average"] is None for item in month["areas"])
    assert month["top_habits"] == [] and month["best_week"] is None and month["lines"] == []
    assert len(month["days"]) == 31 and not any(day["completed"] for day in month["days"])
    assert month["elapsed_days"] == 22


def test_a_finished_month_counts_all_its_days(client, clock):
    clock.now = utc(2026, 11, 5, 12, 0)
    month = client.get(f"{RECAPS}/2026-10").json()
    assert month["is_current"] is False and month["elapsed_days"] == 31


def test_the_month_summarises_days_areas_and_lines(client, clock):
    ids = first_ids(client, 2)
    record(client, clock, 2026, 10, 3, ticks=ids, reflection="First line")
    record(client, clock, 2026, 10, 4, ticks=ids[:1])
    record(client, clock, 2026, 10, 12)
    record(client, clock, 2026, 10, 14, reflection="Later line")
    clock.now = utc(2026, 10, 22, 12, 0)
    month = client.get(f"{RECAPS}/2026-10").json()
    assert month["filled_days"] == 4
    assert month["overall"] is not None
    third = next(day for day in month["days"] if day["day"] == "2026-10-03")
    assert third["completed"] is True and third["overall"] is not None
    assert next(day for day in month["days"] if day["day"] == "2026-10-05")["completed"] is False
    assert month["line_count"] == 2
    assert [line["text"] for line in month["lines"]] == ["Later line", "First line"]


def test_the_previous_month_is_there_for_comparison(client, clock):
    ids = first_ids(client, 3)
    record(client, clock, 2026, 9, 10, ticks=ids)
    record(client, clock, 2026, 9, 11, ticks=ids)
    record(client, clock, 2026, 10, 10, ticks=ids[:1])
    clock.now = utc(2026, 10, 22, 12, 0)
    month = client.get(f"{RECAPS}/2026-10").json()
    assert month["previous_filled_days"] == 2 and month["previous_days"] == 30
    assert month["previous_overall"] is not None
    physical = next(item for item in month["areas"] if item["area"] == "physical")
    assert physical["previous"] is not None


def test_the_most_kept_habits_need_a_few_days(client, clock):
    ids = first_ids(client, 2)
    record(client, clock, 2026, 10, 1, ticks=ids)
    record(client, clock, 2026, 10, 2, ticks=ids[:1])
    clock.now = utc(2026, 10, 22, 12, 0)
    assert client.get(f"{RECAPS}/2026-10").json()["top_habits"] == []
    record(client, clock, 2026, 10, 3, ticks=ids[:1])
    clock.now = utc(2026, 10, 22, 12, 0)
    top = client.get(f"{RECAPS}/2026-10").json()["top_habits"]
    assert [item["activity_id"] for item in top][:1] == [ids[0]]
    assert top[0]["done"] == 3 and top[0]["total"] == 3
    assert all(item["done"] > 0 for item in top)


def test_the_best_week_is_the_one_with_most_days(client, clock):
    for day in (6, 7):
        record(client, clock, 2026, 10, day)
    for day in (12, 13, 14, 15):
        record(client, clock, 2026, 10, day)
    clock.now = utc(2026, 10, 22, 12, 0)
    best = client.get(f"{RECAPS}/2026-10").json()["best_week"]
    assert best == {"week_start": "2026-10-12", "filled": 4, "possible": 7}


def test_the_year_lists_its_months(client, clock):
    ids = first_ids(client, 1)
    record(client, clock, 2026, 3, 5, ticks=ids)
    record(client, clock, 2026, 3, 6, ticks=ids)
    record(client, clock, 2026, 10, 5, ticks=ids)
    clock.now = utc(2026, 10, 22, 12, 0)
    year = client.get(f"{RECAPS}/2026").json()
    assert year["kind"] == "year" and year["filled_days"] == 3
    assert [month["month"] for month in year["months"]][0] == "2026-01"
    assert len(year["months"]) == 10
    march = next(month for month in year["months"] if month["month"] == "2026-03")
    assert march == {"month": "2026-03", "filled": 2, "possible": 31}
    assert year["months"][-1]["possible"] == 22
    assert "days" not in year and year["lines"] == []
    assert year["elapsed_days"] == 295
