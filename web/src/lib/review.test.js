import { describe, expect, it } from 'vitest';
import { change, groupActivities, mondayOf, signed, weekRange } from './review.js';

describe('mondayOf', () => {
  it('goes back to the Monday of the week', () => {
    expect(mondayOf('2026-10-19')).toBe('2026-10-19');
    expect(mondayOf('2026-10-22')).toBe('2026-10-19');
    expect(mondayOf('2026-10-25')).toBe('2026-10-19');
    expect(mondayOf('2026-11-01')).toBe('2026-10-26');
  });
});

describe('weekRange', () => {
  it('writes one range, with the month once when the week stays inside it', () => {
    const text = weekRange('2026-10-19', 'en');
    expect(text).toMatch(/October/);
    expect(text.match(/October/g)).toHaveLength(1);
    expect(text).toMatch(/19/);
    expect(text).toMatch(/25/);
  });

  it('names both months when the week crosses two', () => {
    const text = weekRange('2026-10-26', 'en');
    expect(text).toMatch(/October/);
    expect(text).toMatch(/November/);
  });

  it('follows the language', () => {
    expect(weekRange('2026-10-19', 'it')).toMatch(/ottobre/);
  });
});

describe('change', () => {
  it('compares rounded values and is null without both weeks', () => {
    expect(change(80.4, 75.6)).toBe(4);
    expect(change(50, 70)).toBe(-20);
    expect(change(null, 70)).toBeNull();
    expect(change(70, undefined)).toBeNull();
  });

  it('writes the sign', () => {
    expect(signed(4)).toBe('+4');
    expect(signed(-20)).toBe('−20');
    expect(signed(0)).toBe('0');
  });
});

describe('groupActivities', () => {
  it('groups by area in the given order and skips empty areas', () => {
    const items = [
      { area: 'career', name: 'a' },
      { area: 'physical', name: 'b' },
      { area: 'career', name: 'c' },
    ];
    const groups = groupActivities(items, ['physical', 'social', 'career']);
    expect(groups.map((group) => group.area)).toEqual(['physical', 'career']);
    expect(groups[1].items).toHaveLength(2);
  });
});
