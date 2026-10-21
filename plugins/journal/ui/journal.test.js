import { describe, expect, it } from 'vitest';
import { PROMPT_COUNT, excerpt, groupByMonth, mergeEntries, pickPrompt } from './journal.js';

describe('groupByMonth', () => {
  it('keeps the order and starts a group when the month changes', () => {
    const entries = [
      { id: 4, day: '2026-11-02' },
      { id: 3, day: '2026-10-30' },
      { id: 2, day: '2026-10-02' },
      { id: 1, day: '2026-09-30' },
    ];
    const groups = groupByMonth(entries);
    expect(groups.map((group) => group.month)).toEqual(['2026-11', '2026-10', '2026-09']);
    expect(groups[1].entries.map((entry) => entry.id)).toEqual([3, 2]);
  });

  it('returns nothing for no entries', () => {
    expect(groupByMonth([])).toEqual([]);
  });
});

describe('excerpt', () => {
  it('leaves short text alone', () => {
    expect(excerpt('Short', 20)).toEqual({ text: 'Short', truncated: false });
  });

  it('cuts long text at a word and adds an ellipsis', () => {
    const result = excerpt('one two three four five six seven', 20);
    expect(result.truncated).toBe(true);
    expect(result.text).toBe('one two three four…');
  });

  it('cuts in the middle of a very long word', () => {
    expect(excerpt('x'.repeat(50), 10)).toEqual({ text: `${'x'.repeat(10)}…`, truncated: true });
  });
});

describe('pickPrompt', () => {
  it('stays between 1 and the number of prompts', () => {
    expect(pickPrompt(0)).toBe(1);
    expect(pickPrompt(0.999999)).toBe(PROMPT_COUNT);
    expect(pickPrompt(1)).toBe(PROMPT_COUNT);
  });
});

describe('mergeEntries', () => {
  it('appends only entries it does not already have', () => {
    const merged = mergeEntries([{ id: 1 }, { id: 2 }], [{ id: 2 }, { id: 3 }]);
    expect(merged.map((entry) => entry.id)).toEqual([1, 2, 3]);
  });
});
