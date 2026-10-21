<script>
  import { pluginRequest } from '$core/lib/api.js';
  import Link from '$core/components/Link.svelte';
  import { formatDate, lastDays } from '$core/lib/dates.js';
  import { locale, t } from '$core/lib/i18n.svelte.js';
  import { barWidths, buildChart, seriesFor } from './chart.js';

  let period = $state(30);
  let data = $state(null);
  let failed = $state(false);

  $effect(() => {
    const days = period;
    failed = false;
    pluginRequest('mood', 'GET', `/summary?days=${days}`)
      .then((result) => {
        if (period === days) data = result;
      })
      .catch(() => {
        failed = true;
      });
  });

  const chart = $derived(
    data ? buildChart(seriesFor(lastDays(data.to, data.days), data.entries)) : null,
  );
  const widths = $derived(data ? barWidths(data.distribution) : []);
  const max = $derived(data ? Math.max(...data.distribution) : 0);
  const shortDate = (day) => formatDate(day, locale(), { day: 'numeric', month: 'short' });
</script>

<Link class="back" href="/more">
  <svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('nav.more')}
</Link>
<header>
  <div class="eyebrow">{t('plugin.mood.eyebrow')}</div>
  <h1 class="title">{t('plugin.mood.heading')} <em>{t('plugin.mood.headingEmphasis')}</em></h1>
  <p class="lede">{t('plugin.mood.lede')}</p>
</header>

{#if failed}
  <p class="error" role="alert">{t('error.generic')}</p>
{:else if data && chart}
  <section class="card trend rise" aria-label={t('plugin.mood.trendLabel')}>
    <div class="trend-head">
      <h2>{t('plugin.mood.lastDays', { days: data.days })}</h2>
      <div class="segmented" role="group" aria-label={t('home.period')}>
        <button class="seg" class:on={period === 30} aria-pressed={period === 30} onclick={() => (period = 30)}>{t('plugin.mood.days30')}</button>
        <button class="seg" class:on={period === 14} aria-pressed={period === 14} onclick={() => (period = 14)}>{t('plugin.mood.days14')}</button>
      </div>
    </div>
    <svg viewBox="0 0 720 220" role="img" aria-label={t('plugin.mood.chartLabel')}>
      {#each chart.grid as row}
        <line x1="40" x2="712" y1={row.y} y2={row.y} class="grid" />
        <text x="26" y={row.y + 4} text-anchor="end" class="tick">{row.value}</text>
      {/each}
      <path d={chart.line} class="line" />
      {#each chart.points as point}
        <circle cx={point.x} cy={point.y} r="4" class="point" />
      {/each}
      {#each chart.gaps as gap}
        <line x1={gap.x} x2={gap.x} y1="196" y2="204" class="gap" />
      {/each}
    </svg>
    <p class="muted foot">{t('plugin.mood.gapsNote')}</p>
  </section>

  <div class="two">
    <section class="card pad rise" aria-label={t('plugin.mood.distribution')}>
      <h2 class="eyebrow">{t('plugin.mood.distribution')}</h2>
      {#each data.distribution as count, index}
        <div class="bar-row">
          <span class="bar-name">{t(`plugin.mood.level.${index + 1}`)}</span>
          <span class="bar"><span style:width="{widths[index]}%"></span></span>
          <span class="bar-count">{count}</span>
        </div>
      {/each}
      {#if max === 0}
        <p class="muted foot">{t('plugin.mood.noEntries')}</p>
      {/if}
    </section>

    <section class="card pad rise" aria-label={t('plugin.mood.notes')}>
      <h2 class="eyebrow">{t('plugin.mood.notes')}</h2>
      {#each data.notes as entry (entry.day)}
        <div class="note">
          <div class="eyebrow when">{shortDate(entry.day)}</div>
          <p>«{entry.note}»</p>
        </div>
      {:else}
        <p class="muted foot">{t('plugin.mood.noNotes')}</p>
      {/each}
    </section>
  </div>
{:else}
  <p class="lede" aria-live="polite">{t('common.loading')}</p>
{/if}

<style>
  .trend {
    padding: 24px 24px 20px;
  }

  .trend-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
  }

  h2:not(.eyebrow) {
    margin: 0;
    font: 400 24px/1.2 var(--serif);
  }

  .trend svg {
    display: block;
    width: 100%;
    height: auto;
  }

  .grid {
    stroke: var(--line);
    stroke-width: 1;
    stroke-dasharray: 2 4;
  }

  .tick {
    font: 400 11px 'DM Sans', sans-serif;
    fill: var(--ink-3);
  }

  .line {
    fill: none;
    stroke: var(--area-mindset);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .point {
    fill: var(--area-mindset);
    stroke: var(--surface);
    stroke-width: 1.5;
  }

  .gap {
    stroke: var(--ink-3);
    stroke-width: 1.5;
    stroke-linecap: round;
  }

  .foot {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .two {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  .pad {
    flex: 1 1 360px;
    padding: 24px;
  }

  .pad h2 {
    margin: 0 0 12px;
  }

  .bar-row {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 34px;
  }

  .bar-name {
    flex: none;
    width: 110px;
    font: 400 14px/1 var(--sans);
    color: var(--ink-2);
  }

  .bar {
    flex-grow: 1;
    height: 10px;
    border-radius: 5px;
    background: var(--paper-2);
  }

  .bar span {
    display: block;
    height: 100%;
    border-radius: 5px;
    background: var(--area-mindset);
    opacity: 0.75;
  }

  .bar-count {
    flex: none;
    width: 24px;
    text-align: right;
    font: 500 14px/1 var(--sans);
  }

  .note {
    padding: 12px 0;
    border-top: 1px solid var(--line);
  }

  .when {
    font-size: 11px;
    letter-spacing: 0.1em;
  }

  .note p {
    margin: 8px 0 0;
    font: italic 400 17px/1.4 var(--serif);
  }
</style>
