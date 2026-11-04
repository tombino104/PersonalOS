import { pluginRequest } from '$core/lib/api.js';
import { DEFAULT_TARGET, localDay, localTime, nightOfLightsOff } from './sleep.js';

export async function loadSleep() {
  const [listing, settings] = await Promise.all([
    pluginRequest('sleep', 'GET', '/nights?limit=30'),
    pluginRequest('sleep', 'GET', '/settings').catch(() => ({ target_minutes: DEFAULT_TARGET })),
  ]);
  return { nights: listing.nights, target: settings.target_minutes };
}

export async function tapNow(field, date = new Date()) {
  const time = localTime(date);
  const day = field === 'lights_off' ? nightOfLightsOff(date) : localDay(date);
  await pluginRequest('sleep', 'PUT', `/nights/${day}`, { [field]: time });
  return time;
}
