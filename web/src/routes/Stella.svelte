<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';
  import { AREAS, easeInOut, radarAxes, radarFrame, radarLabel, radarPoint, radarRings } from '../lib/charts.js';
  import { addDays } from '../lib/dates.js';
  import { has, t } from '../lib/i18n.svelte.js';
  import { playProgress } from '../lib/motion.js';

  let today = $state('');
  let firstDay = $state(null);
  let period = $state(7);
  let selected = $state('physical');
  let current = $state({});
  let previous = $state({});
  let stats = $state([]);
  let status = $state('loading');

  const toMap = (result) => Object.fromEntries(result.areas.map((area) => [area.area, area.average]));

  onMount(async () => {
    try {
      const info = await api.today();
      today = info.day;
      firstDay = info.first_day;
    } catch {
      status = 'error';
    }
  });

  $effect(() => {
    if (!today) return;
    const days = period;
    const everything = days === 0;
    const start = everything ? (firstDay ?? today) : addDays(today, -(days - 1));
    const previousEnd = addDays(start, -1);
    const previousStart = addDays(previousEnd, -(days - 1));
    Promise.all([
      api.areaStats(start, today),
      everything ? Promise.resolve({ areas: [] }) : api.areaStats(previousStart, previousEnd),
      api.activityStats(start, today),
    ])
      .then(([now, before, activities]) => {
        current = toMap(now);
        previous = toMap(before);
        stats = activities.activities;
        status = 'ready';
      })
      .catch(() => {
        status = 'error';
      });
  });

  const round = (value) => Math.round(value);
  const withData = $derived(AREAS.filter((area) => current[area] !== null && current[area] !== undefined));
  const highest = $derived(
    withData.length > 1 ? withData.reduce((a, b) => (current[b] > current[a] ? b : a)) : null,
  );
  const lowest = $derived(
    withData.length > 1 ? withData.reduce((a, b) => (current[b] < current[a] ? b : a)) : null,
  );
  const reading = $derived(
    highest && lowest && highest !== lowest
      ? t('stella.reading', { high: t(`area.${highest}`), low: t(`area.${lowest}`) })
      : t('stella.readingEmpty'),
  );
  let progress = $state(0);
  const currentFrame = $derived(radarFrame(AREAS.map((area) => current[area]), progress));
  const previousFrame = $derived(radarFrame(AREAS.map((area) => previous[area]), progress));

  $effect(() => {
    if (status !== 'ready') return;
    current;
    previous;
    return playProgress((value) => (progress = easeInOut(value)), { delay: 250 });
  });
  const rings = radarRings();
  const axes = radarAxes();
  const selectedStats = $derived(stats.filter((entry) => entry.area === selected && !entry.archived));
</script>

<div class="content stagger">
  <header class="header-row">
    <div>
      <div class="eyebrow">{t('nav.stella')}</div>
      <h1 class="title">{t('stella.title')}</h1>
      <p class="lede">{t('stella.lede')}</p>
      <p class="reading">{reading}</p>
    </div>
    <div class="segmented" role="group" aria-label={t('home.period')}>
      <button class="seg" class:on={period === 7} aria-pressed={period === 7} onclick={() => (period = 7)}>{t('stella.days7')}</button>
      <button class="seg" class:on={period === 30} aria-pressed={period === 30} onclick={() => (period = 30)}>{t('stella.days30')}</button>
      <button class="seg" class:on={period === 0} aria-pressed={period === 0} onclick={() => (period = 0)}>{t('stella.daysAll')}</button>
    </div>
  </header>

  {#if status === 'error'}
    <p class="error" role="alert">{t('error.generic')}</p>
  {:else}
    <div class="layout">
      <section class="card radar rise" aria-label={t('stella.radarLabel')}>
        <svg viewBox="-40 0 540 460" role="img" aria-label={t('stella.radarLabel')}>
          {#each rings as points}
            <polygon {points} fill="none" stroke="var(--line)" stroke-width="1" />
          {/each}
          {#each axes as axis}
            <line x1="230" y1="230" x2={axis.x2} y2={axis.y2} stroke="var(--line)" stroke-width="1" />
          {/each}
          {#if period !== 0}
            <polyline points={previousFrame.outline} fill="none" stroke="var(--ink-3)" stroke-width="1.25" stroke-dasharray="4 4" stroke-linejoin="round" />
          {/if}
          <polygon points={currentFrame.outline} fill="var(--ink)" fill-opacity="0.09" />
          <polyline points={currentFrame.outline} fill="none" stroke="var(--ink)" stroke-width="1.5" stroke-linejoin="round" />
          {#each AREAS as area, index}
            {@const point = radarPoint(index, current[area] ?? 0)}
            {@const label = radarLabel(index)}
            {#if currentFrame.scales[index] > 0}
              <circle cx={point[0].toFixed(1)} cy={point[1].toFixed(1)} r={(selected === area ? 7 : 4.5) * currentFrame.scales[index]} fill="var(--area-{area})" stroke="var(--surface)" stroke-width="2" />
            {/if}
            <text x={label.x} y={label.y} text-anchor={label.anchor} dominant-baseline="middle" class="axis-label">{t(`area.${area}`)}</text>
          {/each}
        </svg>
        <div class="legend muted">
          <span><i class="solid"></i>{period === 0 ? t('stella.currentAll') : t('stella.current', { days: period })}</span>
          {#if period !== 0}
            <span><i class="dashed"></i>{t('stella.previous', { days: period })}</span>
          {/if}
        </div>
      </section>

      <section class="side">
        <div class="card list rise" role="group" aria-label={t('stella.pick')}>
          {#each AREAS as area}
            <button class="row" class:sel={selected === area} aria-pressed={selected === area} data-area={area} onclick={() => (selected = area)}>
              <span class="dot"></span>
              <span class="area-name">{t(`area.${area}`)}</span>
              <span class="value muted">{current[area] === null || current[area] === undefined ? '–' : `${round(current[area])} %`}</span>
            </button>
          {/each}
        </div>

        <div class="card detail rise" data-area={selected}>
          <div class="detail-head">
            <span class="dot"></span>
            <h2>{t(`area.${selected}`)}</h2>
            <span class="muted count">{t('stella.activities', { count: selectedStats.length })}</span>
          </div>
          <ul>
            {#each selectedStats as entry (entry.activity_id)}
              <li>
                <span class="name">{entry.name}</span>
                <span class="muted days">{t('stella.daysOf', { done: entry.done, total: entry.total })}</span>
                <span class="weight" role="img" aria-label={t('stella.weight', { weight: entry.weight })}>
                  {#each [1, 2, 3] as step}
                    <i class:filled={step <= entry.weight}></i>
                  {/each}
                </span>
              </li>
            {:else}
              <li class="muted">{t('stella.noActivityData')}</li>
            {/each}
          </ul>
          {#if has(`area.${selected}.note`)}
            <p class="muted note">{t(`area.${selected}.note`)}</p>
          {/if}
        </div>
      </section>
    </div>
  {/if}
</div>

<style>
  .reading {
    max-width: 560px;
    margin: 16px 0 0;
    font: italic 400 20px/1.4 var(--serif);
  }

  .layout {
    display: flex;
    flex-wrap: wrap;
    align-items: stretch;
    gap: 16px;
  }

  .radar {
    display: flex;
    flex: 1 1 460px;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    min-width: 0;
    padding: 24px;
  }

  .radar svg {
    display: block;
    width: 100%;
    max-width: 540px;
    height: auto;
  }

  .axis-label {
    font: 500 15px 'Newsreader', Georgia, serif;
    fill: var(--ink);
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px 24px;
    font: 400 12.5px/1 var(--sans);
  }

  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  .legend i {
    width: 18px;
    height: 0;
    border-top: 1.5px solid var(--ink);
  }

  .legend i.dashed {
    border-top: 1.5px dashed var(--ink-3);
  }

  .side {
    display: flex;
    flex: 1 1 380px;
    flex-direction: column;
    gap: 16px;
    min-width: 0;
  }

  .list {
    padding: 12px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-height: 48px;
    padding: 0 16px;
    border: 1px solid transparent;
    border-radius: 12px;
    background: transparent;
    cursor: pointer;
    text-align: left;
  }

  .row:hover,
  .row.sel {
    background: var(--paper-2);
  }

  .row.sel {
    border-color: var(--line);
  }

  .area-name {
    font: 500 17px/1 var(--serif);
  }

  .value {
    margin-left: auto;
    font: 400 13px/1 var(--sans);
  }

  .detail {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 20px 24px;
  }

  .detail-head {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .detail-head h2 {
    margin: 0;
    font: 500 22px/1 var(--serif);
  }

  .count {
    margin-left: auto;
    font: 400 12.5px/1 var(--sans);
  }

  ul {
    display: flex;
    flex-direction: column;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  li {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 0;
    border-top: 1px solid var(--line);
  }

  .name {
    flex: 1 1 auto;
    min-width: 0;
    font: 400 15px/1.35 var(--sans);
  }

  .days {
    font: 400 12.5px/1 var(--sans);
    white-space: nowrap;
  }

  .weight {
    display: inline-flex;
    gap: 4px;
  }

  .weight i {
    width: 8px;
    height: 8px;
    border: 1.25px solid var(--ink-3);
    border-radius: 50%;
  }

  .weight i.filled {
    background: var(--ink-2);
  }

  .note {
    margin: 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
