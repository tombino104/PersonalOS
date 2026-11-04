import { beforeEach, describe, expect, it, vi } from 'vitest';

const request = vi.fn();
vi.mock('$core/lib/api.js', () => ({ pluginRequest: (...args) => request(...args) }));

const { tapNow } = await import('./data.js');

beforeEach(() => {
  request.mockReset();
  request.mockResolvedValue({});
});

describe('tapNow', () => {
  it('saves a late evening lights-off under tomorrow morning', async () => {
    const time = await tapNow('lights_off', new Date(2026, 10, 3, 23, 30));
    expect(time).toBe('23:30');
    expect(request).toHaveBeenCalledWith('sleep', 'PUT', '/nights/2026-11-04', { lights_off: '23:30' });
  });

  it('saves a lights-off after midnight under today', async () => {
    await tapNow('lights_off', new Date(2026, 10, 4, 0, 40));
    expect(request).toHaveBeenCalledWith('sleep', 'PUT', '/nights/2026-11-04', { lights_off: '00:40' });
  });

  it('saves a wake-up under today', async () => {
    const time = await tapNow('woke_up', new Date(2026, 10, 4, 7, 5));
    expect(time).toBe('07:05');
    expect(request).toHaveBeenCalledWith('sleep', 'PUT', '/nights/2026-11-04', { woke_up: '07:05' });
  });

  it('passes a failure on to the caller', async () => {
    request.mockRejectedValue(new Error('offline'));
    await expect(tapNow('woke_up', new Date(2026, 10, 4, 7, 5))).rejects.toThrow('offline');
  });
});
