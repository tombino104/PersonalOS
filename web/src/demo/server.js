import {
  addDays,
  atTime,
  clock,
  daysBetween,
  editDeadline,
  isDay,
  isTime,
  logicalDay,
  occurrences,
  weekdayOf,
} from './dates.js';
import { AREAS, completionsFor, sampleActivities, seedEvents, seedHistory, seedJournal } from './seed.js';

const manifests = import.meta.glob('../../../plugins/*/manifest.json', { eager: true, import: 'default' });

const MAX_RANGE_DAYS = 366;
const MAX_STATS_RANGE_DAYS = 3660;
const DEFAULT_RANGE_DAYS = 90;
const SOFT_LIMIT_PER_AREA = 5;
const CATEGORIES = ['personal', 'work', 'study', 'health', 'social', 'other'];
const REPEATS = ['none', 'daily', 'weekly', 'monthly', 'yearly'];
const KEEP = { auto: 7, manual: 20, 'before-restore': 5 };
const MAX_DOCK = 7;
const DOCK_KEY = /^[a-z0-9_]+(:[a-z0-9_]+)?$/;

class Failure extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const refuse = (status, code, message) => {
  throw new Failure(status, code, message);
};

const invalid = () => refuse(422, 'validation_error', 'invalid request');
const notFound = (message = 'not found') => refuse(404, 'not_found', message);
const unavailable = () => refuse(409, 'demo', 'This is not available in the demo.');

const mean = (values) => {
  const present = values.filter((value) => value !== null);
  return present.length ? present.reduce((sum, value) => sum + value, 0) / present.length : null;
};

const score = (maximum, obtained) => (maximum === 0 ? null : (obtained / maximum) * 100);

function browserZone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

function freshState() {
  return {
    signedIn: true,
    userCreated: true,
    userName: 'Demo',
    settings: {
      timezone: browserZone(),
      day_cutoff: '04:00',
      report_lock: false,
      report_time: '20:00',
      reminder_enabled: false,
      reminder_time: '21:00',
      backup_auto: true,
      backup_time: '03:00',
      home_period: 'week',
      home_areas: 'all',
      theme: null,
      language: null,
      dock: null,
    },
    profile: { display_name: null, about: null, birth_year: null, has_photo: false, version: null },
    activities: [],
    nextActivityId: 1,
    reports: new Map(),
    nextCompletionId: 1,
    plugins: Object.fromEntries(Object.values(manifests).map((manifest) => [manifest.id, { installed: true, active: true }])),
    events: [],
    nextEventId: 1,
    mood: new Map(),
    journal: [],
    nextEntryId: 1,
    reviews: new Map(),
  };
}

function describePlugin(state, manifest) {
  const row = state.plugins[manifest.id];
  const adds = manifest.adds ?? {};
  return {
    id: manifest.id,
    name: manifest.name,
    version: manifest.version,
    description: manifest.description,
    core_api: manifest.core_api,
    permissions: [...manifest.permissions].sort(),
    questionnaire_blocks: adds.questionnaire_blocks ?? [],
    report_sections: adds.report_sections ?? [],
    widgets: adds.widgets ?? [],
    pages: adds.pages ?? [],
    entries: (adds.entries ?? []).map(({ id, label, icon, placement, page }) => ({ id, label, icon, placement, page })),
    settings: Boolean(manifest.settings),
    default_active: Boolean(manifest.default_active),
    installed: Boolean(row),
    active: Boolean(row?.active),
    consecutive_errors: 0,
    message: null,
    state: row?.active ? 'active' : 'inactive',
  };
}

export function createDemoServer({ now = () => new Date(), version = 'demo', empty = false } = {}) {
  let state = freshState();
  const routes = [];

  const on = (method, pattern, handler) => {
    const source = pattern.replace(/:(\w+)/g, '(?<$1>[^/]+)').replace(/\*(\w+)/g, '(?<$1>.*)');
    routes.push({ method, matcher: new RegExp(`^${source}$`), handler });
  };

  const today = () => logicalDay(now(), state.settings.day_cutoff);

  function populate() {
    const current = today();
    seedHistory(state, current);
    seedEvents(state, current);
    seedJournal(state, current);
  }

  function blank() {
    state = freshState();
    state.signedIn = false;
    state.userCreated = false;
    state.userName = '';
    for (const id of Object.keys(state.plugins)) state.plugins[id].active = manifestOf(id).default_active === true;
    sampleActivities(state, now());
  }


  function opensAt(day) {
    if (!state.settings.report_lock) return null;
    return atTime(day, state.settings.report_time);
  }

  function requireOpenTime(day) {
    const moment = opensAt(day);
    if (moment && now() < moment) refuse(409, 'report_not_open', `the report opens at ${clock(moment)}`);
  }

  const deadlineOf = (day) => editDeadline(day, state.settings.day_cutoff);
  const isClosed = (day) => now() >= deadlineOf(day);

  function requireEditable(report) {
    if (isClosed(report.day)) refuse(409, 'report_closed', `report ${report.day} is closed`);
    requireOpenTime(report.day);
  }

  const reportOf = (day) => state.reports.get(day) ?? notFound(`no report for ${day}`);

  function weeklyProgress(report, item) {
    const start = addDays(report.day, -weekdayOf(report.day));
    let doneBefore = 0;
    for (const other of state.reports.values()) {
      if (!other.completedAt || other.day < start || other.day >= report.day) continue;
      if (other.completions.some((entry) => entry.activity_id === item.activity_id && entry.done)) doneBefore += 1;
    }
    const activity = state.activities.find((candidate) => candidate.id === item.activity_id);
    const daysLeft = (activity?.days ?? []).filter((weekday) => weekday >= weekdayOf(report.day)).length;
    return { target: item.target, done_before: doneBefore, forced: item.target - doneBefore >= daysLeft };
  }

  const isOptional = (report, item) => item.target != null && !weeklyProgress(report, item).forced;

  function scoresOf(report) {
    const counted = report.completions.filter((item) => item.done || !isOptional(report, item));
    return AREAS.map((area) => {
      const items = counted.filter((item) => item.area === area.slug);
      const maximum = items.reduce((sum, item) => sum + item.weight, 0);
      const obtained = items.reduce((sum, item) => sum + (item.done ? item.weight : 0), 0);
      return { area: area.slug, maximum, obtained, score: score(maximum, obtained) };
    });
  }

  function detail(report) {
    const closed = isClosed(report.day);
    const scores = report.completedAt ? scoresOf(report) : null;
    return {
      day: report.day,
      status: closed ? 'closed' : 'open',
      editable: !closed,
      completed: Boolean(report.completedAt),
      completed_at: report.completedAt ? report.completedAt.toISOString() : null,
      editable_until: deadlineOf(report.day).toISOString(),
      reflection: report.reflection,
      completions: report.completions.map((item) => ({
        activity_id: item.activity_id,
        name: item.name,
        description: state.activities.find((activity) => activity.id === item.activity_id)?.description ?? null,
        weight: item.weight,
        area: item.area,
        done: item.done,
        weekly: item.target == null ? null : weeklyProgress(report, item),
      })),
      scores,
      overall: scores ? mean(scores.map((entry) => entry.score)) : null,
    };
  }

  function range(query, limit = MAX_RANGE_DAYS) {
    const end = query.get('to') ?? today();
    const start = query.get('from') ?? addDays(end, -(DEFAULT_RANGE_DAYS - 1));
    if (!isDay(start) || !isDay(end)) invalid();
    if (start > end) refuse(422, 'invalid_range', "'from' must not be after 'to'");
    if (daysBetween(start, end) >= limit) {
      refuse(422, 'invalid_range', `range cannot exceed ${limit} days`);
    }
    return [start, end];
  }

  function completedIn(start, end) {
    return [...state.reports.values()]
      .filter((report) => report.completedAt && report.day >= start && report.day <= end)
      .sort((a, b) => (a.day < b.day ? -1 : 1));
  }

  const activityOf = (id) =>
    state.activities.find((activity) => activity.id === Number(id) && !activity.deleted_at) ??
    notFound(`activity ${id} not found`);

  function warnings() {
    return AREAS.map((area) => ({
      area: area.slug,
      count: state.activities.filter((item) => item.area === area.slug && !item.archived_at).length,
    }))
      .filter((entry) => entry.count > SOFT_LIMIT_PER_AREA)
      .map((entry) => ({
        code: 'too_many_activities',
        area: entry.area,
        count: entry.count,
        suggested_max: SOFT_LIMIT_PER_AREA,
      }));
  }

  const publicActivity = (activity) => ({ ...activity, days: [...activity.days].sort() });

  function checkDays(days) {
    if (!Array.isArray(days) || days.length === 0 || new Set(days).size !== days.length) invalid();
    if (days.some((day) => !Number.isInteger(day) || day < 0 || day > 6)) invalid();
    return [...days].sort();
  }

  function checkName(name) {
    if (typeof name !== 'string') invalid();
    const clean = name.trim();
    if (clean.length < 1 || clean.length > 100) invalid();
    return clean;
  }

  function checkDescription(description) {
    if (description === undefined || description === null) return null;
    if (typeof description !== 'string' || description.trim().length > 300) invalid();
    return description.trim() || null;
  }

  function checkTimes(times) {
    if (times === undefined || times === null || times === 0) return null;
    if (!Number.isInteger(times) || times < 1 || times > 7) invalid();
    return times;
  }

  function checkWeight(weight) {
    if (![1, 2, 3].includes(weight)) invalid();
    return weight;
  }

  function checkArea(slug) {
    if (!AREAS.some((area) => area.slug === slug)) refuse(422, 'unknown_area', `unknown area: ${slug}`);
    return slug;
  }

  const active = (id) => Boolean(state.plugins[id]?.active);

  function requirePlugin(id) {
    if (!active(id)) refuse(404, 'plugin_inactive', 'this plugin is not active');
  }

  const manifestOf = (id) => Object.values(manifests).find((item) => item.id === id) ?? notFound(`plugin ${id} not found`);
  const pluginList = () => Object.values(manifests).map((item) => describePlugin(state, item)).sort((a, b) => (a.id < b.id ? -1 : 1));

  on('GET', '/info', () => ({ api: '1', version }));

  on('GET', '/auth/status', () => ({ setup_required: !state.userCreated, setup_code_required: false }));

  on('POST', '/auth/setup', ({ body }) => {
    if (state.userCreated) refuse(409, 'setup_done', 'the first account already exists');
    const name = String(body?.name ?? '').trim();
    if (!name || String(body?.password ?? '').length < 8) {
      refuse(422, 'weak_password', 'use at least 8 characters');
    }
    state.userCreated = true;
    state.signedIn = true;
    state.userName = name;
    return { name };
  });

  on('POST', '/auth/login', ({ body }) => {
    const name = String(body?.name ?? '').trim() || state.userName;
    state.signedIn = true;
    state.userName = name;
    return { name };
  });

  on('POST', '/auth/reset', () => {
    blank();
    return { setup_required: true };
  });

  const protectedRoute = (method, pattern, handler) =>
    on(method, pattern, (context) => {
      if (!state.signedIn) refuse(401, 'unauthorized', 'login required');
      return handler(context);
    });

  on('POST', '/auth/logout', () => {
    state.signedIn = false;
    return { ok: true };
  });

  protectedRoute('GET', '/auth/me', () => ({ name: state.userName }));
  protectedRoute('POST', '/auth/password', () => ({ ok: true }));

  protectedRoute('GET', '/today', () => {
    const day = today();
    const moment = opensAt(day);
    const locked = moment !== null && now() < moment;
    const first = [...state.reports.values()].filter((report) => report.completedAt).map((report) => report.day).sort()[0];
    return { day, report_opens_at: locked ? clock(moment) : null, first_day: first ?? null };
  });

  protectedRoute('GET', '/areas', () => ({ areas: AREAS.map((area) => ({ ...area })) }));

  protectedRoute('GET', '/settings', () => ({ ...state.settings }));

  protectedRoute('PATCH', '/settings', ({ body }) => {
    const changes = body ?? {};
    if (Object.values(changes).some((value) => value === null)) {
      refuse(422, 'validation_error', 'fields cannot be null');
    }
    for (const [key, code] of [
      ['day_cutoff', 'invalid_day_cutoff'],
      ['report_time', 'invalid_report_time'],
      ['backup_time', 'invalid_backup_time'],
      ['reminder_time', 'invalid_reminder_time'],
    ]) {
      if (key in changes && !isTime(changes[key])) refuse(422, code, 'expected a time like 20:00');
    }
    for (const key of [
      'timezone',
      'day_cutoff',
      'report_lock',
      'report_time',
      'reminder_enabled',
      'reminder_time',
      'backup_auto',
      'backup_time',
      'home_period',
      'home_areas',
      'theme',
      'language',
    ]) {
      if (key in changes) state.settings[key] = changes[key];
    }
    if ('dock' in changes) {
      const keys = changes.dock;
      if (!Array.isArray(keys) || keys.length > MAX_DOCK || keys.some((key) => !DOCK_KEY.test(key))) invalid();
      if (
        keys.length > 0 &&
        (new Set(keys).size !== keys.length || !keys.includes('questionnaire') || keys.at(-1) !== 'more')
      ) {
        refuse(422, 'invalid_dock', `the dock holds at most ${MAX_DOCK} different items, with the questionnaire in it and more last`);
      }
      state.settings.dock = keys.length ? keys : null;
    }
    return { ...state.settings };
  });

  protectedRoute('GET', '/profile', () => ({ ...state.profile }));

  protectedRoute('PUT', '/profile', ({ body }) => {
    for (const key of ['display_name', 'about', 'birth_year']) {
      if (key in (body ?? {})) state.profile[key] = body[key] || null;
    }
    state.profile.version = now().toISOString();
    return { ...state.profile };
  });

  protectedRoute('PUT', '/profile/photo', () => refuse(422, 'invalid_photo', 'Photos are turned off in the demo.'));
  protectedRoute('DELETE', '/profile/photo', () => ({ ...state.profile }));

  protectedRoute('GET', '/backups', () => ({ backups: [], keep: KEEP }));
  protectedRoute('GET', '/export', unavailable);
  protectedRoute('POST', '/backups', unavailable);
  protectedRoute('POST', '/backups/restore', unavailable);
  protectedRoute('POST', '/backups/:name/restore', unavailable);

  protectedRoute('GET', '/activities', ({ query }) => {
    const includeArchived = query.get('include_archived') === 'true';
    const order = new Map(AREAS.map((area) => [area.slug, area.position]));
    const items = state.activities
      .filter((activity) => !activity.deleted_at && (includeArchived || !activity.archived_at))
      .sort((a, b) => order.get(a.area) - order.get(b.area) || a.id - b.id)
      .map(publicActivity);
    return { activities: items, warnings: warnings() };
  });

  protectedRoute('POST', '/activities', ({ body }) => {
    const activity = {
      id: state.nextActivityId++,
      area: checkArea(body?.area),
      name: checkName(body?.name),
      description: checkDescription(body?.description),
      times_per_week: checkTimes(body?.times_per_week),
      weight: checkWeight(body?.weight),
      cadence: 'daily',
      days: body?.days == null ? [0, 1, 2, 3, 4, 5, 6] : checkDays(body.days),
      created_at: now().toISOString(),
      archived_at: null,
    };
    state.activities.push(activity);
    return { status: 201, data: { activity: publicActivity(activity), warnings: warnings() } };
  });

  protectedRoute('PATCH', '/activities/:id', ({ params, body }) => {
    const changes = body ?? {};
    if (Object.values(changes).some((value) => value === null)) {
      refuse(422, 'validation_error', 'fields cannot be null');
    }
    const activity = activityOf(params.id);
    if ('name' in changes) activity.name = checkName(changes.name);
    if ('description' in changes) activity.description = checkDescription(changes.description);
    if ('times_per_week' in changes) activity.times_per_week = checkTimes(changes.times_per_week);
    if ('area' in changes) activity.area = checkArea(changes.area);
    if ('weight' in changes) activity.weight = checkWeight(changes.weight);
    if ('days' in changes) activity.days = checkDays(changes.days);
    if ('archived' in changes) {
      activity.archived_at = changes.archived ? (activity.archived_at ?? now().toISOString()) : null;
    }
    return { activity: publicActivity(activity), warnings: warnings() };
  });

  protectedRoute('DELETE', '/activities/:id', ({ params }) => {
    const activity = activityOf(params.id);
    if (!activity.archived_at) refuse(409, 'activity_not_archived', 'archive the activity before deleting it');
    const used = [...state.reports.values()].some((report) =>
      report.completions.some((item) => item.activity_id === activity.id),
    );
    if (used) activity.deleted_at = now().toISOString();
    else state.activities = state.activities.filter((candidate) => candidate !== activity);
    return { id: activity.id, kept_in_history: used };
  });

  protectedRoute('POST', '/reports', ({ body }) => {
    const day = body?.day;
    if (!isDay(day)) invalid();
    const existing = state.reports.get(day);
    if (existing) return detail(existing);
    if (day > today()) refuse(422, 'future_day', 'cannot open a report for a future day');
    if (isClosed(day)) refuse(409, 'report_closed', `the edit window for ${day} has ended`);
    requireOpenTime(day);
    const report = { day, completedAt: null, reflection: null, completions: completionsFor(state, day) };
    state.reports.set(day, report);
    return { status: 201, data: detail(report) };
  });

  protectedRoute('GET', '/reports', ({ query }) => {
    const [start, end] = range(query);
    const items = [...state.reports.values()]
      .filter((report) => report.day >= start && report.day <= end)
      .sort((a, b) => (a.day < b.day ? 1 : -1))
      .map((report) => ({
        day: report.day,
        status: isClosed(report.day) ? 'closed' : 'open',
        completed: Boolean(report.completedAt),
        completed_at: report.completedAt ? report.completedAt.toISOString() : null,
        editable_until: deadlineOf(report.day).toISOString(),
      }));
    return { reports: items };
  });

  protectedRoute('GET', '/reports/:day', ({ params }) => detail(reportOf(params.day)));

  protectedRoute('PUT', '/reports/:day/completions/:activity', ({ params, body }) => {
    const report = reportOf(params.day);
    requireEditable(report);
    if (typeof body?.done !== 'boolean') invalid();
    const item = report.completions.find((entry) => entry.activity_id === Number(params.activity));
    if (!item) notFound(`activity ${params.activity} is not part of report ${report.day}`);
    item.done = body.done;
    return { activity_id: item.activity_id, done: body.done };
  });

  protectedRoute('PUT', '/reports/:day/reflection', ({ params, body }) => {
    const report = reportOf(params.day);
    requireEditable(report);
    if (!body || !('text' in body)) invalid();
    report.reflection = body.text;
    return { reflection: body.text };
  });

  protectedRoute('POST', '/reports/:day/sync', ({ params }) => {
    const report = reportOf(params.day);
    requireEditable(report);
    const weekday = weekdayOf(report.day);
    const known = new Map(state.activities.map((activity) => [activity.id, activity]));
    report.completions = report.completions.filter((item) => {
      const activity = known.get(item.activity_id);
      return activity && !activity.archived_at && activity.days.includes(weekday);
    });
    for (const item of report.completions) {
      const activity = known.get(item.activity_id);
      Object.assign(item, { name: activity.name, weight: activity.weight, area: activity.area, target: activity.times_per_week ?? null });
    }
    const present = new Set(report.completions.map((item) => item.activity_id));
    report.completions.push(...completionsFor(state, report.day).filter((item) => !present.has(item.activity_id)));
    const order = new Map(AREAS.map((area) => [area.slug, area.position]));
    report.completions.sort((a, b) => order.get(a.area) - order.get(b.area) || a.id - b.id);
    return detail(report);
  });

  protectedRoute('POST', '/reports/:day/complete', ({ params }) => {
    const report = reportOf(params.day);
    requireEditable(report);
    report.completedAt ??= now();
    return detail(report);
  });

  protectedRoute('GET', '/scores', ({ query }) => {
    const [start, end] = range(query);
    const days = completedIn(start, end).map((report) => {
      const areas = scoresOf(report);
      return { day: report.day, areas, overall: mean(areas.map((entry) => entry.score)) };
    });
    return { days };
  });

  protectedRoute('GET', '/stats/areas', ({ query }) => {
    const [start, end] = range(query, MAX_STATS_RANGE_DAYS);
    const reports = completedIn(start, end);
    return {
      filled_days: reports.length,
      areas: AREAS.map((area) => ({
        area: area.slug,
        average: mean(reports.map((report) => scoresOf(report).find((entry) => entry.area === area.slug).score)),
      })),
    };
  });

  protectedRoute('GET', '/stats/activities', ({ query }) => {
    const [start, end] = range(query, MAX_STATS_RANGE_DAYS);
    const stats = new Map();
    for (const report of completedIn(start, end)) {
      for (const item of report.completions) {
        const entry = stats.get(item.activity_id) ?? { activity_id: item.activity_id, done: 0, total: 0 };
        const activity = state.activities.find((candidate) => candidate.id === item.activity_id);
        Object.assign(entry, {
          name: item.name,
          weight: item.weight,
          area: item.area,
          archived: Boolean(activity?.archived_at),
        });
        entry.done += item.done ? 1 : 0;
        entry.total += 1;
        stats.set(item.activity_id, entry);
      }
    }
    const order = new Map(AREAS.map((area) => [area.slug, area.position]));
    const activities = [...stats.values()].sort(
      (a, b) => order.get(a.area) - order.get(b.area) || a.activity_id - b.activity_id,
    );
    return { activities };
  });

  function checkWeek(weekStart) {
    if (!isDay(weekStart) || weekdayOf(weekStart) !== 0) refuse(422, 'invalid_week', 'a week starts on a Monday');
    if (weekStart > today()) refuse(422, 'future_week', 'that week has not started yet');
  }

  function averagesOf(start, end) {
    const reports = completedIn(start, end);
    return {
      filled: reports.length,
      areas: AREAS.map((area) => ({
        area: area.slug,
        average: mean(reports.map((report) => scoresOf(report).find((entry) => entry.area === area.slug).score)),
      })),
    };
  }

  protectedRoute('GET', '/reviews/:week', ({ params }) => {
    const start = params.week;
    checkWeek(start);
    const end = addDays(start, 6);
    const current = averagesOf(start, end);
    const before = averagesOf(addDays(start, -7), addDays(start, -1));
    const previous = Object.fromEntries(before.areas.map((item) => [item.area, item.average]));
    const days = Array.from({ length: 7 }, (_, offset) => {
      const day = addDays(start, offset);
      const report = state.reports.get(day);
      const completed = Boolean(report?.completedAt);
      return {
        day,
        completed,
        overall: completed ? mean(scoresOf(report).map((entry) => entry.score)) : null,
        reflection: completed ? report.reflection : null,
      };
    });
    const stats = new Map();
    for (const report of completedIn(start, end)) {
      for (const item of report.completions) {
        const entry = stats.get(item.activity_id) ?? { activity_id: item.activity_id, done: 0, total: 0 };
        const activity = state.activities.find((candidate) => candidate.id === item.activity_id);
        Object.assign(entry, { name: item.name, weight: item.weight, area: item.area, archived: Boolean(activity?.archived_at) });
        entry.done += item.done ? 1 : 0;
        entry.total += 1;
        stats.set(item.activity_id, entry);
      }
    }
    const order = new Map(AREAS.map((area) => [area.slug, area.position]));
    return {
      week_start: start,
      week_end: end,
      is_current: start <= today() && today() <= end,
      filled_days: current.filled,
      previous_filled_days: before.filled,
      days,
      areas: current.areas.map((item) => ({ ...item, previous: previous[item.area] })),
      activities: [...stats.values()].sort((a, b) => order.get(a.area) - order.get(b.area) || a.activity_id - b.activity_id),
      note: state.reviews.get(start) ?? null,
    };
  });

  protectedRoute('PUT', '/reviews/:week/note', ({ params, body }) => {
    checkWeek(params.week);
    if (!body || !('text' in body) || (body.text !== null && typeof body.text !== 'string') || (body.text ?? '').length > 5000) invalid();
    const text = (body.text ?? '').trim() || null;
    if (text === null) state.reviews.delete(params.week);
    else state.reviews.set(params.week, text);
    return { note: text };
  });

  protectedRoute('GET', '/plugins', () => ({ plugins: pluginList() }));

  protectedRoute('POST', '/plugins/:id/activate', ({ params, body }) => {
    manifestOf(params.id);
    if (body?.accept_permissions !== true) {
      refuse(422, 'permissions_not_accepted', 'accept the permissions to turn the plugin on');
    }
    state.plugins[params.id] = { installed: true, active: true };
    return { plugins: pluginList() };
  });

  protectedRoute('POST', '/plugins/:id/deactivate', ({ params }) => {
    manifestOf(params.id);
    if (state.plugins[params.id]) state.plugins[params.id].active = false;
    return { plugins: pluginList() };
  });

  protectedRoute('POST', '/plugins/:id/remove-data', ({ params, body }) => {
    manifestOf(params.id);
    const row = state.plugins[params.id];
    if (!row) notFound(`plugin ${params.id} has no data to remove`);
    if (row.active) refuse(409, 'plugin_active', 'turn the plugin off before removing its data');
    if (body?.confirm !== params.id) refuse(422, 'confirmation_mismatch', 'type the plugin id to confirm');
    delete state.plugins[params.id];
    if (params.id === 'calendar') state.events = [];
    if (params.id === 'mood') state.mood = new Map();
    if (params.id === 'journal') state.journal = [];
    return { plugins: pluginList() };
  });

  const eventOf = (id) => state.events.find((event) => event.id === Number(id)) ?? notFound('event not found');

  function checkEvent(body) {
    const title = typeof body?.title === 'string' ? body.title.trim() : '';
    if (title.length < 1 || title.length > 120) invalid();
    if (!isDay(body.day) || body.day < '1970-01-01' || body.day > '2100-12-31') invalid();
    const time = body.time === '' ? null : (body.time ?? null);
    if (time !== null && !isTime(time)) invalid();
    const category = body.category ?? 'personal';
    const repeat = body.repeat ?? 'none';
    if (!CATEGORIES.includes(category) || !REPEATS.includes(repeat)) invalid();
    const until = body.until ?? null;
    if (until !== null && (!isDay(until) || until < '1970-01-01' || until > '2100-12-31')) invalid();
    const notes = typeof body.notes === 'string' ? body.notes.trim() || null : null;
    if (notes && notes.length > 500) invalid();
    if (until !== null && (repeat === 'none' || until < body.day)) {
      refuse(422, 'error', "'until' needs a repeat and cannot be before the day");
    }
    return { title, day: body.day, time, category, notes, repeat, until };
  }

  const guarded = (plugin, method, pattern, handler) =>
    protectedRoute(method, `/plugins/${plugin}${pattern}`, (context) => {
      requirePlugin(plugin);
      return handler(context);
    });

  guarded('calendar', 'GET', '/events', ({ query }) => {
    const start = query.get('start');
    const end = query.get('end');
    if (!isDay(start) || !isDay(end)) invalid();
    if (end < start || daysBetween(start, end) >= 100) refuse(422, 'error', 'the range must be 1 to 100 days');
    const found = [];
    for (const event of state.events) {
      if (event.until && event.until < start) continue;
      for (const day of occurrences(event.day, event.repeat, event.until, start, end)) {
        const { id, ...rest } = event;
        found.push({ ...rest, event_id: id, day });
      }
    }
    found.sort(
      (a, b) =>
        a.day.localeCompare(b.day) ||
        (a.time ?? '').localeCompare(b.time ?? '') ||
        a.title.toLowerCase().localeCompare(b.title.toLowerCase()),
    );
    return { start, end, occurrences: found };
  });

  guarded('calendar', 'GET', '/events/:id', ({ params }) => ({ ...eventOf(params.id) }));

  guarded('calendar', 'POST', '/events', ({ body }) => {
    const event = { id: state.nextEventId++, ...checkEvent(body) };
    state.events.push(event);
    return { status: 201, data: { ...event } };
  });

  guarded('calendar', 'PUT', '/events/:id', ({ params, body }) => {
    const event = eventOf(params.id);
    Object.assign(event, checkEvent(body));
    return { ...event };
  });

  guarded('calendar', 'DELETE', '/events/:id', ({ params }) => {
    const event = eventOf(params.id);
    state.events = state.events.filter((candidate) => candidate !== event);
    return { ok: true };
  });

  const entryOf = (id) => state.journal.find((entry) => entry.id === Number(id)) ?? notFound('entry not found');

  function checkEntry(body, current = null) {
    const text = typeof body?.body === 'string' ? body.body.trim() : '';
    if (text.length < 1 || text.length > 20000) invalid();
    const title = typeof body?.title === 'string' ? body.title.trim() || null : null;
    if (title && title.length > 120) invalid();
    const day = body?.day ?? current?.day ?? today();
    if (!isDay(day) || day < '1970-01-01' || day > '2100-12-31') invalid();
    if (day > today()) refuse(422, 'error', 'an entry cannot be dated in the future');
    return { day, title, body: text };
  }

  const likeAny = (entry, text) =>
    entry.body.toLowerCase().includes(text) || (entry.title ?? '').toLowerCase().includes(text);

  guarded('journal', 'GET', '/entries', ({ query }) => {
    const limit = Number(query.get('limit') ?? 30);
    const offset = Number(query.get('offset') ?? 0);
    if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0) invalid();
    const text = (query.get('q') ?? '').trim().toLowerCase();
    const matching = state.journal
      .filter((entry) => !text || likeAny(entry, text))
      .sort((a, b) => (a.day === b.day ? b.id - a.id : a.day < b.day ? 1 : -1));
    return { entries: matching.slice(offset, offset + limit).map((entry) => ({ ...entry })), total: matching.length };
  });

  guarded('journal', 'GET', '/entries/:id', ({ params }) => ({ ...entryOf(params.id) }));

  guarded('journal', 'POST', '/entries', ({ body }) => {
    const at = now().toISOString();
    const entry = { id: state.nextEntryId++, ...checkEntry(body), created_at: at, updated_at: at };
    state.journal.push(entry);
    return { status: 201, data: { ...entry } };
  });

  guarded('journal', 'PUT', '/entries/:id', ({ params, body }) => {
    const entry = entryOf(params.id);
    Object.assign(entry, checkEntry(body, entry), { updated_at: now().toISOString() });
    return { ...entry };
  });

  guarded('journal', 'DELETE', '/entries/:id', ({ params }) => {
    const entry = entryOf(params.id);
    state.journal = state.journal.filter((candidate) => candidate !== entry);
    return { ok: true };
  });

  guarded('mood', 'GET', '/entries/:day', ({ params }) => {
    if (!isDay(params.day)) invalid();
    const entry = state.mood.get(params.day);
    return { value: entry?.value ?? null, note: entry?.note ?? null };
  });

  guarded('mood', 'PUT', '/entries/:day', ({ params, body }) => {
    if (!isDay(params.day)) invalid();
    const value = body?.value ?? null;
    if (value !== null && ![1, 2, 3, 4, 5].includes(value)) invalid();
    if (typeof body?.note === 'string' && body.note.length > 300) invalid();
    if (!state.reports.has(params.day)) notFound('no report for that day');
    const note = typeof body?.note === 'string' ? body.note.trim() || null : null;
    if (value === null && note === null) state.mood.delete(params.day);
    else state.mood.set(params.day, { value, note });
    return { value, note };
  });

  guarded('mood', 'GET', '/summary', ({ query }) => {
    const days = Number(query.get('days') ?? 30);
    if (!Number.isInteger(days) || days < 7 || days > 366) invalid();
    const end = today();
    const start = addDays(end, -(days - 1));
    const rows = [...state.mood.entries()]
      .filter(([day]) => day >= start && day <= end)
      .sort(([a], [b]) => (a < b ? -1 : 1))
      .map(([day, entry]) => ({ day, ...entry }));
    const distribution = [1, 2, 3, 4, 5].map((level) => rows.filter((row) => row.value === level).length);
    return {
      from: start,
      to: end,
      days,
      entries: rows.filter((row) => row.value !== null).map(({ day, value }) => ({ day, value })),
      distribution,
      notes: rows
        .filter((row) => row.note)
        .map(({ day, note }) => ({ day, note }))
        .reverse()
        .slice(0, 5),
    };
  });

  if (empty) blank();
  else populate();

  function handle(method, path, query = new URLSearchParams(), body = undefined) {
    const route = routes.find((candidate) => candidate.method === method && candidate.matcher.test(path));
    if (!route) return { status: 404, data: { error: { code: 'not_found', message: 'not found' } } };
    try {
      const params = route.matcher.exec(path).groups ?? {};
      const result = route.handler({ params, query, body });
      if (result && typeof result === 'object' && 'status' in result && 'data' in result) return result;
      return { status: 200, data: result };
    } catch (error) {
      if (!(error instanceof Failure)) throw error;
      return { status: error.status, data: { error: { code: error.code, message: error.message } } };
    }
  }

  return { handle };
}
