import { formatDate, weekdayIndex } from './dates.js';

export const periodKind = (period) => (period.length === 4 ? 'year' : 'month');

export function currentPeriod(kind, today) {
  return kind === 'year' ? today.slice(0, 4) : today.slice(0, 7);
}

export function shiftPeriod(period, delta) {
  if (periodKind(period) === 'year') return String(Number(period) + delta).padStart(4, '0');
  const index = Number(period.slice(0, 4)) * 12 + Number(period.slice(5)) - 1 + delta;
  const year = Math.floor(index / 12);
  return `${String(year).padStart(4, '0')}-${String((index % 12) + 1).padStart(2, '0')}`;
}

export function switchKind(period, kind, today) {
  if (periodKind(period) === kind) return period;
  if (kind === 'year') return period.slice(0, 4);
  const last = `${period}-12`;
  return last > today.slice(0, 7) ? today.slice(0, 7) : last;
}

export function periodLabel(period, locale) {
  if (periodKind(period) === 'year') return period;
  return formatDate(`${period}-01`, locale, { month: 'long', year: 'numeric' });
}

export function monthName(month, locale) {
  return formatDate(`${month}-01`, locale, { month: 'short' });
}

export function monthOffset(period) {
  return weekdayIndex(`${period}-01`);
}

export function readingOf(areas) {
  const present = areas.filter((item) => item.average !== null && item.average !== undefined);
  if (present.length < 2) return null;
  const high = present.reduce((a, b) => (b.average > a.average ? b : a));
  const low = present.reduce((a, b) => (b.average < a.average ? b : a));
  return high.area === low.area || high.average === low.average ? null : { high: high.area, low: low.area };
}

export function dayCountChange(data) {
  if (data.previous_filled_days === 0) return null;
  return data.filled_days - data.previous_filled_days;
}

export function homeInvitation(today, hasDataBefore) {
  if (!hasDataBefore) return null;
  const month = Number(today.slice(5, 7));
  const day = Number(today.slice(8, 10));
  if (month === 1 && day <= 14) return String(Number(today.slice(0, 4)) - 1).padStart(4, '0');
  if (day <= 7) return shiftPeriod(today.slice(0, 7), -1);
  return null;
}
