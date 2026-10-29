import { addDays, formatDate, weekdayIndex } from './dates.js';
import { mondayOf } from './review.js';

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

export const VIEWS = ['week', 'month', 'year'];

export function viewOf(period) {
  if (/^\d{4}$/.test(period)) return 'year';
  if (/^\d{4}-\d{2}$/.test(period)) return 'month';
  return 'week';
}

export function periodFor(kind, day) {
  if (kind === 'year') return day.slice(0, 4);
  if (kind === 'month') return day.slice(0, 7);
  return mondayOf(day);
}

export function latestPeriod(kind, today) {
  return periodFor(kind, today);
}

export function shiftView(kind, period, delta) {
  return kind === 'week' ? addDays(period, delta * 7) : shiftPeriod(period, delta);
}

export function canGoBack(kind, period, firstDay) {
  if (!firstDay) return false;
  return period > periodFor(kind, firstDay);
}

export function switchView(from, to, period, today) {
  if (from === to) return period;
  const start = from === 'week' ? period : from === 'month' ? `${period}-01` : `${period}-01-01`;
  const latest = periodFor(to, today);
  const mine = periodFor(to, start);
  if (from === 'year' && to === 'month') return period === today.slice(0, 4) ? latest : `${period}-12`;
  if (to === 'week' && periodFor(from, today) === period) return latest;
  return mine > latest ? latest : mine;
}
