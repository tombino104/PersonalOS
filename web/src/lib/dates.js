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

export function formatDate(iso, locale, options) {
  return new Intl.DateTimeFormat(locale, { ...options, timeZone: 'UTC' }).format(parseDay(iso));
}
