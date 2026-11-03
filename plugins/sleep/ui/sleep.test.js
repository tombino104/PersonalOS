import { describe, expect, it } from 'vitest';
import {
  averageMinutes,
  batteryAt,
  bedtimeRange,
  defaultNightDay,
  hoursText,
  lastNight,
  nightDays,
  nightMinutes,
  nightOfLightsOff,
  openSleep,
  spanOf,
  toMinutes,
  toTime,
} from './sleep.js';

const night = (day, lights_off, woke_up) => ({ day, lights_off, woke_up });
const at = (day, time) => spanOf({ day, lights_off: null, woke_up: time }, 0).wake;

describe('times', () => {
  it('reads and writes HH:MM', () => {
    expect(toMinutes('07:30')).toBe(450);
    expect(toMinutes('24:00')).toBeNull();
    expect(toMinutes(null)).toBeNull();
    expect(toTime(450)).toBe('07:30');
    expect(toTime(-30)).toBe('23:30');
    expect(toTime(1470)).toBe('00:30');
  });

  it('writes hours and minutes', () => {
    expect(hoursText(420)).toBe('7h');
    expect(hoursText(445)).toBe('7h 25m');
    expect(hoursText(45)).toBe('0h 45m');
  });
});

describe('nightMinutes', () => {
  it('counts across midnight and after it', () => {
    expect(nightMinutes(night('2026-10-20', '23:15', '06:45'))).toBe(450);
    expect(nightMinutes(night('2026-10-20', '00:30', '07:30'))).toBe(420);
  });

  it('needs both moments', () => {
    expect(nightMinutes(night('2026-10-20', '23:00', null))).toBeNull();
    expect(nightMinutes(night('2026-10-20', null, '07:00'))).toBeNull();
  });
});

describe('nightOfLightsOff', () => {
  it('puts an evening on the next morning and a night after midnight on today', () => {
    expect(nightOfLightsOff(new Date(2026, 9, 20, 23, 30))).toBe('2026-10-21');
    expect(nightOfLightsOff(new Date(2026, 9, 21, 0, 40))).toBe('2026-10-21');
    expect(nightOfLightsOff(new Date(2026, 9, 31, 22, 0))).toBe('2026-11-01');
  });
});

describe('batteryAt', () => {
  const full = night('2026-10-20', '23:00', '07:00');

  it('is high at the moment you get up and falls through the day', () => {
    const wake = at('2026-10-20', '07:00');
    const morning = batteryAt([full], wake);
    const evening = batteryAt([full], wake + 16 * 60);
    expect(morning.percent).toBe(89);
    expect(evening.percent).toBe(37);
    expect(morning.awake).toBe(0);
    expect(evening.awake).toBe(960);
  });

  it('is lower after a short night than after a long one', () => {
    const wake = at('2026-10-20', '07:00');
    const short = batteryAt([night('2026-10-20', '03:00', '07:00')], wake);
    expect(short.percent).toBeLessThan(batteryAt([full], wake).percent);
    expect(short.percent).toBeGreaterThan(60);
  });

  it('forgets the starting guess after a couple of nights', () => {
    const nights = [night('2026-10-19', '23:00', '07:00'), full];
    const wake = at('2026-10-20', '07:00');
    expect(Math.abs(batteryAt(nights, wake).percent - batteryAt([full], wake).percent)).toBeLessThanOrEqual(3);
  });

  it('assumes the target length when only the wake time is known', () => {
    const wake = at('2026-10-20', '07:00');
    const result = batteryAt([night('2026-10-20', null, '07:00')], wake, 480);
    expect(result.estimated).toBe(true);
    expect(result.percent).toBe(89);
  });

  it('says nothing without a recent night', () => {
    const wake = at('2026-10-20', '07:00');
    expect(batteryAt([], wake)).toBeNull();
    expect(batteryAt([night('2026-10-20', '23:00', null)], wake + 20 * 60)).toBeNull();
    expect(batteryAt([full], wake + 24 * 60 + 1)).toBeNull();
    expect(batteryAt([full], wake + 24 * 60)).not.toBeNull();
    expect(batteryAt([full], wake - 60)).toBeNull();
  });

  it('never leaves the 0 to 100 range', () => {
    const wake = at('2026-10-20', '07:00');
    const result = batteryAt([full], wake + 24 * 60);
    expect(result.percent).toBeGreaterThanOrEqual(0);
    expect(result.percent).toBeLessThanOrEqual(100);
  });
});

describe('batteryAt while you sleep', () => {
  const before = night('2026-11-02', '23:00', '07:00');

  it('goes up while the lights are off and the wake-up is not logged yet', () => {
    const evening = batteryAt([before], at('2026-11-02', '23:00')).percent;
    const sleeping = batteryAt([before, night('2026-11-03', '23:00', null)], at('2026-11-03', '03:00'));
    expect(sleeping.asleep).toBe(true);
    expect(sleeping.since).toBe('23:00');
    expect(sleeping.percent).toBeGreaterThan(evening);
  });

  it('works after midnight too', () => {
    const result = batteryAt([before, night('2026-11-03', '00:30', null)], at('2026-11-03', '03:30'));
    expect(result.asleep).toBe(true);
  });

  it('forgets a lights-off that is more than sixteen hours old', () => {
    const lights = night('2026-11-03', '23:00', null);
    const start = at('2026-11-03', '23:00') - 1440;
    expect(batteryAt([before, lights], start + 16 * 60).asleep).toBe(true);
    expect(batteryAt([before, lights], start + 16 * 60 + 1)?.asleep).toBeFalsy();
  });

  it('works with nothing but a lights-off', () => {
    expect(batteryAt([night('2026-11-03', '23:00', null)], at('2026-11-03', '03:00')).asleep).toBe(true);
  });

  it('drops back to awake once the wake-up is logged', () => {
    const result = batteryAt([before, night('2026-11-03', '23:00', '07:00')], at('2026-11-03', '09:00'));
    expect(result.asleep).toBe(false);
    expect(result.awake).toBe(120);
  });
});

describe('openSleep', () => {
  it('ignores a lights-off from before the last wake-up', () => {
    expect(openSleep([night('2026-11-03', '23:00', null)], at('2026-11-03', '03:00'), at('2026-11-03', '03:00'))).toBeNull();
  });
});

describe('nightDays', () => {
  it('puts the lights-off on the day before when the night crosses midnight', () => {
    expect(nightDays('2026-11-03', '23:30', '07:00')).toEqual({ lightsOffDay: '2026-11-02', wokeUpDay: '2026-11-03' });
    expect(nightDays('2026-11-03', '00:30', '07:00')).toEqual({ lightsOffDay: '2026-11-03', wokeUpDay: '2026-11-03' });
  });
});

describe('defaultNightDay', () => {
  it('proposes tomorrow in the evening and today otherwise', () => {
    expect(defaultNightDay(new Date(2026, 10, 2, 22, 0))).toBe('2026-11-03');
    expect(defaultNightDay(new Date(2026, 10, 3, 14, 0))).toBe('2026-11-03');
  });
});

describe('averageMinutes', () => {
  it('averages the latest nights and skips incomplete ones', () => {
    const nights = [
      night('2026-10-18', '23:00', '07:00'),
      night('2026-10-19', '00:00', '06:00'),
      night('2026-10-20', '23:00', null),
    ];
    expect(averageMinutes(nights)).toBe(420);
  });

  it('needs at least two nights', () => {
    expect(averageMinutes([night('2026-10-18', '23:00', '07:00')])).toBeNull();
  });
});

describe('bedtimeRange', () => {
  it('spans evening and after-midnight times without jumping over midnight', () => {
    const nights = [
      night('2026-10-18', '23:10', '07:00'),
      night('2026-10-19', '23:50', '07:00'),
      night('2026-10-20', '00:20', '07:00'),
    ];
    expect(bedtimeRange(nights)).toEqual({ earliest: '23:10', latest: '00:20', spread: 70, count: 3 });
  });

  it('needs at least three nights', () => {
    expect(bedtimeRange([night('2026-10-18', '23:10', '07:00'), night('2026-10-19', '23:20', '07:00')])).toBeNull();
  });
});

describe('lastNight', () => {
  it('is the newest night with both moments', () => {
    const nights = [night('2026-10-19', '23:00', '07:00'), night('2026-10-20', '23:00', null)];
    expect(lastNight(nights).day).toBe('2026-10-19');
    expect(lastNight([])).toBeNull();
  });
});
