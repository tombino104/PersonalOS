import { describe, expect, it } from 'vitest';
import { AREAS } from './charts.js';
import en from '../locales/en.json';
import it_ from '../locales/it.json';
import { SUGGESTIONS } from './suggestions.js';

describe('suggestions', () => {
  it('cover every area with a few ideas', () => {
    expect(Object.keys(SUGGESTIONS).sort()).toEqual([...AREAS].sort());
    for (const list of Object.values(SUGGESTIONS)) expect(list.length).toBeGreaterThanOrEqual(4);
  });

  it('have valid weights and weekly goals, and no repeated id in an area', () => {
    for (const list of Object.values(SUGGESTIONS)) {
      expect(new Set(list.map((item) => item.id)).size).toBe(list.length);
      for (const item of list) {
        expect([1, 2, 3]).toContain(item.weight);
        expect(item.times).toBeGreaterThanOrEqual(0);
        expect(item.times).toBeLessThanOrEqual(7);
      }
    }
  });

  it('are translated in both languages', () => {
    for (const [area, list] of Object.entries(SUGGESTIONS)) {
      for (const item of list) {
        const key = `suggestion.${area}.${item.id}`;
        expect(en[key], key).toBeTruthy();
        expect(it_[key], key).toBeTruthy();
      }
    }
  });
});
