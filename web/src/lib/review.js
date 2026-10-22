import { addDays, parseDay, weekdayIndex } from './dates.js';

export const mondayOf = (iso) => addDays(iso, -weekdayIndex(iso));

export function weekRange(start, locale) {
  return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long', timeZone: 'UTC' }).formatRange(
    parseDay(start),
    parseDay(addDays(start, 6)),
  );
}

export function change(current, previous) {
  if (current === null || current === undefined || previous === null || previous === undefined) return null;
  return Math.round(current) - Math.round(previous);
}

export function signed(value) {
  if (value === 0) return '0';
  return value > 0 ? `+${value}` : `−${Math.abs(value)}`;
}

export function groupActivities(activities, areas) {
  return areas
    .map((area) => ({ area, items: activities.filter((item) => item.area === area) }))
    .filter((group) => group.items.length > 0);
}
