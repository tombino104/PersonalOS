import { describe, expect, it } from 'vitest';
import { dotCategories, gridDays, groupByDay, monthStart, shiftMonth, todayIso } from './calendar.js';

describe('calendar grid', () => {
  it('always has six weeks starting on a Monday', () => {
    const days = gridDays('2026-10-21');
    expect(days).toHaveLength(42);
    expect(days[0]).toBe('2026-09-28');
    expect(days[41]).toBe('2026-11-08');
  });

  it('starts on the first when the month begins on a Monday', () => {
    expect(gridDays('2026-06-15')[0]).toBe('2026-06-01');
  });

  it('shifts months across the year boundary', () => {
    expect(shiftMonth('2026-12-01', 1)).toBe('2027-01-01');
    expect(shiftMonth('2026-01-15', -1)).toBe('2025-12-01');
    expect(monthStart('2026-10-21')).toBe('2026-10-01');
  });

  it('formats the local date', () => {
    expect(todayIso(new Date(2026, 9, 5))).toBe('2026-10-05');
  });
});

describe('calendar events', () => {
  const items = [
    { day: '2026-10-21', category: 'work' },
    { day: '2026-10-21', category: 'work' },
    { day: '2026-10-22', category: 'health' },
  ];

  it('groups occurrences by day', () => {
    const groups = groupByDay(items);
    expect(groups['2026-10-21']).toHaveLength(2);
    expect(groups['2026-10-22']).toHaveLength(1);
  });

  it('shows one dot per category, at most three', () => {
    expect(dotCategories(items.slice(0, 2))).toEqual(['work']);
    const many = ['personal', 'work', 'study', 'health'].map((category) => ({ category }));
    expect(dotCategories(many)).toHaveLength(3);
  });
});
