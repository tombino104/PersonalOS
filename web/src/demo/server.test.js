import { describe, expect, it } from 'vitest';
import { createDemoServer } from './server.js';
import { addDays, format, occurrences } from './dates.js';

const NOON = new Date(2026, 9, 21, 12, 0);

function demo(options = {}) {
  const clock = { now: NOON };
  const server = createDemoServer({ now: () => clock.now, ...options });
  const call = (method, path, body) => {
    const [pathname, search = ''] = path.split('?');
    return server.handle(method, pathname, new URLSearchParams(search), body);
  };
  return { call, clock };
}

const TODAY = format(NOON);

describe('demo server', () => {
  it('starts signed in with a few months of history', () => {
    const { call } = demo();
    expect(call('GET', '/auth/me').data).toEqual({ name: 'Demo' });
    expect(call('GET', '/today').data).toEqual({ day: TODAY, report_opens_at: null });
    const scores = call('GET', '/scores').data.days;
    expect(scores.length).toBeGreaterThan(50);
    expect(scores.every((day) => day.areas.length === 6)).toBe(true);
    expect(call('GET', '/stats/areas').data.filled_days).toBeGreaterThan(50);
  });

  it('keeps today empty until the questionnaire is opened and completed', () => {
    const { call } = demo();
    expect(call('GET', `/reports/${TODAY}`).status).toBe(404);
    const opened = call('POST', '/reports', { day: TODAY });
    expect(opened.status).toBe(201);
    expect(opened.data.completed).toBe(false);
    const first = opened.data.completions[0];
    expect(call('PUT', `/reports/${TODAY}/completions/${first.activity_id}`, { done: true }).data.done).toBe(true);
    const done = call('POST', `/reports/${TODAY}/complete`).data;
    expect(done.completed).toBe(true);
    expect(done.scores.find((entry) => entry.area === first.area).obtained).toBe(first.weight);
    expect(call('POST', '/reports', { day: TODAY }).status).toBe(200);
  });

  it('leaves an area with nothing scheduled empty, not zero', () => {
    const { call } = demo();
    for (const item of call('GET', '/activities').data.activities) {
      call('PATCH', `/activities/${item.id}`, { archived: true });
    }
    const created = call('POST', '/activities', { area: 'physical', name: 'Gym', weight: 2, days: [0] });
    expect(created.status).toBe(201);
    const opened = call('POST', '/reports', { day: TODAY }).data;
    expect(opened.completions).toEqual([]);
    const complete = call('POST', `/reports/${TODAY}/complete`).data;
    expect(complete.scores.every((entry) => entry.score === null)).toBe(true);
    expect(complete.overall).toBeNull();
  });

  it('refuses reports for the future, closed days and bad input', () => {
    const { call } = demo();
    expect(call('POST', '/reports', { day: addDays(TODAY, 1) }).data.error.code).toBe('future_day');
    expect(call('POST', '/reports', { day: addDays(TODAY, -200) }).data.error.code).toBe('report_closed');
    expect(call('POST', '/activities', { area: 'physical', name: ' ', weight: 2 }).status).toBe(422);
    expect(call('POST', '/activities', { area: 'nope', name: 'X', weight: 2 }).data.error.code).toBe('unknown_area');
    expect(call('PATCH', '/activities/9999', { weight: 1 }).status).toBe(404);
  });

  it('applies the optional report time lock', () => {
    const { call, clock } = demo();
    call('PATCH', '/settings', { report_lock: true, report_time: '20:00' });
    expect(call('GET', '/today').data.report_opens_at).toBe('20:00');
    expect(call('POST', '/reports', { day: TODAY }).data.error.code).toBe('report_not_open');
    clock.now = new Date(2026, 9, 21, 20, 30);
    expect(call('POST', '/reports', { day: TODAY }).status).toBe(201);
    expect(call('PATCH', '/settings', { report_time: '8pm' }).data.error.code).toBe('invalid_report_time');
  });

  it('syncs a draft with the current activities', () => {
    const { call } = demo();
    call('POST', '/reports', { day: TODAY });
    call('POST', '/activities', { area: 'career', name: 'Inbox zero', weight: 1 });
    const synced = call('POST', `/reports/${TODAY}/sync`).data;
    expect(synced.completions.some((item) => item.name === 'Inbox zero')).toBe(true);
  });

  it('serves the three plugins and their data', () => {
    const { call } = demo();
    const plugins = call('GET', '/plugins').data.plugins;
    expect(plugins.map((plugin) => plugin.id)).toEqual(['calendar', 'mood', 'quotes']);
    expect(plugins.every((plugin) => plugin.active)).toBe(true);
    const events = call('GET', `/plugins/calendar/events?start=${TODAY}&end=${addDays(TODAY, 30)}`).data;
    expect(events.occurrences.length).toBeGreaterThan(3);
    const created = call('POST', '/plugins/calendar/events', { title: 'Run', day: TODAY, repeat: 'weekly' });
    expect(created.status).toBe(201);
    expect(call('DELETE', `/plugins/calendar/events/${created.data.id}`).data).toEqual({ ok: true });
    const summary = call('GET', '/plugins/mood/summary?days=30').data;
    expect(summary.distribution).toHaveLength(5);
    call('POST', '/plugins/mood/deactivate');
    expect(call('GET', '/plugins/mood/summary').data.error.code).toBe('plugin_inactive');
  });

  it('turns off what a static demo cannot do', () => {
    const { call } = demo();
    expect(call('POST', '/backups').data.error.code).toBe('demo');
    expect(call('PUT', '/profile/photo').data.error.code).toBe('invalid_photo');
  });

  it('erases everything and goes back to the welcome flow', () => {
    const { call } = demo();
    expect(call('POST', '/auth/reset', { code: 'x' }).data).toEqual({ setup_required: true });
    expect(call('GET', '/auth/me').status).toBe(401);
    expect(call('GET', '/auth/status').data).toEqual({ setup_required: true, setup_code_required: false });
    expect(call('POST', '/auth/setup', { name: 'Sam', password: 'longenough' }).data).toEqual({ name: 'Sam' });
    expect(call('GET', '/reports').data.reports).toEqual([]);
    expect(call('GET', '/activities').data.activities.length).toBeGreaterThan(5);
  });

  it('can start empty after an erase and a reload', () => {
    const { call } = demo({ empty: true });
    expect(call('GET', '/auth/status').data.setup_required).toBe(true);
  });
});

describe('occurrences', () => {
  it('repeats weekly, monthly and yearly, clamping short months', () => {
    expect(occurrences('2026-01-05', 'weekly', null, '2026-01-19', '2026-02-02')).toEqual(['2026-01-19', '2026-01-26', '2026-02-02']);
    expect(occurrences('2026-01-31', 'monthly', null, '2026-02-01', '2026-03-31')).toEqual(['2026-02-28', '2026-03-31']);
    expect(occurrences('2024-02-29', 'yearly', null, '2026-01-01', '2026-12-31')).toEqual(['2026-02-28']);
    expect(occurrences('2026-03-01', 'none', null, '2026-01-01', '2026-02-01')).toEqual([]);
  });
});
