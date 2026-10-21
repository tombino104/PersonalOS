import { describe, expect, it } from 'vitest';
import { barWidths, buildChart, seriesFor, yFor } from './chart.js';

describe('mood chart', () => {
  it('puts higher moods higher on the chart', () => {
    expect(yFor(5)).toBeLessThan(yFor(1));
  });

  it('draws one line for consecutive days', () => {
    const chart = buildChart([3, 4, 5]);
    expect(chart.points).toHaveLength(3);
    expect(chart.line.match(/M/g)).toHaveLength(1);
    expect(chart.gaps).toEqual([]);
  });

  it('breaks the line at days without an entry instead of dropping to zero', () => {
    const chart = buildChart([3, null, 4]);
    expect(chart.points).toHaveLength(2);
    expect(chart.line.match(/M/g)).toHaveLength(2);
    expect(chart.gaps).toHaveLength(1);
    expect(chart.points.every((point) => point.y >= yFor(5) && point.y <= yFor(1))).toBe(true);
  });

  it('has a grid line per level', () => {
    expect(buildChart([]).grid.map((row) => row.value)).toEqual([1, 2, 3, 4, 5]);
  });

  it('scales the bars to the most frequent value', () => {
    expect(barWidths([0, 2, 4, 1, 0])).toEqual([0, 50, 100, 25, 0]);
    expect(barWidths([0, 0, 0, 0, 0])).toEqual([0, 0, 0, 0, 0]);
  });

  it('lines entries up with days and leaves the rest empty', () => {
    const days = ['2026-10-18', '2026-10-19', '2026-10-20'];
    expect(seriesFor(days, [{ day: '2026-10-20', value: 4 }, { day: '2026-10-18', value: 2 }])).toEqual([2, null, 4]);
  });
});
