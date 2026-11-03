import { afterEach, describe, expect, it, vi } from 'vitest';
import { grow } from './motion.js';

function frames() {
  const queue = [];
  vi.stubGlobal('requestAnimationFrame', (callback) => queue.push(callback));
  vi.stubGlobal('cancelAnimationFrame', () => {});
  return {
    run() {
      const pending = queue.splice(0);
      pending.forEach((callback) => callback());
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('grow', () => {
  it('sets the width at once when there is no animation frame', () => {
    const node = { style: {} };
    const action = grow(node, { value: 40 });
    expect(node.style.width).toBe('40%');
    action.update({ value: 70 });
    expect(node.style.width).toBe('70%');
  });

  it('sets the width at once when the user prefers reduced motion', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const queue = frames();
    const node = { style: {} };
    grow(node, { value: 55 });
    expect(node.style.width).toBe('55%');
    expect(node.style.transition).toBeUndefined();
    queue.run();
    expect(node.style.width).toBe('55%');
  });

  it('starts empty and grows to the value after two frames', () => {
    const queue = frames();
    const node = { style: {} };
    grow(node, { value: 40, delay: 140 });
    expect(node.style.width).toBe('0%');
    expect(node.style.transition).toBe('none');
    queue.run();
    expect(node.style.width).toBe('0%');
    queue.run();
    expect(node.style.width).toBe('40%');
    expect(node.style.transition).toContain('width');
    expect(node.style.transition).toContain('140ms');
  });

  it('can grow the height instead of the width', () => {
    const queue = frames();
    const node = { style: {} };
    grow(node, { value: 25, property: 'height' });
    queue.run();
    queue.run();
    expect(node.style.height).toBe('25%');
  });

  it('plays again from empty when the key changes', () => {
    const queue = frames();
    const node = { style: {} };
    const action = grow(node, { value: 40, key: 'a' });
    queue.run();
    queue.run();
    action.update({ value: 40, key: 'b' });
    expect(node.style.width).toBe('0%');
    expect(node.style.transition).toBe('none');
    queue.run();
    queue.run();
    expect(node.style.width).toBe('40%');
  });

  it('moves smoothly to a new value when the key stays the same', () => {
    const queue = frames();
    const node = { style: {} };
    const action = grow(node, { value: 40, key: 'a' });
    queue.run();
    queue.run();
    action.update({ value: 80, key: 'a' });
    expect(node.style.width).toBe('80%');
    expect(node.style.transition).toContain('width');
  });
});
