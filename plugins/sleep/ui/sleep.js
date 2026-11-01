export const DEFAULT_TARGET = 420;
export const RISE_MINUTES = 18.2 * 60;
export const FALL_MINUTES = 4.2 * 60;
export const WINDOW_DAYS = 4;
export const STALE_AWAKE_MINUTES = 36 * 60;
export const RECENT_NIGHTS = 7;

const DAY_MINUTES = 1440;
const START_PRESSURE = 0.75;

export function toMinutes(time) {
  const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(time ?? '');
  return match ? Number(match[1]) * 60 + Number(match[2]) : null;
}

export function toTime(minutes) {
  const wrapped = ((Math.round(minutes) % DAY_MINUTES) + DAY_MINUTES) % DAY_MINUTES;
  return `${String(Math.floor(wrapped / 60)).padStart(2, '0')}:${String(wrapped % 60).padStart(2, '0')}`;
}

export function nightMinutes(night) {
  const start = toMinutes(night?.lights_off);
  const end = toMinutes(night?.woke_up);
  if (start === null || end === null) return null;
  return end > start ? end - start : end - start + DAY_MINUTES;
}

export function hoursText(minutes) {
  const total = Math.round(minutes);
  const hours = Math.floor(total / 60);
  const rest = total % 60;
  return rest === 0 ? `${hours}h` : `${hours}h ${String(rest).padStart(2, '0')}m`;
}

export function localDay(date = new Date()) {
  const pad = (number) => String(number).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function localTime(date = new Date()) {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

export function nightOfLightsOff(date = new Date()) {
  const next = new Date(date.getFullYear(), date.getMonth(), date.getDate() + (date.getHours() >= 12 ? 1 : 0));
  return localDay(next);
}

function dayStart(day) {
  const [year, month, date] = day.split('-').map(Number);
  return Math.round(Date.UTC(year, month - 1, date) / 60000);
}

export function wallMinutes(date) {
  return Math.round(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours(), date.getMinutes()) / 60000);
}

export function spanOf(night, target = DEFAULT_TARGET) {
  const wake = toMinutes(night.woke_up);
  if (wake === null) return null;
  const end = dayStart(night.day) + wake;
  const start = toMinutes(night.lights_off);
  if (start === null) return { off: end - target, wake: end, estimated: true };
  const length = nightMinutes(night);
  return { off: end - length, wake: end, estimated: false };
}

function rise(pressure, minutes) {
  return 1 - (1 - pressure) * Math.exp(-minutes / RISE_MINUTES);
}

function fall(pressure, minutes) {
  return pressure * Math.exp(-minutes / FALL_MINUTES);
}

export function batteryAt(nights, now, target = DEFAULT_TARGET) {
  const spans = nights
    .map((night) => spanOf(night, target))
    .filter((span) => span && span.wake <= now && span.wake >= now - WINDOW_DAYS * DAY_MINUTES)
    .sort((a, b) => a.wake - b.wake);
  if (spans.length === 0) return null;
  const last = spans[spans.length - 1];
  if (now - last.wake > STALE_AWAKE_MINUTES) return null;
  let pressure = START_PRESSURE;
  let clock = spans[0].off;
  for (const span of spans) {
    const off = Math.max(span.off, clock);
    pressure = rise(pressure, off - clock);
    pressure = fall(pressure, Math.max(span.wake - off, 0));
    clock = Math.max(span.wake, clock);
  }
  pressure = rise(pressure, now - clock);
  return {
    percent: Math.max(0, Math.min(100, Math.round((1 - pressure) * 100))),
    awake: now - last.wake,
    estimated: last.estimated,
  };
}

function latest(nights, count) {
  return [...nights].sort((a, b) => (a.day < b.day ? 1 : -1)).slice(0, count);
}

export function averageMinutes(nights, count = RECENT_NIGHTS) {
  const lengths = latest(nights, count)
    .map(nightMinutes)
    .filter((minutes) => minutes !== null);
  if (lengths.length < 2) return null;
  return Math.round(lengths.reduce((sum, minutes) => sum + minutes, 0) / lengths.length);
}

export function bedtimeRange(nights, count = RECENT_NIGHTS) {
  const times = latest(nights, count)
    .map((night) => toMinutes(night.lights_off))
    .filter((minutes) => minutes !== null)
    .map((minutes) => (minutes < 720 ? minutes + DAY_MINUTES : minutes));
  if (times.length < 3) return null;
  const earliest = Math.min(...times);
  const latestTime = Math.max(...times);
  return { earliest: toTime(earliest), latest: toTime(latestTime), spread: latestTime - earliest, count: times.length };
}

export function lastNight(nights) {
  return latest(nights, nights.length).find((night) => nightMinutes(night) !== null) ?? null;
}
