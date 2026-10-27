import { addDays, weekdayIndex } from './dates.js';

export const AREAS = ['physical', 'discipline', 'social', 'intellect', 'career', 'mindset'];

const TREND = { x0: 8, x1: 296, yBase: 100, yHeight: 88 };

export function trendGeometry(values) {
  const count = values.length;
  const step = count > 1 ? (TREND.x1 - TREND.x0 - 16) / (count - 1) : 0;
  const x = (index) => TREND.x0 + 8 + index * step;
  const y = (value) => TREND.yBase - (value / 100) * TREND.yHeight;
  const points = [];
  const runs = [];
  let run = [];
  values.forEach((value, index) => {
    if (value === null || value === undefined) {
      if (run.length) runs.push(run);
      run = [];
      return;
    }
    const point = { x: x(index), y: y(value) };
    points.push(point);
    run.push(point);
  });
  if (run.length) runs.push(run);
  return { points, runs, ...trendPaths(runs) };
}

function trendPaths(runs) {
  const fixed = (number) => number.toFixed(1);
  let area = '';
  let line = '';
  for (const part of runs) {
    if (part.length < 2) continue;
    const last = part[part.length - 1];
    area += `M${fixed(part[0].x)} ${TREND.yBase} ${part.map((p) => `L${fixed(p.x)} ${fixed(p.y)}`).join(' ')} L${fixed(last.x)} ${TREND.yBase} Z `;
    line += `M${part.map((p) => `${fixed(p.x)} ${fixed(p.y)}`).join(' L')} `;
  }
  return { area: area.trim(), line: line.trim() };
}

const clamp = (value) => Math.min(1, Math.max(0, value));
const EPSILON = 1e-9;

export const easeInOut = (progress) => (1 - Math.cos(Math.PI * clamp(progress))) / 2;

function popScale(tip, index) {
  return clamp((tip - index) * 3 + 1);
}

function cut(points, tip, start) {
  const reached = Math.min(points.length, Math.max(0, Math.floor(tip - start + EPSILON) + 1));
  const shown = points.slice(0, reached);
  const fraction = tip - (start + reached - 1);
  if (reached > 0 && reached < points.length && fraction > EPSILON) {
    const from = points[reached - 1];
    const to = points[reached];
    shown.push({ x: from.x + (to.x - from.x) * fraction, y: from.y + (to.y - from.y) * fraction });
  }
  return shown;
}

export function trendFrame(geometry, progress) {
  const total = geometry.points.length;
  const tip = total > 1 ? clamp(progress) * (total - 1) : 0;
  const runs = [];
  let start = 0;
  for (const run of geometry.runs) {
    runs.push(cut(run, tip, start));
    start += run.length;
  }
  return {
    ...trendPaths(runs),
    scales: geometry.points.map((_, index) => (total > 1 ? popScale(tip, index) : clamp(progress * 3))),
  };
}

const RADAR = { center: 230, radius: 160 };

export function radarPoint(index, value, radius = null) {
  const angle = ((-90 + 60 * index) * Math.PI) / 180;
  const distance = radius ?? (RADAR.radius * value) / 100;
  return [RADAR.center + distance * Math.cos(angle), RADAR.center + distance * Math.sin(angle)];
}

const pair = (point) => `${point[0].toFixed(1)},${point[1].toFixed(1)}`;

export function radarPolygon(values) {
  return values.map((value, index) => pair(radarPoint(index, value ?? 0))).join(' ');
}

export function radarFrame(values, progress) {
  const corners = values.map((value, index) => {
    const [x, y] = radarPoint(index, value ?? 0);
    return { x, y };
  });
  const closed = [...corners, corners[0]];
  const tip = clamp(progress) * (closed.length - 1);
  const shown = cut(closed, tip, 0);
  const text = shown.map((point) => pair([point.x, point.y])).join(' ');
  return {
    outline: text,
    scales: corners.map((_, index) => popScale(tip, index)),
  };
}

export function radarRings() {
  return [25, 50, 75, 100].map((level) =>
    AREAS.map((_, index) => pair(radarPoint(index, level))).join(' '),
  );
}

export function radarAxes() {
  return AREAS.map((_, index) => {
    const [x, y] = radarPoint(index, 100);
    return { x2: x.toFixed(1), y2: y.toFixed(1) };
  });
}

export function radarLabel(index) {
  const [x, y] = radarPoint(index, 0, RADAR.radius + 26);
  const cosine = Math.cos(((-90 + 60 * index) * Math.PI) / 180);
  const anchor = cosine > 0.2 ? 'start' : cosine < -0.2 ? 'end' : 'middle';
  return { x: x.toFixed(1), y: y.toFixed(1), anchor };
}

export function heatLevel(overall) {
  if (overall === null || overall === undefined) return 'empty';
  if (overall < 30) return 'h1';
  if (overall < 55) return 'h2';
  if (overall < 78) return 'h3';
  return 'h4';
}

export function buildHeatGrid(today, overallByDay, weeks = 26) {
  const currentMonday = addDays(today, -weekdayIndex(today));
  const firstMonday = addDays(currentMonday, -7 * (weeks - 1));
  const columns = [];
  let filled = 0;
  let elapsed = 0;
  for (let week = 0; week < weeks; week += 1) {
    const monday = addDays(firstMonday, week * 7);
    const cells = [];
    for (let row = 0; row < 7; row += 1) {
      const day = addDays(monday, row);
      if (day > today) {
        cells.push({ day, kind: 'future' });
        continue;
      }
      elapsed += 1;
      if (day === today && !overallByDay.has(day)) {
        cells.push({ day, kind: 'today' });
      } else if (overallByDay.has(day)) {
        filled += 1;
        const overall = overallByDay.get(day);
        cells.push({ day, kind: 'filled', overall, level: heatLevel(overall) });
      } else {
        cells.push({ day, kind: 'empty' });
      }
    }
    columns.push({ monday, cells });
  }
  return { columns, filled, elapsed };
}
