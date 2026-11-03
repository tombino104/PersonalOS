<script>
  import { onMount } from 'svelte';
  import { pluginRequest } from '$core/lib/api.js';
  import Link from '$core/components/Link.svelte';
  import { formatDate } from '$core/lib/dates.js';
  import { locale, t } from '$core/lib/i18n.svelte.js';
  import { loadSleep } from './data.js';
  import NightDialog from './NightDialog.svelte';
  import {
    DEFAULT_TARGET,
    averageMinutes,
    batteryAt,
    bedtimeRange,
    hoursText,
    lastNight,
    localDay,
    localTime,
    nightMinutes,
    nightOfLightsOff,
    wallMinutes,
  } from './sleep.js';

  let nights = $state([]);
  let target = $state(DEFAULT_TARGET);
  let status = $state('loading');
  let dialogOpen = $state(false);
  let editing = $state(null);
  let reload = $state(0);
  let now = $state(wallMinutes(new Date()));
  let message = $state('');
  let failed = $state(false);
  let targetHours = $state(DEFAULT_TARGET / 60);

  $effect(() => {
    reload;
    loadSleep()
      .then((result) => {
        nights = result.nights;
        target = result.target;
        targetHours = result.target / 60;
        status = 'ready';
      })
      .catch(() => {
        status = 'error';
      });
  });

  onMount(() => {
    const timer = setInterval(() => (now = wallMinutes(new Date())), 60000);
    const visible = () => {
      if (document.visibilityState !== 'visible') return;
      now = wallMinutes(new Date());
      reload += 1;
    };
    document.addEventListener('visibilitychange', visible);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', visible);
    };
  });

  const battery = $derived(batteryAt(nights, now, target));
  const last = $derived(lastNight(nights));
  const average = $derived(averageMinutes(nights));
  const range = $derived(bedtimeRange(nights));

  function open(night) {
    editing = night;
    dialogOpen = true;
  }

  function saved() {
    dialogOpen = false;
    message = '';
    reload += 1;
  }

  async function tap(day, field, text) {
    const time = localTime();
    failed = false;
    try {
      await pluginRequest('sleep', 'PUT', `/nights/${day}`, { [field]: time });
      message = t(text, { time });
      reload += 1;
    } catch {
      failed = true;
      message = t('error.generic');
    }
  }

  async function saveTarget() {
    const hours = Number(targetHours);
    if (!Number.isFinite(hours) || hours < 4 || hours > 14) {
      targetHours = target / 60;
      return;
    }
    try {
      const result = await pluginRequest('sleep', 'PUT', '/settings', { target_minutes: Math.round(hours * 60) });
      target = result.target_minutes;
    } catch {
      targetHours = target / 60;
    }
  }

  function dayText(day) {
    return formatDate(day, locale(), { weekday: 'short', day: 'numeric', month: 'long' });
  }

  function rowText(night) {
    if (night.lights_off && night.woke_up) return `${night.lights_off} → ${night.woke_up}`;
    if (night.lights_off) return t('plugin.sleep.onlyLightsOff', { time: night.lights_off });
    return t('plugin.sleep.onlyWokeUp', { time: night.woke_up });
  }
</script>

<Link class="back" href="/more">
  <svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('nav.more')}
</Link>
<header class="head">
  <div>
    <div class="eyebrow">{t('plugin.sleep.eyebrow')}</div>
    <h1 class="title">{t('plugin.sleep.heading')} <em>{t('plugin.sleep.headingEmphasis')}</em></h1>
    <p class="lede">{t('plugin.sleep.lede')}</p>
  </div>
  <button class="btn solid" type="button" onclick={() => open(null)}>{t('plugin.sleep.logNight')}</button>
</header>

{#if status === 'error'}
  <p class="error" role="alert">{t('error.generic')}</p>
{:else if status === 'loading'}
  <p class="lede" aria-live="polite">{t('common.loading')}</p>
{:else}
  <div class="quick">
    <button class="btn" type="button" onclick={() => tap(nightOfLightsOff(), 'lights_off', 'plugin.sleep.savedLightsOff')}>
      {t('plugin.sleep.lightsOffNow')}
    </button>
    <button class="btn" type="button" onclick={() => tap(localDay(), 'woke_up', 'plugin.sleep.savedWokeUp')}>
      {t('plugin.sleep.wokeUpNow')}
    </button>
    {#if message}
      <span class="muted saved" class:error={failed} role="status">{message}</span>
    {/if}
  </div>

  <section class="card battery" aria-label={t('plugin.sleep.batteryTitle')}>
    <div class="eyebrow">{t('plugin.sleep.batteryTitle')} · {t('plugin.sleep.batteryEstimate')}</div>
    {#if battery}
      <div class="level">
        <span class="percent">{battery.percent}%</span>
        <span class="bar" role="img" aria-label="{battery.percent}%"><i style:width="{battery.percent}%"></i></span>
      </div>
      <p class="muted small">
        {#if battery.asleep}
          {t('plugin.sleep.batteryAsleep', { time: battery.since })}
        {:else}
          {t('plugin.sleep.batteryAwake', { hours: hoursText(battery.awake) })}{#if battery.estimated}
            · {t('plugin.sleep.batteryGuessed')}{/if}
        {/if}
      </p>
    {:else}
      <p class="lede none">{t('plugin.sleep.batteryEmpty')}</p>
    {/if}
    <p class="muted small note">{t('plugin.sleep.batteryNote')}</p>
  </section>

  <section class="stats">
    <div class="card stat">
      <div class="eyebrow">{t('plugin.sleep.lastNight')}</div>
      {#if last}
        <div class="value">{hoursText(nightMinutes(last))}</div>
        <div class="muted small">{t('plugin.sleep.target', { hours: hoursText(target) })}</div>
      {:else}
        <div class="muted small">—</div>
      {/if}
    </div>
    <div class="card stat">
      <div class="eyebrow">{t('plugin.sleep.average')}</div>
      {#if average !== null}
        <div class="value">{hoursText(average)}</div>
      {:else}
        <div class="muted small">{t('plugin.sleep.averageEmpty')}</div>
      {/if}
    </div>
    <div class="card stat">
      <div class="eyebrow">{t('plugin.sleep.bedtime')}</div>
      {#if range}
        <div class="value small-value">{t('plugin.sleep.bedtimeRange', { from: range.earliest, to: range.latest })}</div>
      {:else}
        <div class="muted small">{t('plugin.sleep.bedtimeEmpty')}</div>
      {/if}
    </div>
  </section>

  <h2 class="section-title">{t('plugin.sleep.nights')}</h2>
  {#if nights.length === 0}
    <section class="card empty">
      <p class="lede">{t('plugin.sleep.noNights')}</p>
    </section>
  {:else}
    <section class="card list" aria-label={t('plugin.sleep.nights')}>
      {#each nights as night (night.day)}
        <div class="row">
          <div class="who">
            <span class="name">{dayText(night.day)}</span>
            <span class="muted when">{rowText(night)}</span>
          </div>
          {#if night.minutes !== null}
            <span class="length">{hoursText(night.minutes)}</span>
          {/if}
          <button class="btn" type="button" onclick={() => open(night)}>{t('plugin.sleep.edit')}</button>
        </div>
      {/each}
    </section>
  {/if}

  <section class="card goal">
    <h2 class="section-title flat">{t('plugin.sleep.targetTitle')}</h2>
    <label class="label" for="sleep-target">{t('plugin.sleep.targetHours')}</label>
    <input
      id="sleep-target"
      class="field"
      type="number"
      min="4"
      max="14"
      step="0.5"
      inputmode="decimal"
      bind:value={targetHours}
      onchange={saveTarget}
    />
    <p class="muted small">{t('plugin.sleep.targetHint')}</p>
  </section>
{/if}

<p class="muted foot">{t('plugin.sleep.foot')}</p>

{#if dialogOpen}
  {#key editing?.day ?? 'new'}
    <NightDialog night={editing} {nights} onsaved={saved} onclose={() => (dialogOpen = false)} />
  {/key}
{/if}

<style>
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 24px;
  }

  .quick {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
  }

  .saved {
    font: 400 13px/1.4 var(--sans);
  }

  .battery {
    padding: 24px;
    margin-bottom: 16px;
  }

  .level {
    display: flex;
    align-items: center;
    gap: 20px;
    margin: 12px 0 8px;
  }

  .percent {
    font: 400 44px/1 var(--serif);
  }

  .bar {
    flex: 1 1 auto;
    height: 14px;
    border: 1.5px solid var(--ink-2);
    border-radius: 4px;
    overflow: hidden;
  }

  .bar i {
    display: block;
    height: 100%;
    background: var(--ink-2);
  }

  .small {
    margin: 0;
    font: 400 13px/1.5 var(--sans);
  }

  .note {
    margin-top: 12px;
  }

  .none {
    margin: 12px 0 0;
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 8px;
  }

  .stat {
    padding: 20px;
  }

  .value {
    margin: 8px 0 4px;
    font: 400 30px/1.1 var(--serif);
  }

  .small-value {
    font-size: 20px;
    line-height: 1.3;
  }

  .section-title {
    margin: 28px 2px 12px;
    font: 400 22px/1.2 var(--serif);
  }

  .section-title.flat {
    margin: 0 0 12px;
  }

  .list {
    padding: 8px 24px;
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 16px;
    padding: 14px 0;
    border-top: 1px solid var(--line);
  }

  .row:first-child {
    border-top: 0;
  }

  .who {
    display: flex;
    flex: 1 1 200px;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .name {
    font: 500 17px/1.3 var(--serif);
  }

  .when {
    font: 400 13px/1.3 var(--sans);
  }

  .length {
    font: 400 14px/1.3 var(--sans);
    color: var(--ink-2);
  }

  .empty {
    padding: 28px;
  }

  .empty .lede {
    margin: 0;
  }

  .goal {
    margin-top: 28px;
    padding: 24px;
  }

  .goal .field {
    max-width: 140px;
    margin-bottom: 12px;
  }

  .foot {
    margin: 16px 2px 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
