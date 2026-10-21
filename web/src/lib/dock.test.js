import { describe, expect, it } from 'vitest';
import { MAX_DOCK, addKey, defaultKeys, isFull, moveKey, removeKey, resolveKeys } from './dock.js';

const CORE = ['home', 'stella', 'questionnaire', 'more'];
const available = (...extra) => new Set([...CORE, ...extra]);

describe('resolveKeys', () => {
  it('uses the default dock until the user changes it', () => {
    expect(resolveKeys(null, available('calendar:calendar'), ['calendar:calendar'])).toEqual([
      'home',
      'stella',
      'questionnaire',
      'calendar:calendar',
      'more',
    ]);
    expect(resolveKeys([], available(), [])).toEqual(defaultKeys([]));
  });

  it('keeps a saved order, always with more last', () => {
    const keys = resolveKeys(['questionnaire', 'calendar:calendar', 'home', 'more'], available('calendar:calendar'), []);
    expect(keys).toEqual(['questionnaire', 'calendar:calendar', 'home', 'more']);
  });

  it('drops entries of plugins that are not available any more', () => {
    expect(resolveKeys(['home', 'gone:page', 'questionnaire', 'more'], available(), [])).toEqual([
      'home',
      'questionnaire',
      'more',
    ]);
  });

  it('puts the questionnaire back if it is missing and ignores duplicates', () => {
    expect(resolveKeys(['home', 'home', 'stella'], available(), [])).toEqual(['home', 'stella', 'questionnaire', 'more']);
  });

  it('never goes over the maximum and keeps the questionnaire', () => {
    const many = ['a:a', 'b:b', 'c:c', 'd:d', 'e:e', 'f:f', 'g:g', 'h:h'];
    const keys = resolveKeys(many, available(...many), []);
    expect(keys).toHaveLength(MAX_DOCK);
    expect(keys.at(-1)).toBe('more');
    expect(keys).toContain('questionnaire');
  });
});

describe('editing', () => {
  const start = ['home', 'stella', 'questionnaire', 'more'];

  it('adds before more and stops when the dock is full', () => {
    let keys = addKey(start, 'a:a');
    expect(keys).toEqual(['home', 'stella', 'questionnaire', 'a:a', 'more']);
    keys = addKey(addKey(addKey(keys, 'b:b'), 'c:c'), 'd:d');
    expect(isFull(keys)).toBe(true);
    expect(keys).toHaveLength(MAX_DOCK);
    expect(addKey(keys, 'e:e')).toBe(keys);
    expect(addKey(start, 'home')).toBe(start);
  });

  it('removes anything but the questionnaire and more', () => {
    expect(removeKey(start, 'home')).toEqual(['stella', 'questionnaire', 'more']);
    expect(removeKey(start, 'questionnaire')).toBe(start);
    expect(removeKey(start, 'more')).toBe(start);
  });

  it('moves an item up or down without touching more', () => {
    expect(moveKey(start, 'stella', -1)).toEqual(['stella', 'home', 'questionnaire', 'more']);
    expect(moveKey(start, 'home', 1)).toEqual(['stella', 'home', 'questionnaire', 'more']);
    expect(moveKey(start, 'home', -1)).toBe(start);
    expect(moveKey(start, 'questionnaire', 1)).toBe(start);
    expect(moveKey(start, 'more', -1)).toBe(start);
    expect(moveKey(start, 'unknown', 1)).toBe(start);
  });
});
