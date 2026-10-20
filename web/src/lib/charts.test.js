import { describe, expect, it } from 'vitest';
import { AREAS, buildHeatGrid, heatLevel, radarPoint, radarPolygon, trendGeometry } from './charts.js';

describe('trendGeometry', () => {
  it('draws one run for consecutive values', () => {
    const { line, area, points } = trendGeometry([10, 50, 90]);
    expect(points).toHaveLength(3);
    expect(line.startsWith('M')).toBe(true);
    expect(line.match(/M/g)).toHaveLength(1);
    expect(area.endsWith('Z')).toBe(true);
  });

  it('breaks the line at empty days', () => {
    const { line, points } = trendGeometry([10, 20, null, 40, 50]);
    expect(points).toHaveLength(4);
    expect(line.match(/M/g)).toHaveLength(2);
  });

  it('keeps isolated days as points without a line', () => {
    const { line, points } = trendGeometry([null, 40, null]);
    expect(points).toHaveLength(1);
    expect(line).toBe('');
  });

  it('handles no data and a single value', () => {
    expect(trendGeometry([null, null]).points).toEqual([]);
    expect(trendGeometry([50]).points).toHaveLength(1);
  });

  it('puts higher values higher on the chart', () => {
    const { points } = trendGeometry([10, 90]);
    expect(points[1].y).toBeLessThan(points[0].y);
  });
});

describe('radar', () => {
  it('puts the first area straight up', () => {
    const [x, y] = radarPoint(0, 100);
    expect(x).toBeCloseTo(230);
    expect(y).toBeCloseTo(70);
  });

  it('collapses missing values to the center', () => {
    const polygon = radarPolygon(AREAS.map(() => null));
    expect(new Set(polygon.split(' ')).size).toBe(1);
  });
});

describe('heatLevel', () => {
  it.each([
    [null, 'empty'],
    [0, 'h1'],
    [29.9, 'h1'],
    [30, 'h2'],
    [54.9, 'h2'],
    [55, 'h3'],
    [77.9, 'h3'],
    [78, 'h4'],
    [100, 'h4'],
  ])('maps %s to %s', (value, level) => {
    expect(heatLevel(value)).toBe(level);
  });
});

describe('buildHeatGrid', () => {
  const today = '2026-10-21';
  const scores = new Map([
    ['2026-10-20', 80],
    ['2026-10-19', 10],
  ]);
  const grid = buildHeatGrid(today, scores, 26);
  const cells = grid.columns.flatMap((column) => column.cells);

  it('has 26 weeks of 7 rows', () => {
    expect(grid.columns).toHaveLength(26);
    expect(grid.columns.every((column) => column.cells.length === 7)).toBe(true);
  });

  it('starts every column on a Monday and ends in the current week', () => {
    const last = grid.columns[25];
    expect(last.monday).toBe('2026-10-19');
    expect(last.cells.map((cell) => cell.kind)).toEqual([
      'filled',
      'filled',
      'today',
      'future',
      'future',
      'future',
      'future',
    ]);
  });

  it('marks unfilled past days as empty, never as a low score', () => {
    const empty = cells.find((cell) => cell.day === '2026-10-18');
    expect(empty.kind).toBe('empty');
    expect(empty.level).toBeUndefined();
  });

  it('counts filled days and elapsed days up to today', () => {
    expect(grid.filled).toBe(2);
    expect(grid.elapsed).toBe(cells.filter((cell) => cell.kind !== 'future').length);
  });

  it('assigns color levels from the overall score', () => {
    expect(cells.find((cell) => cell.day === '2026-10-20').level).toBe('h4');
    expect(cells.find((cell) => cell.day === '2026-10-19').level).toBe('h1');
  });

  it('shows today as an open cell once it is filled in', () => {
    const filledToday = buildHeatGrid(today, new Map([[today, 60]]), 4);
    const cell = filledToday.columns[3].cells[2];
    expect(cell.kind).toBe('filled');
    expect(cell.level).toBe('h3');
  });
});
