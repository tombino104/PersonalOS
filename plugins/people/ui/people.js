export function parseBirthday(value) {
  if (!value) return null;
  const match = /^(?:(\d{4})-)?(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  return { year: match[1] ? Number(match[1]) : null, month: Number(match[2]), day: Number(match[3]) };
}

export function toBirthday({ day, month, year }) {
  if (!day && !month && !year) return null;
  if (!day || !month) return undefined;
  const pad = (number) => String(number).padStart(2, '0');
  return year ? `${String(year).padStart(4, '0')}-${pad(month)}-${pad(day)}` : `${pad(month)}-${pad(day)}`;
}

export function whenKey(daysUntil) {
  if (daysUntil === null || daysUntil === undefined) return null;
  if (daysUntil === 0) return 'today';
  if (daysUntil === 1) return 'tomorrow';
  return 'inDays';
}
