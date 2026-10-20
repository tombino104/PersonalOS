from datetime import date, datetime

import pytest

from app.logical_day import DayRules, edit_deadline, logical_day
from tests.conftest import utc


def test_before_cutoff_belongs_to_previous_day(rules):
    assert logical_day(utc(2026, 10, 20, 1, 59), rules) == date(2026, 10, 19)


def test_at_cutoff_belongs_to_current_day(rules):
    assert logical_day(utc(2026, 10, 20, 2, 0), rules) == date(2026, 10, 20)


def test_cutoff_follows_local_time_after_daylight_saving_ends(rules):
    assert logical_day(utc(2026, 10, 26, 2, 59), rules) == date(2026, 10, 25)
    assert logical_day(utc(2026, 10, 26, 3, 0), rules) == date(2026, 10, 26)


def test_other_timezone_is_respected():
    rules = DayRules(timezone="UTC")
    assert logical_day(utc(2026, 10, 20, 3, 59), rules) == date(2026, 10, 19)
    assert logical_day(utc(2026, 10, 20, 4, 0), rules) == date(2026, 10, 20)


def test_naive_datetime_is_rejected(rules):
    with pytest.raises(ValueError):
        logical_day(datetime(2026, 10, 20, 12, 0), rules)


def test_edit_deadline_is_cutoff_two_days_later(rules):
    assert edit_deadline(date(2026, 10, 20), rules) == utc(2026, 10, 22, 2, 0)


def test_edit_deadline_handles_daylight_saving_change(rules):
    assert edit_deadline(date(2026, 10, 24), rules) == utc(2026, 10, 26, 3, 0)
