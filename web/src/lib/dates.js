const DAY_MS = 86400000;

export function parseDay(iso) {
  const [year, month, day] = iso.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

export function formatDay(date) {
  return date.toISOString().slice(0, 10);
}

export function addDays(iso, count) {
  return formatDay(new Date(parseDay(iso).getTime() + count * DAY_MS));
}

export function daysBetween(fromIso, toIso) {
  return Math.round((parseDay(toIso).getTime() - parseDay(fromIso).getTime()) / DAY_MS);
}

export function weekdayIndex(iso) {
  return (parseDay(iso).getUTCDay() + 6) % 7;
}

export function lastDays(endIso, count) {
  return Array.from({ length: count }, (_, index) => addDays(endIso, index - count + 1));
}

export function weekdayInitials(locale) {
  return Array.from({ length: 7 }, (_, index) =>
    new Intl.DateTimeFormat(locale, { weekday: 'narrow', timeZone: 'UTC' }).format(parseDay(addDays('2024-01-01', index))),
  );
}

export function daysLabel(days, locale) {
  if (days.length === 7) return '';
  const initials = weekdayInitials(locale);
  return days.map((day) => initials[day]).join(' ');
}

export function formatDate(iso, locale, options) {
  return new Intl.DateTimeFormat(locale, { ...options, timeZone: 'UTC' }).format(parseDay(iso));
}
