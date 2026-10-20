from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    weight: int
    done: bool


def tally(items: Iterable[Item]) -> tuple[int, int]:
    maximum = 0
    obtained = 0
    for item in items:
        maximum += item.weight
        if item.done:
            obtained += item.weight
    return maximum, obtained


def score(maximum: int, obtained: int) -> float | None:
    if maximum < 0 or obtained < 0 or obtained > maximum:
        raise ValueError("expected 0 <= obtained <= maximum")
    if maximum == 0:
        return None
    return obtained / maximum * 100


def mean_score(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)
