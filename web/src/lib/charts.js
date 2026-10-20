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
  const fixed = (number) => number.toFixed(1);
  let area = '';
  let line = '';
  for (const part of runs) {
    if (part.length < 2) continue;
    const last = part[part.length - 1];
    area += `M${fixed(part[0].x)} ${TREND.yBase} ${part.map((p) => `L${fixed(p.x)} ${fixed(p.y)}`).join(' ')} L${fixed(last.x)} ${TREND.yBase} Z `;
    line += `M${part.map((p) => `${fixed(p.x)} ${fixed(p.y)}`).join(' L')} `;
  }
  return { points, area: area.trim(), line: line.trim() };
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
