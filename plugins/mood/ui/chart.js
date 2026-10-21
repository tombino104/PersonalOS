export const X0 = 48;
export const X1 = 704;

export const yFor = (value) => 190 - (value - 1) * 40;

export function buildChart(values) {
  const count = values.length;
  const step = count > 1 ? (X1 - X0) / (count - 1) : 0;
  const points = [];
  const gaps = [];
  let line = '';
  let drawing = false;
  values.forEach((value, index) => {
    const x = Number((X0 + index * step).toFixed(1));
    if (value === null || value === undefined) {
      gaps.push({ x });
      drawing = false;
      return;
    }
    const y = yFor(value);
    points.push({ x, y });
    line += `${drawing ? 'L' : 'M'}${x} ${y} `;
    drawing = true;
  });
  return {
    points,
    gaps,
    line: line.trim(),
    grid: [1, 2, 3, 4, 5].map((value) => ({ value, y: yFor(value) })),
  };
}

export function barWidths(counts) {
  const max = Math.max(...counts);
  return counts.map((count) => (max ? Math.round((count / max) * 100) : 0));
}

export function seriesFor(days, entries) {
  const byDay = new Map(entries.map((entry) => [entry.day, entry.value]));
  return days.map((day) => byDay.get(day) ?? null);
}
