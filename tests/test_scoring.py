import pytest

from app.scoring import Item, score, tally


def test_zero_maximum_gives_null_score_not_zero_percent():
    assert score(0, 0) is None


def test_zero_obtained_with_activities_is_zero_percent():
    assert score(5, 0) == 0.0


def test_partial_and_full_scores():
    assert score(4, 3) == 75.0
    assert score(7, 7) == 100.0


def test_tally_sums_weights():
    items = [Item(3, True), Item(2, False), Item(1, True)]
    assert tally(items) == (6, 4)


def test_tally_of_nothing_is_zero_zero():
    assert tally([]) == (0, 0)


@pytest.mark.parametrize("maximum,obtained", [(-1, 0), (3, -1), (3, 4)])
def test_invalid_values_are_rejected(maximum, obtained):
    with pytest.raises(ValueError):
        score(maximum, obtained)
