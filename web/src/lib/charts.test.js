import { describe, expect, it } from 'vitest';
import {
  AREAS,
  buildHeatGrid,
  easeInOut,
  heatLevel,
  radarFrame,
  radarPoint,
  radarPolygon,
  trendFrame,
  trendGeometry,
} from './charts.js';

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

describe('trendFrame', () => {
  const geometry = trendGeometry([0, 100, 40, null, 80, 90]);

  it('shows only the first dot and no line at the start', () => {
    const frame = trendFrame(geometry, 0);
    expect(frame.line).toBe('');
    expect(frame.scales[0]).toBe(1);
    expect(frame.scales.slice(1).every((scale) => scale === 0)).toBe(true);
  });

  it('extends the line from point to point', () => {
    const early = trendFrame(geometry, 0.2);
    expect(early.line.match(/L/g)).toHaveLength(1);
    expect(early.scales[1]).toBeGreaterThan(0);
    expect(early.scales[2]).toBe(0);
    const later = trendFrame(geometry, 0.55);
    expect(later.line.match(/L/g)).toHaveLength(2);
    expect(later.scales[2]).toBe(1);
  });

  it('matches the full geometry at the end', () => {
    const frame = trendFrame(geometry, 1);
    expect(frame.line).toBe(geometry.line);
    expect(frame.area).toBe(geometry.area);
    expect(frame.scales.every((scale) => scale === 1)).toBe(true);
  });

  it('does not draw across a gap', () => {
    const frame = trendFrame(geometry, 1);
    expect(frame.line.match(/M/g)).toHaveLength(2);
  });

  it('shows a single point without a line', () => {
    const single = trendGeometry([null, 40, null]);
    expect(trendFrame(single, 1).scales).toEqual([1]);
    expect(trendFrame(single, 1).line).toBe('');
  });
});

describe('easeInOut', () => {
  it('runs from 0 to 1 and clamps', () => {
    expect(easeInOut(0)).toBe(0);
    expect(easeInOut(1)).toBe(1);
    expect(easeInOut(0.5)).toBeCloseTo(0.5);
    expect(easeInOut(2)).toBe(1);
    expect(easeInOut(-1)).toBe(0);
  });
});

describe('radarFrame', () => {
  const values = [100, 50, 80, 20, 60, 40];

  it('starts at the first corner and ends on the full shape', () => {
    expect(radarFrame(values, 0).outline.split(' ')).toHaveLength(1);
    expect(radarFrame(values, 0).scales[1]).toBe(0);
    const full = radarFrame(values, 1);
    expect(full.outline.split(' ')).toHaveLength(7);
    expect(full.outline.split(' ')[0]).toBe(full.outline.split(' ')[6]);
    expect(full.scales.every((scale) => scale === 1)).toBe(true);
  });

  it('adds one corner at a time', () => {
    const frame = radarFrame(values, 0.5);
    expect(frame.outline.split(' ').length).toBeGreaterThanOrEqual(4);
    expect(frame.scales[0]).toBe(1);
    expect(frame.scales[5]).toBe(0);
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
