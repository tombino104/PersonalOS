import { afterEach, describe, expect, it, vi } from 'vitest';
import { isOpen, setOpen } from './collapse.js';

function stubStorage() {
  const store = new Map();
  vi.stubGlobal('localStorage', {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('collapse', () => {
  it('starts closed and remembers what was opened', () => {
    stubStorage();
    expect(isOpen('review.habits')).toBe(false);
    setOpen('review.habits', true);
    expect(isOpen('review.habits')).toBe(true);
    expect(isOpen('review.lines')).toBe(false);
    setOpen('review.habits', false);
    expect(isOpen('review.habits')).toBe(false);
  });

  it('stays closed when storage is unavailable', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('blocked');
      },
      removeItem: () => {
        throw new Error('blocked');
      },
    });
    expect(isOpen('x')).toBe(false);
    expect(() => setOpen('x', true)).not.toThrow();
  });
});
