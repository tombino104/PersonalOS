<script>
  import { onMount } from 'svelte';
  import Link from '$core/components/Link.svelte';
  import { t } from '$core/lib/i18n.svelte.js';
  import { loadSleep, tapNow } from './data.js';
  import { DEFAULT_TARGET, batteryAt, hoursText, lastNight, localDay, nightMinutes, wallMinutes } from './sleep.js';

  let nights = $state([]);
  let target = $state(DEFAULT_TARGET);
  let now = $state(wallMinutes(new Date()));
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  function refresh() {
    now = wallMinutes(new Date());
    loadSleep()
      .then((result) => {
        nights = result.nights;
        target = result.target;
      })
      .catch(() => {});
  }

  onMount(() => {
    refresh();
    const timer = setInterval(() => (now = wallMinutes(new Date())), 60000);
    const visible = () => {
      if (document.visibilityState === 'visible') refresh();
    };
    document.addEventListener('visibilitychange', visible);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', visible);
    };
  });

  async function tap(field, text) {
    busy = true;
    failed = false;
    try {
      const time = await tapNow(field);
      message = t(text, { time });
      refresh();
    } catch {
      failed = true;
      message = t('error.generic');
    }
    busy = false;
  }

  const battery = $derived(batteryAt(nights, now, target));
  const last = $derived(lastNight(nights));
</script>

<div class="head">
  <div class="eyebrow">{t('plugin.sleep.batteryTitle')} · {t('plugin.sleep.batteryEstimate')}</div>
  <Link class="open" href="/p/sleep/nights">{t('plugin.sleep.widgetOpen')}</Link>
</div>
{#if battery}
  <div class="level">
    <span class="percent">{battery.percent}%</span>
    <span class="bar" role="img" aria-label="{battery.percent}%"><i style:width="{battery.percent}%"></i></span>
  </div>
  {#if battery.asleep}
    <p class="muted line">{t('plugin.sleep.batteryAsleep', { time: battery.since })}</p>
  {:else if last}
    <p class="muted line">{last.day === localDay() ? t('plugin.sleep.lastNight') : t('plugin.sleep.lastLogged')} {hoursText(nightMinutes(last))} · {t('plugin.sleep.target', { hours: hoursText(target) })}</p>
  {/if}
{:else}
  <p class="muted line none">{t('plugin.sleep.widgetEmpty')}</p>
{/if}
<div class="quick">
  <button class="btn" type="button" disabled={busy} onclick={() => tap('lights_off', 'plugin.sleep.savedLightsOff')}>
    {t('plugin.sleep.lightsOffNow')}
  </button>
  <button class="btn" type="button" disabled={busy} onclick={() => tap('woke_up', 'plugin.sleep.savedWokeUp')}>
    {t('plugin.sleep.wokeUpNow')}
  </button>
  {#if message}
    <span class="muted note" class:error={failed} role="status">{message}</span>
  {/if}
</div>

<style>
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px 16px;
  }

  .head :global(.open) {
    font: 500 13px/1 var(--sans);
    color: var(--ink-2);
    text-decoration: underline;
  }

  .level {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-top: 10px;
  }

  .percent {
    font: 400 26px/1 var(--serif);
  }

  .bar {
    flex: 1 1 auto;
    height: 10px;
    border: 1.5px solid var(--ink-2);
    border-radius: 4px;
    overflow: hidden;
  }

  .bar i {
    display: block;
    height: 100%;
    background: var(--ink-2);
  }

  .line {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .none {
    margin-top: 10px;
  }

  .quick {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 10px;
    margin-top: 14px;
  }

  .quick .btn {
    min-height: 36px;
    padding: 0 16px;
    font-size: 13px;
  }

  .note {
    font: 400 13px/1.4 var(--sans);
  }
</style>
