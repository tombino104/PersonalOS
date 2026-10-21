import { describe, expect, it } from 'vitest';
import { QUOTES, localDay, quoteFor } from './quotes.js';

describe('daily quotes', () => {
  it('has an author and both languages for every quote', () => {
    expect(QUOTES.length).toBeGreaterThanOrEqual(90);
    for (const [author, en, it_] of QUOTES) {
      expect(author.trim()).not.toBe('');
      expect(en.trim()).not.toBe('');
      expect(it_.trim()).not.toBe('');
    }
  });

  it('has no repeated quote', () => {
    const texts = QUOTES.map((quote) => quote[1]);
    expect(new Set(texts).size).toBe(texts.length);
  });

  it('gives the same quote all day and a different one the next day', () => {
    expect(quoteFor('2026-10-21')).toBe(quoteFor('2026-10-21'));
    expect(quoteFor('2026-10-22')).not.toBe(quoteFor('2026-10-21'));
  });

  it('walks through every quote before repeating', () => {
    const seen = new Set();
    let day = new Date(Date.UTC(2026, 0, 1));
    for (let index = 0; index < QUOTES.length; index += 1) {
      seen.add(quoteFor(day.toISOString().slice(0, 10)));
      day = new Date(day.getTime() + 86400000);
    }
    expect(seen.size).toBe(QUOTES.length);
  });

  it('formats the local date', () => {
    expect(localDay(new Date(2026, 9, 5))).toBe('2026-10-05');
  });
});
