export const PROMPT_COUNT = 8;
export const PAGE_SIZE = 30;
export const EXCERPT_LENGTH = 320;
export const SHEET_LENGTH = 220;
export const MEMORY_LENGTH = 200;
export const MAX_TILT = 2.2;
export const PIN_AREAS = ['physical', 'discipline', 'social', 'intellect', 'career', 'mindset'];

function seed(id) {
  const x = Math.sin(id * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

export function tiltFor(id) {
  return Math.round((seed(id) * 2 - 1) * MAX_TILT * 10) / 10;
}

export function pinFor(id) {
  return PIN_AREAS[Math.floor(seed(id + 7) * PIN_AREAS.length)];
}

export function groupByMonth(entries) {
  const groups = [];
  for (const entry of entries) {
    const month = entry.day.slice(0, 7);
    const last = groups[groups.length - 1];
    if (last && last.month === month) last.entries.push(entry);
    else groups.push({ month, entries: [entry] });
  }
  return groups;
}

export function excerpt(text, limit = EXCERPT_LENGTH) {
  if (text.length <= limit) return { text, truncated: false };
  const cut = text.slice(0, limit);
  const space = cut.lastIndexOf(' ');
  const end = space > limit * 0.6 ? space : limit;
  return { text: `${text.slice(0, end).trimEnd()}…`, truncated: true };
}

export function pickPrompt(random = Math.random()) {
  return Math.min(PROMPT_COUNT, Math.floor(random * PROMPT_COUNT) + 1);
}

export function mergeEntries(current, next) {
  const known = new Set(current.map((entry) => entry.id));
  return [...current, ...next.filter((entry) => !known.has(entry.id))];
}
