const pad = (value) => String(value).padStart(2, '0');

export const format = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

export function parse(day) {
  const [year, month, date] = day.split('-').map(Number);
  return new Date(year, month - 1, date);
}

export function addDays(day, count) {
  const date = parse(day);
  date.setDate(date.getDate() + count);
  return format(date);
}

export const daysBetween = (from, to) => Math.round((parse(to) - parse(from)) / 86400000);

export const weekdayOf = (day) => (parse(day).getDay() + 6) % 7;

export function splitTime(text) {
  const [hours, minutes] = text.split(':').map(Number);
  return { hours, minutes };
}

export function logicalDay(now, cutoff) {
  const { hours, minutes } = splitTime(cutoff);
  return format(new Date(now.getTime() - (hours * 60 + minutes) * 60000));
}

export function editDeadline(day, cutoff) {
  const { hours, minutes } = splitTime(cutoff);
  const date = parse(day);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + 2, hours, minutes);
}

export function atTime(day, time) {
  const { hours, minutes } = splitTime(time);
  const date = parse(day);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), hours, minutes);
}

export const isTime = (value) => /^([01]\d|2[0-3]):[0-5]\d$/.test(value);

export const isDay = (value) => /^\d{4}-\d{2}-\d{2}$/.test(value) && format(parse(value)) === value;

export const clock = (date) => `${pad(date.getHours())}:${pad(date.getMinutes())}`;

export function occurrences(first, repeat, until, start, end) {
  const last = until && until < end ? until : end;
  if (last < start || last < first) return [];
  if (repeat === 'none') return start <= first && first <= last ? [first] : [];
  if (repeat === 'daily' || repeat === 'weekly') {
    const step = repeat === 'daily' ? 1 : 7;
    const skipped = Math.max(daysBetween(first, start), 0);
    let current = addDays(first, Math.ceil(skipped / step) * step);
    const days = [];
    while (current <= last) {
      days.push(current);
      current = addDays(current, step);
    }
    return days;
  }
  const earliest = first > start ? first : start;
  let [year, month] = earliest.split('-').map(Number);
  const [, firstMonth, firstDay] = first.split('-').map(Number);
  if (repeat === 'yearly') month = firstMonth;
  const days = [];
  for (;;) {
    const current = `${year}-${pad(month)}-${pad(Math.min(firstDay, new Date(year, month, 0).getDate()))}`;
    if (current > last) return days;
    if (current >= earliest) days.push(current);
    if (repeat === 'yearly') year += 1;
    else {
      month += 1;
      if (month > 12) {
        month = 1;
        year += 1;
      }
    }
  }
}
