import { describe, expect, it } from 'vitest';
import { parseBirthday, toBirthday, whenKey } from './people.js';

describe('parseBirthday', () => {
  it('reads a birthday with or without a year', () => {
    expect(parseBirthday('03-14')).toEqual({ year: null, month: 3, day: 14 });
    expect(parseBirthday('1990-03-14')).toEqual({ year: 1990, month: 3, day: 14 });
  });

  it('returns nothing for an empty or odd value', () => {
    expect(parseBirthday(null)).toBeNull();
    expect(parseBirthday('')).toBeNull();
    expect(parseBirthday('march')).toBeNull();
  });
});

describe('toBirthday', () => {
  it('writes a birthday back', () => {
    expect(toBirthday({ day: 4, month: 3, year: null })).toBe('03-04');
    expect(toBirthday({ day: 14, month: 3, year: 1990 })).toBe('1990-03-14');
  });

  it('is empty when nothing was typed and invalid when only half was', () => {
    expect(toBirthday({ day: '', month: '', year: '' })).toBeNull();
    expect(toBirthday({ day: 4, month: '', year: '' })).toBeUndefined();
    expect(toBirthday({ day: '', month: 3, year: 1990 })).toBeUndefined();
  });
});

describe('whenKey', () => {
  it('names today, tomorrow and later', () => {
    expect(whenKey(0)).toBe('today');
    expect(whenKey(1)).toBe('tomorrow');
    expect(whenKey(9)).toBe('inDays');
    expect(whenKey(null)).toBeNull();
  });
});
