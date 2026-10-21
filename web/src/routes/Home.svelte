<script>
  import { onMount } from 'svelte';
  import Avatar from '../components/Avatar.svelte';
  import Icon from '../components/Icon.svelte';
  import Link from '../components/Link.svelte';
  import { api } from '../lib/api.js';
  import { AREAS, buildHeatGrid, trendGeometry } from '../lib/charts.js';
  import { addDays, formatDate, lastDays } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { widgets } from '../lib/plugins.svelte.js';

  let status = $state('loading');
  let today = $state('');
  let period = $state('week');
  let threeOnly = $state(false);
  let trioPage = $state(0);
  let scoreByDay = $state({});
  let averages = $state({});

  const length = $derived(period === 'month' ? 30 : 7);
  const days = $derived(today ? lastDays(today, length) : []);

  onMount(async () => {
    try {
      today = (await api.today()).day;
      const result = await api.scores(addDays(today, -181), today);
      const byDay = {};
      for (const entry of result.days) {
        byDay[entry.day] = {
          overall: entry.overall,
          areas: Object.fromEntries(entry.areas.map((area) => [area.area, area.score])),
        };
      }
      scoreByDay = byDay;
      status = 'ready';
    } catch {
      status = 'error';
    }
  });

  $effect(() => {
    if (!today) return;
    const from = addDays(today, -(length - 1));
    api
      .areaStats(from, today)
      .then((result) => {
        averages = Object.fromEntries(result.areas.map((area) => [area.area, area.average]));
      })
      .catch(() => {
        averages = {};
      });
  });

  const trends = $derived(
    AREAS.map((area) => {
      const values = days.map((day) => scoreByDay[day]?.areas[area] ?? null);
      return {
        area,
        geometry: trendGeometry(values),
        average: averages[area] ?? null,
        hasData: values.some((value) => value !== null),
      };
    }),
  );
  const visible = $derived(threeOnly ? trends.slice(trioPage * 3, trioPage * 3 + 3) : trends);
  const todayOverall = $derived(scoreByDay[today]?.overall ?? null);
  const heat = $derived(
    today
      ? buildHeatGrid(
          today,
          new Map(Object.entries(scoreByDay).map(([day, entry]) => [day, entry.overall])),
        )
      : null,
  );
  const heatCells = $derived(heat ? heat.columns.flatMap((column) => column.cells) : []);
  const monthLabels = $derived(
    heat
      ? heat.columns.map((column) =>
          Number(column.monday.slice(8)) <= 7
            ? formatDate(column.monday, locale(), { month: 'short' })
            : '',
        )
      : [],
  );
  const weekdayLabels = ['2024-01-01', '', '2024-01-03', '', '2024-01-05', '', ''];

  const pluginWidgets = $derived(widgets().filter((widget) => widget.placement === 'bottom'));
  const topWidgets = $derived(widgets().filter((widget) => widget.placement === 'top'));
  const round = (value) => Math.round(value);
  const weekday = $derived(today ? formatDate(today, locale(), { weekday: 'long' }) : '');
  const dateText = $derived(today ? formatDate(today, locale(), { day: 'numeric', month: 'long' }) : '');
  const rangeStart = $derived(days.length ? formatDate(days[0], locale(), { day: 'numeric', month: 'short' }) : '');
  const rangeEnd = $derived(days.length ? formatDate(days[days.length - 1], locale(), { day: 'numeric', month: 'short' }) : '');

  function cellTitle(cell) {
    const text = formatDate(cell.day, locale(), { day: 'numeric', month: 'short' });
    if (cell.kind === 'today') return `${text} · ${t('home.today')}`;
    if (cell.kind === 'empty') return `${text} · ${t('home.notFilled')}`;
    return cell.overall === null ? text : `${text} · ${round(cell.overall)} %`;
  }
</script>

<svg width="0" height="0" aria-hidden="true" class="defs">
  <defs>
    {#each AREAS as area}
      <pattern id="hatch-{area}" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="6" style="stroke: var(--area-{area}); stroke-width: 1.3; opacity: 0.55" />
      </pattern>
    {/each}
  </defs>
</svg>

<div class="content stagger">
  <header class="header-row">
    <div>
      <div class="greeting">
        <Link href="/settings/mascot" aria-label={t('settings.mascot')}><Avatar size={40} /></Link>
        <div class="eyebrow">{t('nav.home')}</div>
      </div>
      <h1 class="title">
        {weekday.charAt(0).toUpperCase() + weekday.slice(1)}, <em>{dateText}</em>
      </h1>
      <p class="lede">{t('home.lede')}</p>
    </div>
    <div class="controls">
      <div class="segmented" role="group" aria-label={t('home.period')}>
        <button class="seg" class:on={period === 'week'} aria-pressed={period === 'week'} onclick={() => (period = 'week')}>{t('home.week')}</button>
        <button class="seg" class:on={period === 'month'} aria-pressed={period === 'month'} onclick={() => (period = 'month')}>{t('home.month')}</button>
      </div>
      {#if todayOverall !== null}
        <div class="today-score">{t('home.today')} <b>{round(todayOverall)} %</b></div>
      {/if}
    </div>
  </header>

  {#each topWidgets as widget (widget.pluginId + widget.widgetId)}
    <section class="card widget rise">
      <widget.component />
    </section>
  {/each}

  {#if status === 'loading'}
    <p class="lede" aria-live="polite">{t('common.loading')}</p>
  {:else if status === 'error'}
    <p class="error" role="alert">{t('error.generic')}</p>
  {:else}
    <section class="trends" aria-label={t('home.trends')}>
      <div class="trend-controls">
        <div class="segmented" role="group" aria-label={t('home.howMany')}>
          <button class="seg" class:on={!threeOnly} aria-pressed={!threeOnly} onclick={() => (threeOnly = false)}>{t('home.allSix')}</button>
          <button class="seg" class:on={threeOnly} aria-pressed={threeOnly} onclick={() => (threeOnly = true)}>{t('home.onlyThree')}</button>
        </div>
        {#if threeOnly}
          <div class="pages">
            <button class="pager" aria-label={t('home.firstThree')} disabled={trioPage === 0} onclick={() => (trioPage = 0)}><Icon name="back" small /></button>
            <span>{trioPage === 0 ? `${t('area.physical')} · ${t('area.discipline')} · ${t('area.social')}` : `${t('area.intellect')} · ${t('area.career')} · ${t('area.mindset')}`}</span>
            <button class="pager" aria-label={t('home.lastThree')} disabled={trioPage === 1} onclick={() => (trioPage = 1)}><Icon name="forward" small /></button>
          </div>
        {/if}
      </div>

      <div class="trend-grid">
        {#each visible as trend (trend.area)}
          <div class="card trend rise" data-area={trend.area}>
            <div class="trend-head">
              <div class="trend-name">
                <span class="dot small"></span>
                <span>{t(`area.${trend.area}`)}</span>
              </div>
              <span class="muted avg">
                {trend.average === null ? t('home.noData') : t('home.average', { value: round(trend.average) })}
              </span>
            </div>
            <svg
              viewBox="0 0 300 112"
              role="img"
              aria-label={t('home.trendLabel', {
                area: t(`area.${trend.area}`),
                days: length,
                value: trend.average === null ? '–' : round(trend.average),
              })}
            >
              <line x1="8" y1="57" x2="296" y2="57" stroke="var(--line)" stroke-width="1" stroke-dasharray="2 6" />
              <path d={trend.geometry.area} fill="url(#hatch-{trend.area})" />
              <path class="line" d={trend.geometry.line} />
              <path d="M8 6 V100 H296" fill="none" stroke="var(--ink-3)" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" />
              {#each trend.geometry.points as point}
                <circle cx={point.x} cy={point.y} r={period === 'month' ? 2.5 : 4} fill="var(--area)" stroke="var(--surface)" stroke-width="1.5" />
              {/each}
            </svg>
            <div class="range muted"><span>{rangeStart}</span><span>{rangeEnd}</span></div>
          </div>
        {/each}
      </div>
    </section>

    <section class="card heat rise" aria-label={t('home.consistencyLabel')}>
      <div class="heat-main">
        <div class="heat-head">
          <span class="section-title">{t('home.consistency')}</span>
          <span class="muted small-text">{t('home.sixMonths')}</span>
        </div>
        <div class="heat-scroll">
          <div class="heat-grid">
            <span></span>
            <div class="months">
              {#each monthLabels as label}<span>{label}</span>{/each}
            </div>
            <div class="weekdays">
              {#each weekdayLabels as iso}
                <span>{iso ? formatDate(iso, locale(), { weekday: 'short' }) : ''}</span>
              {/each}
            </div>
            <div class="cells">
              {#each heatCells as cell (cell.day)}
                <span class="cell {cell.kind === 'filled' ? cell.level : cell.kind}" title={cellTitle(cell)}></span>
              {/each}
            </div>
          </div>
        </div>
      </div>
      <div class="heat-side">
        <p>{t('home.filledDays', { filled: heat?.filled ?? 0, total: heat?.elapsed ?? 0 })}</p>
        <div class="legend"><span>{t('home.less')}</span><span class="cell"></span><span class="cell h2"></span><span class="cell h3"></span><span class="cell h4"></span><span>{t('home.more')}</span></div>
        <div class="legend"><span class="cell empty"></span><span>{t('home.notFilled')}</span></div>
      </div>
    </section>

    {#each pluginWidgets as widget (widget.pluginId + widget.widgetId)}
      <section class="card widget rise">
        <widget.component />
      </section>
    {/each}
  {/if}
</div>

<style>
  .widget {
    padding: 22px 24px;
  }

  .defs {
    position: absolute;
  }

  .greeting {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 4px;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 20px;
  }

  .today-score {
    font: 400 13px/1 var(--sans);
    color: var(--ink-3);
  }

  .today-score b {
    font-weight: 500;
    color: var(--ink-2);
  }

  .trends {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .trend-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .pages {
    display: flex;
    align-items: center;
    gap: 10px;
    font: 400 14px/1 var(--sans);
    color: var(--ink-2);
  }

  .trend-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
    gap: 16px;
  }

  .trend {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 18px 20px 14px;
  }

  .trend-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .trend-name {
    display: flex;
    align-items: center;
    gap: 10px;
    font: 500 21px/1 var(--serif);
  }

  .dot.small {
    width: 9px;
    height: 9px;
  }

  .avg {
    font: 400 12.5px/1 var(--sans);
  }

  .trend svg {
    display: block;
    width: 100%;
    height: auto;
  }

  .line {
    fill: none;
    stroke: var(--area);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  @media (prefers-reduced-motion: no-preference) {
    .line {
      transform-box: view-box;
      transform-origin: 8px 0;
      animation: reveal 1.1s cubic-bezier(0.4, 0, 0.2, 1) 0.4s backwards;
    }
  }

  .range {
    display: flex;
    justify-content: space-between;
    font: 400 11.5px/1 var(--sans);
  }

  .heat {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 24px 40px;
    padding: 22px 24px;
  }

  .heat-main {
    flex: 1 1 520px;
    min-width: 0;
    max-width: 700px;
  }

  .heat-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  .small-text {
    font: 400 12.5px/1 var(--sans);
  }

  .heat-scroll {
    overflow-x: auto;
  }

  .heat-grid {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr);
    column-gap: 8px;
    row-gap: 6px;
    min-width: 500px;
  }

  .months,
  .cells {
    display: grid;
    grid-template-columns: repeat(26, minmax(0, 1fr));
    gap: 4px;
  }

  .months span,
  .weekdays span {
    font: 400 11px/1 var(--sans);
    color: var(--ink-3);
    white-space: nowrap;
  }

  .weekdays {
    display: grid;
    grid-template-rows: repeat(7, minmax(0, 1fr));
    gap: 4px;
  }

  .weekdays span {
    display: flex;
    align-items: center;
  }

  .cells {
    grid-template-rows: repeat(7, auto);
    grid-auto-flow: column;
  }

  .heat-side {
    display: flex;
    flex: 1 1 200px;
    flex-direction: column;
    gap: 14px;
    padding-top: 40px;
  }

  .heat-side p {
    margin: 0;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .legend {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 400 12px/1 var(--sans);
    color: var(--ink-3);
  }

  .legend .cell {
    width: 14px;
    height: 14px;
    animation: none;
  }
</style>
