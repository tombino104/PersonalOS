export const PROMPT_COUNT = 8;
export const PAGE_SIZE = 30;
export const EXCERPT_LENGTH = 320;

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
