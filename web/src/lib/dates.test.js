import { describe, expect, it } from 'vitest';
import { addDays, daysBetween, daysLabel, formatDate, lastDays, parseDay, weekdayIndex, weekdayInitials } from './dates.js';

describe('dates', () => {
  it('adds days across month and year boundaries', () => {
    expect(addDays('2026-10-31', 1)).toBe('2026-11-01');
    expect(addDays('2026-01-01', -1)).toBe('2025-12-31');
    expect(addDays('2026-03-28', 3)).toBe('2026-03-31');
  });

  it('is not affected by daylight saving changes', () => {
    expect(addDays('2026-10-24', 2)).toBe('2026-10-26');
    expect(daysBetween('2026-10-24', '2026-10-26')).toBe(2);
  });

  it('numbers weekdays from Monday', () => {
    expect(weekdayIndex('2026-10-19')).toBe(0);
    expect(weekdayIndex('2026-10-25')).toBe(6);
  });

  it('lists the last days ending on the given day', () => {
    expect(lastDays('2026-10-20', 3)).toEqual(['2026-10-18', '2026-10-19', '2026-10-20']);
  });

  it('parses a day as UTC midnight', () => {
    expect(parseDay('2026-10-20').toISOString()).toBe('2026-10-20T00:00:00.000Z');
  });

  it('formats a day without shifting it to another one', () => {
    expect(formatDate('2026-10-20', 'en-GB', { day: 'numeric', month: 'long' })).toBe('20 October');
  });
});

describe('weekday helpers', () => {
  it('gives seven initials starting on Monday', () => {
    expect(weekdayInitials('en-GB')).toEqual(['M', 'T', 'W', 'T', 'F', 'S', 'S']);
    expect(weekdayInitials('it-IT')).toEqual(['L', 'M', 'M', 'G', 'V', 'S', 'D']);
  });

  it('describes only the days that are not all of them', () => {
    expect(daysLabel([0, 1, 2, 3, 4, 5, 6], 'it-IT')).toBe('');
    expect(daysLabel([0, 3, 5], 'it-IT')).toBe('L G S');
  });
});
