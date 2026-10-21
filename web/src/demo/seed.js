import { addDays, atTime, weekdayOf } from './dates.js';

export const AREAS = [
  { id: 1, slug: 'physical', name: 'Physical', position: 1, color_token: 'area-physical' },
  { id: 2, slug: 'discipline', name: 'Discipline', position: 2, color_token: 'area-discipline' },
  { id: 3, slug: 'social', name: 'Social', position: 3, color_token: 'area-social' },
  { id: 4, slug: 'intellect', name: 'Intellect', position: 4, color_token: 'area-intellect' },
  { id: 5, slug: 'career', name: 'Career', position: 5, color_token: 'area-career' },
  { id: 6, slug: 'mindset', name: 'Mindset', position: 6, color_token: 'area-mindset' },
];

const EVERY_DAY = [0, 1, 2, 3, 4, 5, 6];
const WEEKDAYS = [0, 1, 2, 3, 4];

export const SAMPLE_ACTIVITIES = {
  physical: [
    ['Workout', 3, [0, 2, 4, 5], 'At least 30 minutes, anything that makes you sweat'],
    ['Walk or run', 2, EVERY_DAY],
    ['Regular sleep', 2, EVERY_DAY, 'In bed before midnight, screens off'],
    ['Balanced meals', 1, EVERY_DAY],
  ],
  discipline: [
    ['Wake up on time', 2, EVERY_DAY],
    ['Morning routine', 2, EVERY_DAY, 'Water, stretching, plan the day'],
    ['Follow the daily plan', 2, WEEKDAYS],
  ],
  social: [
    ['Small kind gesture', 1, EVERY_DAY],
    ['Start a conversation', 2, EVERY_DAY],
    ['Take the initiative', 3, [1, 3, 5], 'Propose something instead of waiting to be asked'],
  ],
  intellect: [
    ['Reading', 2, EVERY_DAY, 'Twenty pages of a book, not the news'],
    ['Follow a course', 3, WEEKDAYS],
    ['Personal project', 2, [5, 6]],
  ],
  career: [
    ['Planned study or work hours', 3, WEEKDAYS],
    ['Finish one task today', 2, WEEKDAYS],
  ],
  mindset: [
    ['Meditation or journaling', 2, EVERY_DAY],
    ['Handle a stressful moment calmly', 3, EVERY_DAY],
  ],
};

const STRENGTH = { physical: 0.7, discipline: 0.8, social: 0.5, intellect: 0.68, career: 0.78, mindset: 0.6 };

const REFLECTIONS = [
  'Slow start, but I kept the routine. That counts.',
  'Skipped the workout. Tired, no excuses, just the fact.',
  'A good day: the plan held from morning to evening.',
  'Talked to someone I had been avoiding. It was easier than expected.',
  'Too much screen time. Tomorrow I start with the book.',
  'Calm under pressure at work today.',
  'Not my best, not my worst. Moving on.',
];

const MOOD_NOTES = [
  'Slept badly, still got things done.',
  'Good energy after the walk.',
  'A heavy day, but a steady one.',
  'Long call with an old friend.',
];

const EVENTS = [
  { title: 'Dentist appointment', offset: 3, time: '10:30', category: 'health', repeat: 'none' },
  { title: 'Call with family', offset: 1, time: '18:00', category: 'social', repeat: 'weekly' },
  { title: 'Course deadline', offset: 9, time: null, category: 'study', repeat: 'none' },
  { title: 'Dinner with friends', offset: 5, time: '20:00', category: 'social', repeat: 'none' },
  { title: 'Monthly budget review', offset: -12, time: '19:00', category: 'personal', repeat: 'monthly' },
  { title: 'Team planning', offset: 2, time: '09:30', category: 'work', repeat: 'weekly' },
];

function random(seed) {
  let value = seed >>> 0;
  return () => {
    value = (value + 0x6d2b79f5) >>> 0;
    let mixed = value;
    mixed = Math.imul(mixed ^ (mixed >>> 15), mixed | 1);
    mixed ^= mixed + Math.imul(mixed ^ (mixed >>> 7), mixed | 61);
    return ((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296;
  };
}

export function sampleActivities(state, at) {
  for (const area of AREAS) {
    for (const [name, weight, days, description] of SAMPLE_ACTIVITIES[area.slug]) {
      state.activities.push({
        id: state.nextActivityId++,
        area: area.slug,
        name,
        description: description ?? null,
        weight,
        cadence: 'daily',
        days,
        created_at: at.toISOString(),
        archived_at: null,
      });
    }
  }
}

export function completionsFor(state, day) {
  const order = new Map(AREAS.map((area) => [area.slug, area.position]));
  const weekday = weekdayOf(day);
  return state.activities
    .filter((activity) => !activity.archived_at && activity.days.includes(weekday))
    .sort((a, b) => order.get(a.area) - order.get(b.area) || a.id - b.id)
    .map((activity) => ({
      id: state.nextCompletionId++,
      activity_id: activity.id,
      name: activity.name,
      weight: activity.weight,
      area: activity.area,
      done: false,
    }));
}

export function seedHistory(state, today, span = 120) {
  const next = random(20260101);
  const since = addDays(today, -span);
  sampleActivities(state, atTime(addDays(since, -10), '09:00'));
  for (let back = span; back >= 1; back -= 1) {
    const day = addDays(today, -back);
    const weekend = weekdayOf(day) >= 5;
    if (next() < (weekend ? 0.16 : 0.07)) continue;
    const progress = 1 - back / span;
    const completions = completionsFor(state, day);
    for (const item of completions) {
      const chance = STRENGTH[item.area] + progress * 0.14 - (weekend ? 0.12 : 0) + (next() - 0.5) * 0.18;
      item.done = next() < chance;
    }
    state.reports.set(day, {
      day,
      completedAt: atTime(day, '21:30'),
      reflection: next() < 0.12 ? REFLECTIONS[Math.floor(next() * REFLECTIONS.length)] : null,
      completions,
    });
    if (next() < 0.78) {
      const done = completions.filter((item) => item.done).length / (completions.length || 1);
      const value = Math.min(5, Math.max(1, Math.round(1.6 + done * 2.6 + (next() - 0.5) * 1.6)));
      const note = next() < 0.1 ? MOOD_NOTES[Math.floor(next() * MOOD_NOTES.length)] : null;
      state.mood.set(day, { value, note });
    }
  }
}

export function seedEvents(state, today) {
  for (const event of EVENTS) {
    state.events.push({
      id: state.nextEventId++,
      title: event.title,
      day: addDays(today, event.offset),
      time: event.time,
      category: event.category,
      notes: null,
      repeat: event.repeat,
      until: null,
    });
  }
}
