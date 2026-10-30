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
    expect(call('GET', '/today').data).toEqual({ day: TODAY, report_opens_at: null, first_day: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) });
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

  it('keeps a completed report in step with the activities while it can be edited', () => {
    const { call } = demo();
    call('POST', '/reports', { day: TODAY });
    call('POST', `/reports/${TODAY}/complete`);
    call('POST', '/activities', { area: 'career', name: 'Inbox zero', weight: 3, description: ' Empty it ' });
    const synced = call('POST', `/reports/${TODAY}/sync`).data;
    const added = synced.completions.find((item) => item.name === 'Inbox zero');
    expect(added.description).toBe('Empty it');
    expect(synced.completed).toBe(true);
    expect(synced.scores.find((entry) => entry.area === 'career').maximum).toBeGreaterThanOrEqual(3);
  });

  it('deletes only archived activities and keeps their history', () => {
    const { call } = demo();
    const used = call('GET', '/activities').data.activities[0];
    expect(call('DELETE', `/activities/${used.id}`).data.error.code).toBe('activity_not_archived');
    call('PATCH', `/activities/${used.id}`, { archived: true });
    expect(call('DELETE', `/activities/${used.id}`).data).toEqual({ id: used.id, kept_in_history: true });
    const listed = call('GET', '/activities?include_archived=true').data.activities;
    expect(listed.some((item) => item.id === used.id)).toBe(false);
    expect(call('PATCH', `/activities/${used.id}`, { weight: 1 }).status).toBe(404);
    const fresh = call('POST', '/activities', { area: 'career', name: 'Never used', weight: 1 }).data.activity;
    call('PATCH', `/activities/${fresh.id}`, { archived: true });
    expect(call('DELETE', `/activities/${fresh.id}`).data.kept_in_history).toBe(false);
  });

  it('saves a custom dock and refuses an invalid one', () => {
    const { call } = demo();
    expect(call('GET', '/settings').data.dock).toBeNull();
    const keys = ['questionnaire', 'journal:journal', 'more'];
    expect(call('PATCH', '/settings', { dock: keys }).data.dock).toEqual(keys);
    expect(call('PATCH', '/settings', { dock: ['home', 'more'] }).data.error.code).toBe('invalid_dock');
    expect(call('PATCH', '/settings', { dock: ['questionnaire', 'Bad Key', 'more'] }).status).toBe(422);
    expect(call('PATCH', '/settings', { dock: [] }).data.dock).toBeNull();
  });

  it('counts a weekly goal only once it can no longer be met', () => {
    const { call } = demo();
    for (const item of call('GET', '/activities').data.activities) {
      call('PATCH', `/activities/${item.id}`, { archived: true });
    }
    call('POST', '/activities', { area: 'physical', name: 'Gym', weight: 2, times_per_week: 7 });
    const opened = call('POST', '/reports', { day: TODAY }).data;
    expect(opened.completions[0].weekly).toMatchObject({ target: 7, forced: true });
    const complete = call('POST', `/reports/${TODAY}/complete`).data;
    expect(complete.scores.find((entry) => entry.area === 'physical').maximum).toBe(2);
    const free = call('POST', '/activities', { area: 'career', name: 'Study', weight: 1, times_per_week: 1 }).data.activity;
    expect(call('PATCH', `/activities/${free.id}`, { times_per_week: 9 }).status).toBe(422);
  });

  it('summarizes a week and keeps a note for it', () => {
    const { call } = demo();
    const monday = addDays(TODAY, -2);
    const week = call('GET', `/reviews/${monday}`).data;
    expect(week.days).toHaveLength(7);
    expect(week.areas).toHaveLength(6);
    expect(week.is_current).toBe(true);
    expect(week.filled_days).toBeGreaterThan(0);
    expect(call('PUT', `/reviews/${monday}/note`, { text: ' Keep the mornings ' }).data).toEqual({ note: 'Keep the mornings' });
    expect(call('GET', `/reviews/${monday}`).data.note).toBe('Keep the mornings');
    expect(call('PUT', `/reviews/${monday}/note`, { text: '  ' }).data).toEqual({ note: null });
    expect(call('GET', `/reviews/${addDays(monday, 1)}`).data.error.code).toBe('invalid_week');
    expect(call('GET', `/reviews/${addDays(monday, 7)}`).data.error.code).toBe('future_week');
  });

  it('summarizes a month and a year', () => {
    const { call } = demo();
    const month = call('GET', '/recaps/2026-09').data;
    expect(month.kind).toBe('month');
    expect(month.days).toHaveLength(30);
    expect(month.filled_days).toBeGreaterThan(0);
    expect(month.areas).toHaveLength(6);
    expect(month.top_habits.length).toBeGreaterThan(0);
    expect(month.previous_filled_days).toBeGreaterThan(0);
    const current = call('GET', '/recaps/2026-10').data;
    expect(current.is_current).toBe(true);
    expect(current.elapsed_days).toBe(21);
    const year = call('GET', '/recaps/2026').data;
    expect(year.kind).toBe('year');
    expect(year.months).toHaveLength(10);
    expect(year.filled_days).toBeGreaterThan(month.filled_days);
    expect(call('GET', '/recaps/2026-13').data.error.code).toBe('invalid_period');
    expect(call('GET', '/recaps/2026-11').data.error.code).toBe('future_period');
  });

  it('keeps a list of people with birthdays', () => {
    const { call } = demo();
    const listing = call('GET', '/plugins/people/people').data.people;
    expect(listing.length).toBeGreaterThan(2);
    expect(listing[0].days_until).toBe(3);
    expect(listing[listing.length - 1].days_until).toBeNull();
    const created = call('POST', '/plugins/people/people', { name: ' Casey ', birthday: '02-29' });
    expect(created.status).toBe(201);
    expect(created.data).toMatchObject({ name: 'Casey', birthday: '02-29' });
    expect(call('POST', '/plugins/people/people', { name: 'x', birthday: '02-30' }).status).toBe(422);
    expect(call('POST', '/plugins/people/people', { name: '  ' }).status).toBe(422);
    const changed = call('PUT', `/plugins/people/people/${created.data.id}`, { name: 'Casey R.', birthday: null });
    expect(changed.data).toMatchObject({ name: 'Casey R.', birthday: null, days_until: null });
    expect(call('DELETE', `/plugins/people/people/${created.data.id}`).data).toEqual({ ok: true });
    expect(call('DELETE', `/plugins/people/people/${created.data.id}`).status).toBe(404);
  });

  it('syncs a draft with the current activities', () => {
    const { call } = demo();
    call('POST', '/reports', { day: TODAY });
    call('POST', '/activities', { area: 'career', name: 'Inbox zero', weight: 1 });
    const synced = call('POST', `/reports/${TODAY}/sync`).data;
    expect(synced.completions.some((item) => item.name === 'Inbox zero')).toBe(true);
  });

  it('serves the plugins and their data', () => {
    const { call } = demo();
    const plugins = call('GET', '/plugins').data.plugins;
    expect(plugins.map((plugin) => plugin.id)).toEqual(['calendar', 'health', 'journal', 'mood', 'people', 'quotes']);
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
    const steps = call('GET', '/plugins/health/days?limit=5').data.days;
    expect(steps).toHaveLength(5);
    expect(steps[0].day > steps[1].day).toBe(true);
  });

  it('keeps a journal with search, paging and edits', () => {
    const { call } = demo();
    const listing = call('GET', '/plugins/journal/entries').data;
    expect(listing.total).toBeGreaterThan(3);
    expect(listing.entries[0].day >= listing.entries[1].day).toBe(true);
    const created = call('POST', '/plugins/journal/entries', { body: ' Found my rhythm ', title: ' Rhythm ' });
    expect(created.status).toBe(201);
    expect(created.data).toMatchObject({ body: 'Found my rhythm', title: 'Rhythm', day: TODAY });
    expect(call('GET', '/plugins/journal/entries?q=RHYTHM').data.total).toBe(1);
    const one = call('GET', `/plugins/journal/entries?start=${TODAY}&end=${TODAY}`).data;
    expect(one.total).toBe(1);
    expect(one.entries[0].day).toBe(TODAY);
    expect(call('POST', '/plugins/journal/entries', { body: '  ' }).status).toBe(422);
    expect(call('POST', '/plugins/journal/entries', { body: 'x', day: addDays(TODAY, 1) }).status).toBe(422);
    const changed = call('PUT', `/plugins/journal/entries/${created.data.id}`, { body: 'Changed' });
    expect(changed.data.body).toBe('Changed');
    expect(call('GET', '/plugins/journal/entries?limit=2&offset=1').data.entries).toHaveLength(2);
    expect(call('DELETE', `/plugins/journal/entries/${created.data.id}`).data).toEqual({ ok: true });
    expect(call('GET', `/plugins/journal/entries/${created.data.id}`).status).toBe(404);
  });

  it('turns off what a static demo cannot do', () => {
    const { call } = demo();
    expect(call('POST', '/backups').data.error.code).toBe('demo');
    expect(call('GET', '/export').data.error.code).toBe('demo');
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
