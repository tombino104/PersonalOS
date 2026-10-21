import { addDays, weekdayIndex } from '$core/lib/dates.js';

export const CATEGORIES = ['personal', 'work', 'study', 'health', 'social', 'other'];
export const REPEATS = ['none', 'daily', 'weekly', 'monthly', 'yearly'];
export const GRID_DAYS = 42;
export const MAX_DOTS = 3;

const COLORS = {
  personal: 'var(--area-mindset)',
  work: 'var(--area-career)',
  study: 'var(--area-intellect)',
  health: 'var(--area-physical)',
  social: 'var(--area-social)',
  other: 'var(--ink-3)',
};

export function categoryColor(category) {
  return COLORS[category] ?? COLORS.other;
}

export function todayIso(now = new Date()) {
  const pad = (value) => String(value).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function monthStart(iso) {
  return `${iso.slice(0, 7)}-01`;
}

export function shiftMonth(iso, delta) {
  const [year, month] = iso.split('-').map(Number);
  const index = year * 12 + (month - 1) + delta;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}-01`;
}

export function gridDays(iso) {
  const first = monthStart(iso);
  const start = addDays(first, -weekdayIndex(first));
  return Array.from({ length: GRID_DAYS }, (_, index) => addDays(start, index));
}

export function groupByDay(occurrences) {
  const groups = {};
  for (const item of occurrences) (groups[item.day] ??= []).push(item);
  return groups;
}

export function dotCategories(items) {
  const seen = [];
  for (const item of items) if (!seen.includes(item.category)) seen.push(item.category);
  return seen.slice(0, MAX_DOTS);
}
