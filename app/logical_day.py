from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class DayRules:
    timezone: str = "Europe/Rome"
    cutoff: time = time(4, 0)

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def _require_aware(moment: datetime) -> None:
    if moment.tzinfo is None:
        raise ValueError("moment must be timezone-aware")


def logical_day(moment: datetime, rules: DayRules) -> date:
    _require_aware(moment)
    local = moment.astimezone(rules.zone)
    shifted = local - timedelta(hours=rules.cutoff.hour, minutes=rules.cutoff.minute)
    return shifted.date()


def edit_deadline(day: date, rules: DayRules) -> datetime:
    local = datetime.combine(day + timedelta(days=2), rules.cutoff, tzinfo=rules.zone)
    return local.astimezone(timezone.utc)
