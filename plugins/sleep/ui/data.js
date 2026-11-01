import { pluginRequest } from '$core/lib/api.js';
import { DEFAULT_TARGET } from './sleep.js';

export async function loadSleep() {
  const [listing, settings] = await Promise.all([
    pluginRequest('sleep', 'GET', '/nights?limit=30'),
    pluginRequest('sleep', 'GET', '/settings').catch(() => ({ target_minutes: DEFAULT_TARGET })),
  ]);
  return { nights: listing.nights, target: settings.target_minutes };
}
