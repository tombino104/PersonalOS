import sqlite3
from datetime import date

import pytest

from app import reports, seed, settings
from app.reports import ReportClosed
from tests.conftest import utc

DAY = date(2026, 10, 20)
EVENING = utc(2026, 10, 20, 20, 0)


def score_of(conn, user_id, area, day=DAY):
    for entry in reports.scores_for_day(conn, user_id, day):
        if entry["area"] == area:
            return entry
    return None


def test_unfilled_day_has_no_row_and_no_scores(conn, user_id):
    assert conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
    assert reports.scores_for_day(conn, user_id, DAY) == []


def test_draft_is_not_scored(conn, user_id, rules, add_activity):
    add_activity("physical", "Workout", 3)
    reports.open_report(conn, user_id, DAY, EVENING, rules)
    assert reports.scores_for_day(conn, user_id, DAY) == []
    assert conn.execute("SELECT COUNT(*) FROM daily_scores").fetchone()[0] == 0


def test_area_without_activities_has_null_score(conn, user_id, rules, add_activity):
    add_activity("physical", "Workout", 3)
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    reports.complete_report(conn, report_id, EVENING)
    empty = score_of(conn, user_id, "mindset")
    assert empty == {"area": "mindset", "maximum": 0, "obtained": 0, "score": None}


def test_scores_per_area(conn, user_id, rules, add_activity):
    workout = add_activity("physical", "Workout", 3)
    add_activity("physical", "Walk", 1)
    reading = add_activity("intellect", "Reading", 2)
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    reports.set_done(conn, report_id, workout, True, EVENING)
    reports.set_done(conn, report_id, reading, True, EVENING)
    reports.complete_report(conn, report_id, EVENING)
    assert score_of(conn, user_id, "physical")["score"] == 75.0
    assert score_of(conn, user_id, "intellect")["score"] == 100.0


def test_all_undone_is_zero_percent_not_null(conn, user_id, rules, add_activity):
    add_activity("physical", "Workout", 3)
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    reports.complete_report(conn, report_id, EVENING)
    assert score_of(conn, user_id, "physical")["score"] == 0.0


def test_changing_activities_does_not_alter_past_reports(conn, user_id, rules, add_activity):
    workout = add_activity("physical", "Workout", 3)
    add_activity("physical", "Walk", 1)
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    reports.set_done(conn, report_id, workout, True, EVENING)
    reports.complete_report(conn, report_id, EVENING)
    before = reports.scores_for_day(conn, user_id, DAY)

    conn.execute("UPDATE activities SET weight = 1, name = 'Renamed' WHERE id = ?", (workout,))
    conn.execute("UPDATE activities SET archived_at = datetime('now') WHERE name = 'Walk'")
    add_activity("physical", "Brand new", 3)
    conn.commit()

    assert reports.scores_for_day(conn, user_id, DAY) == before
    row = conn.execute(
        "SELECT name_at_time, weight_at_time FROM completions "
        "WHERE report_id = ? AND activity_id = ?",
        (report_id, workout),
    ).fetchone()
    assert (row["name_at_time"], row["weight_at_time"]) == ("Workout", 3)


def test_new_report_uses_current_activities(conn, user_id, rules, add_activity):
    old = add_activity("physical", "Old", 3)
    conn.execute("UPDATE activities SET archived_at = datetime('now') WHERE id = ?", (old,))
    add_activity("physical", "Current", 2)
    conn.commit()
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    names = [r["name_at_time"] for r in conn.execute(
        "SELECT name_at_time FROM completions WHERE report_id = ?", (report_id,)
    )]
    assert names == ["Current"]


def test_activities_are_frozen_when_draft_opens(conn, user_id, rules, add_activity):
    add_activity("physical", "Workout", 3)
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    add_activity("physical", "Added later", 2)
    count = conn.execute(
        "SELECT COUNT(*) FROM completions WHERE report_id = ?", (report_id,)
    ).fetchone()[0]
    assert count == 1


def test_open_report_is_idempotent(conn, user_id, rules, add_activity):
    add_activity("physical", "Workout", 3)
    first = reports.open_report(conn, user_id, DAY, EVENING, rules)
    second = reports.open_report(conn, user_id, DAY, EVENING, rules)
    assert first == second
    assert conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1


def test_yesterday_can_be_edited_until_end_of_today(conn, user_id, rules, add_activity):
    workout = add_activity("physical", "Workout", 2)
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    reports.complete_report(conn, report_id, EVENING)
    next_evening = utc(2026, 10, 21, 20, 0)
    reports.set_done(conn, report_id, workout, True, next_evening)
    assert score_of(conn, user_id, "physical")["score"] == 100.0


def test_report_is_locked_at_the_deadline(conn, user_id, rules, add_activity):
    workout = add_activity("physical", "Workout", 2)
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    reports.complete_report(conn, report_id, EVENING)
    with pytest.raises(ReportClosed):
        reports.set_done(conn, report_id, workout, True, utc(2026, 10, 22, 2, 0))
    reports.set_done(conn, report_id, workout, True, utc(2026, 10, 22, 1, 59))


def test_close_expired_marks_reports_closed(conn, user_id, rules, add_activity):
    add_activity("physical", "Workout", 2)
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    assert reports.close_expired(conn, utc(2026, 10, 22, 1, 59)) == 0
    assert reports.close_expired(conn, utc(2026, 10, 22, 2, 0)) == 1
    status = conn.execute("SELECT status FROM reports WHERE id = ?", (report_id,)).fetchone()[0]
    assert status == "closed"
    with pytest.raises(ReportClosed):
        reports.complete_report(conn, report_id, utc(2026, 10, 22, 3, 0))


def test_cannot_open_future_or_expired_days(conn, user_id, rules):
    with pytest.raises(ValueError):
        reports.open_report(conn, user_id, date(2026, 10, 25), EVENING, rules)
    with pytest.raises(ReportClosed):
        reports.open_report(conn, user_id, date(2026, 10, 10), EVENING, rules)


def test_night_before_cutoff_still_counts_for_previous_day(conn, user_id, rules):
    after_midnight = utc(2026, 10, 20, 22, 30)
    assert reports.open_report(conn, user_id, date(2026, 10, 20), after_midnight, rules)
    with pytest.raises(ValueError):
        reports.open_report(conn, user_id, date(2026, 10, 21), after_midnight, rules)


def test_activities_and_reports_are_never_deleted(conn, user_id, rules, add_activity):
    activity = add_activity("physical", "Workout", 2)
    report_id = reports.open_report(conn, user_id, DAY, EVENING, rules)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM activities WHERE id = ?", (activity,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))


def test_weight_must_be_between_one_and_three(conn, add_activity):
    with pytest.raises(sqlite3.IntegrityError):
        add_activity("physical", "Too heavy", 4)


def test_settings_defaults(conn):
    rules = settings.day_rules(conn)
    assert rules.timezone == "Europe/Rome"
    assert rules.cutoff.hour == 4 and rules.cutoff.minute == 0


def test_six_areas_exist(conn):
    slugs = [r["slug"] for r in conn.execute("SELECT slug FROM areas ORDER BY position")]
    assert slugs == ["physical", "discipline", "social", "intellect", "career", "mindset"]


def test_sample_seed_runs_once_and_not_over_existing_data(conn):
    assert seed.sample_activities(conn) is True
    first = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    assert first > 0
    assert seed.sample_activities(conn) is False
    assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == first
