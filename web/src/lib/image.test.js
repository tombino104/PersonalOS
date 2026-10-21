import { describe, expect, it } from 'vitest';
import { coverSquare } from './image.js';

describe('coverSquare', () => {
  it('crops the longer side around the centre', () => {
    expect(coverSquare(1600, 1000)).toEqual({ x: 300, y: 0, side: 1000 });
    expect(coverSquare(600, 900)).toEqual({ x: 0, y: 150, side: 600 });
    expect(coverSquare(500, 500)).toEqual({ x: 0, y: 0, side: 500 });
  });
});
