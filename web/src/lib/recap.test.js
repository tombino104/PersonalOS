import { describe, expect, it } from 'vitest';
import {
  currentPeriod,
  dayCountChange,
  homeInvitation,
  monthOffset,
  periodKind,
  periodLabel,
  readingOf,
  shiftPeriod,
  switchKind,
} from './recap.js';

describe('periods', () => {
  it('tells a month from a year', () => {
    expect(periodKind('2026')).toBe('year');
    expect(periodKind('2026-10')).toBe('month');
  });

  it('finds the current period', () => {
    expect(currentPeriod('month', '2026-10-28')).toBe('2026-10');
    expect(currentPeriod('year', '2026-10-28')).toBe('2026');
  });

  it('moves across year boundaries', () => {
    expect(shiftPeriod('2026-01', -1)).toBe('2025-12');
    expect(shiftPeriod('2025-12', 1)).toBe('2026-01');
    expect(shiftPeriod('2026-10', -10)).toBe('2025-12');
    expect(shiftPeriod('2026', -1)).toBe('2025');
  });

  it('switches between month and year without leaving the past', () => {
    expect(switchKind('2026-03', 'year', '2026-10-28')).toBe('2026');
    expect(switchKind('2025', 'month', '2026-10-28')).toBe('2025-12');
    expect(switchKind('2026', 'month', '2026-10-28')).toBe('2026-10');
    expect(switchKind('2026-03', 'month', '2026-10-28')).toBe('2026-03');
  });

  it('labels periods', () => {
    expect(periodLabel('2026', 'en')).toBe('2026');
    expect(periodLabel('2026-10', 'en')).toBe('October 2026');
  });

  it('knows which weekday a month starts on', () => {
    expect(monthOffset('2026-10')).toBe(3);
    expect(monthOffset('2026-06')).toBe(0);
  });
});

describe('readingOf', () => {
  it('names the highest and the lowest area', () => {
    const areas = [
      { area: 'physical', average: 80 },
      { area: 'social', average: 40 },
      { area: 'career', average: null },
    ];
    expect(readingOf(areas)).toEqual({ high: 'physical', low: 'social' });
  });

  it('says nothing without a real difference', () => {
    expect(readingOf([{ area: 'physical', average: 50 }])).toBeNull();
    expect(readingOf([{ area: 'a', average: 50 }, { area: 'b', average: 50 }])).toBeNull();
    expect(readingOf([{ area: 'a', average: null }, { area: 'b', average: null }])).toBeNull();
  });
});

describe('dayCountChange', () => {
  it('compares only when there was a previous period', () => {
    expect(dayCountChange({ filled_days: 5, previous_filled_days: 0 })).toBeNull();
    expect(dayCountChange({ filled_days: 5, previous_filled_days: 3 })).toBe(2);
    expect(dayCountChange({ filled_days: 2, previous_filled_days: 3 })).toBe(-1);
  });
});

describe('homeInvitation', () => {
  it('invites to the last month during the first week', () => {
    expect(homeInvitation('2026-10-03', true)).toBe('2026-09');
    expect(homeInvitation('2026-10-07', true)).toBe('2026-09');
    expect(homeInvitation('2026-10-08', true)).toBeNull();
  });

  it('invites to the last year in early January', () => {
    expect(homeInvitation('2027-01-05', true)).toBe('2026');
    expect(homeInvitation('2027-01-14', true)).toBe('2026');
    expect(homeInvitation('2027-01-20', true)).toBeNull();
  });

  it('stays quiet when there is nothing behind', () => {
    expect(homeInvitation('2026-10-03', false)).toBeNull();
  });
});
