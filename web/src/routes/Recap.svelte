<script>
  import { onMount } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import { api } from '../lib/api.js';
  import { heatLevel } from '../lib/charts.js';
  import { addDays, formatDate } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { router } from '../lib/router.svelte.js';
  import { change, signed } from '../lib/review.js';
  import {
    currentPeriod,
    dayCountChange,
    monthName,
    monthOffset,
    periodKind,
    periodLabel,
    readingOf,
    shiftPeriod,
    switchKind,
  } from '../lib/recap.js';

  let today = $state('');
  let period = $state('');
  let data = $state(null);
  let status = $state('loading');

  const kind = $derived(period ? periodKind(period) : 'month');
  const isLatest = $derived(Boolean(period) && period === currentPeriod(kind, today));

  onMount(async () => {
    try {
      today = (await api.today()).day;
      const asked = router.query.get('period');
      period = asked && /^\d{4}(-\d{2})?$/.test(asked) ? asked : currentPeriod('month', today);
    } catch {
      status = 'error';
    }
  });

  $effect(() => {
    if (!period) return;
    const requested = period;
    status = 'loading';
    api
      .recap(requested)
      .then((result) => {
        if (requested !== period) return;
        data = result;
        status = 'ready';
      })
      .catch(() => {
        status = 'error';
      });
  });

  const round = (value) => Math.round(value);
  const reading = $derived(data ? readingOf(data.areas) : null);
  const difference = $derived(data ? dayCountChange(data) : null);
  const weekdayLabels = $derived(
    Array.from({ length: 7 }, (_, index) => formatDate(addDays('2024-01-01', index), locale(), { weekday: 'narrow' })),
  );
  const cells = $derived(
    data && data.kind === 'month'
      ? [
          ...Array.from({ length: monthOffset(data.period) }, () => ({ kind: 'blank' })),
          ...data.days.map((day) => ({
            ...day,
            kind: day.day > today ? 'future' : day.completed ? 'filled' : 'empty',
            level: heatLevel(day.completed ? day.overall : null),
          })),
        ]
      : [],
  );
  const dayLong = (day) => formatDate(day, locale(), { weekday: 'long', day: 'numeric', month: 'long' });
</script>

<div class="content stagger">
  <header class="header-row">
    <div>
      <div class="eyebrow">{t('nav.recap')}</div>
      <h1 class="title">
        {t('recap.titleLead')} <em>{period ? periodLabel(period, locale()) : ''}</em>
      </h1>
      {#if data}
        <p class="lede">
          {#if data.filled_days === 0}
            {t('recap.ledeEmpty')}
          {:else}
            {t(`recap.lede${data.is_current ? 'SoFar' : ''}${data.filled_days === 1 ? 'One' : ''}`, { filled: data.filled_days, total: data.elapsed_days })}
          {/if}
        </p>
      {/if}
    </div>
    <div class="controls">
      <div class="segmented" role="group" aria-label={t('recap.periods')}>
        <button class="seg" class:on={kind === 'month'} aria-pressed={kind === 'month'} disabled={!today} onclick={() => (period = switchKind(period, 'month', today))}>{t('recap.month')}</button>
        <button class="seg" class:on={kind === 'year'} aria-pressed={kind === 'year'} disabled={!today} onclick={() => (period = switchKind(period, 'year', today))}>{t('recap.year')}</button>
      </div>
      <div class="nav" role="group" aria-label={t('recap.choose')}>
        <button class="btn" type="button" aria-label={t('recap.previous')} disabled={!period} onclick={() => (period = shiftPeriod(period, -1))}>
          <Icon name="back" small />
        </button>
        <button class="btn" type="button" aria-label={t('recap.next')} disabled={isLatest || !period} onclick={() => (period = shiftPeriod(period, 1))}>
          <Icon name="forward" small />
        </button>
      </div>
    </div>
  </header>

  {#if status === 'error'}
    <p class="error" role="alert">{t('error.generic')}</p>
  {:else if status === 'loading' || !data}
    <p class="lede" aria-live="polite">{t('common.loading')}</p>
  {:else}
    <div class="grid">
    <section class="card block rise" class:wide={data.kind === 'year'} aria-label={data.kind === 'month' ? t('recap.daysTitle') : t('recap.monthsTitle')}>
      <h2 class="eyebrow">{data.kind === 'month' ? t('recap.daysTitle') : t('recap.monthsTitle')}</h2>
      <div class="facts">
        <div class="figure"><span class="num">{data.filled_days}</span><span class="of">{t('recap.ofDays', { total: data.elapsed_days })}</span></div>
        {#if difference !== null}
          <p class="vs">
            {difference === 0
              ? t(`recap.vsSame.${kind}`)
              : t(difference > 0 ? `recap.vsMore.${kind}` : `recap.vsLess.${kind}`, { count: Math.abs(difference) })}
          </p>
        {/if}
      </div>
      {#if data.kind === 'month'}
        <div class="calendar">
          {#each weekdayLabels as label}<span class="wd">{label}</span>{/each}
          {#each cells as cell}
            {#if cell.kind === 'blank'}
              <span></span>
            {:else}
              <span class="cell {cell.kind === 'filled' ? cell.level : cell.kind}" class:future={cell.kind === 'future'} title={dayLong(cell.day)}>
                <span class="n">{Number(cell.day.slice(8))}</span>
              </span>
            {/if}
          {/each}
        </div>
      {:else}
        <div class="months">
          {#each data.months as month (month.month)}
            <div class="month">
              <span class="bar" aria-hidden="true"><span style:height="{month.possible ? round((month.filled / month.possible) * 100) : 0}%"></span></span>
              <span class="mcount">{month.filled}</span>
              <span class="mname">{monthName(month.month, locale())}</span>
            </div>
          {/each}
        </div>
      {/if}
      <p class="muted foot">{t('recap.empty')}</p>
    </section>

    {#if data.filled_days > 0}
      <section class="card block rise" aria-label={t('recap.areasTitle')}>
        <h2 class="eyebrow">{t('recap.areasTitle')}</h2>
        {#each data.areas as item (item.area)}
          {@const diff = change(item.average, item.previous)}
          <div class="area" data-area={item.area}>
            <span class="dot"></span>
            <span class="name">{t(`area.${item.area}`)}</span>
            <span class="abar" aria-hidden="true"><span style:width="{item.average === null ? 0 : round(item.average)}%"></span></span>
            <span class="value">{item.average === null ? '–' : `${round(item.average)} %`}</span>
            <span class="diff muted">{diff === null ? '' : t(`recap.change.${kind}`, { value: signed(diff) })}</span>
          </div>
        {/each}
        {#if reading}
          <p class="reading">{t('recap.reading', { high: t(`area.${reading.high}`), low: t(`area.${reading.low}`) })}</p>
        {/if}
        <p class="muted foot">{t('recap.areasNote')}</p>
      </section>

      {#if data.top_habits.length > 0}
        <section class="card block rise" aria-label={t('recap.habitsTitle')}>
          <h2 class="eyebrow">{t('recap.habitsTitle')}</h2>
          {#each data.top_habits as item (item.activity_id)}
            <div class="habit" data-area={item.area}>
              <span class="dot"></span>
              <span class="name">{item.name}</span>
              <span class="muted">{t(item.done === 1 ? 'recap.habitDaysOne' : 'recap.habitDays', { done: item.done, total: item.total })}</span>
            </div>
          {/each}
        </section>
      {/if}

      {#if data.best_week}
        <section class="card block rise" aria-label={t('recap.bestWeekTitle')}>
          <h2 class="eyebrow">{t('recap.bestWeekTitle')}</h2>
          <p class="big">
            {t('recap.bestWeek', {
              date: formatDate(data.best_week.week_start, locale(), { day: 'numeric', month: 'long' }),
              filled: data.best_week.filled,
              possible: data.best_week.possible,
            })}
          </p>
        </section>
      {/if}

      {#if data.line_count > 0}
        <section class="card block rise wide" aria-label={t('recap.linesTitle')}>
          <h2 class="eyebrow">{t('recap.linesTitle')}</h2>
          <p class="muted count">{t(data.line_count === 1 ? 'recap.lineCountOne' : 'recap.lineCount', { count: data.line_count })}</p>
          {#each data.lines as line (line.day)}
            <div class="line">
              <div class="eyebrow when">{dayLong(line.day)}</div>
              <p>«{line.text}»</p>
            </div>
          {/each}
        </section>
      {/if}
    {/if}
    </div>
    {#if data.filled_days > 0}
      <p class="closing">{t('recap.closing')}</p>
    {/if}
  {/if}
</div>

<style>
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }

  .nav {
    display: flex;
    gap: 8px;
  }

  .nav .btn {
    width: 44px;
    padding: 0;
  }

  .foot {
    margin: 12px 2px 0;
    font: 400 13px/1.5 var(--sans);
  }

  .block {
    margin-top: 16px;
    padding: 24px;
  }

  .block h2 {
    display: block;
    margin: 0 0 14px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
    gap: 16px;
    margin-top: 16px;
  }

  .grid .block {
    margin-top: 0;
  }

  .wide {
    grid-column: 1 / -1;
  }

  .facts {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 6px 20px;
    margin-bottom: 18px;
  }

  .figure {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }

  .num {
    font: 400 64px/1 var(--serif);
  }

  .of {
    font: 400 17px/1.3 var(--sans);
    color: var(--ink-2);
  }

  .vs {
    margin: 0;
    font: italic 400 18px/1.4 var(--serif);
  }

  .calendar {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 6px;
  }

  .wd {
    text-align: center;
    font: 500 11px/1 var(--sans);
    color: var(--ink-3);
    text-transform: uppercase;
  }

  .calendar .cell {
    display: grid;
    place-items: center;
  }

  .n {
    font: 500 12px/1 var(--sans);
    color: var(--ink);
  }

  .cell.empty .n,
  .cell.today .n {
    color: var(--ink-3);
  }

  .months {
    display: flex;
    justify-content: center;
    align-items: flex-end;
    gap: 6px;
  }

  .month {
    display: flex;
    flex: 0 1 84px;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }

  .bar {
    display: flex;
    align-items: flex-end;
    width: 100%;
    height: 96px;
    border-radius: 6px;
    background: var(--paper-2);
    overflow: hidden;
  }

  .bar span {
    display: block;
    width: 100%;
    background: var(--ink-2);
    opacity: 0.75;
  }

  .mcount {
    font: 500 13px/1 var(--sans);
  }

  .mname {
    font: 400 11px/1 var(--sans);
    color: var(--ink-3);
  }

  .area {
    display: grid;
    grid-template-columns: 12px 110px 1fr 56px 130px;
    align-items: center;
    gap: 12px;
    min-height: 40px;
  }

  .name {
    font: 400 15px/1.3 var(--sans);
  }

  .abar {
    height: 8px;
    border-radius: 4px;
    background: var(--paper-2);
  }

  .abar span {
    display: block;
    height: 100%;
    border-radius: 4px;
    background: var(--area);
    opacity: 0.8;
  }

  .value {
    text-align: right;
    font: 500 14px/1 var(--sans);
  }

  .diff {
    font: 400 13px/1 var(--sans);
  }

  .reading {
    margin: 16px 0 0;
    font: italic 400 19px/1.4 var(--serif);
  }

  .habit {
    display: grid;
    grid-template-columns: 12px 1fr auto;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-top: 1px solid var(--line);
  }

  .habit:first-of-type {
    border-top: 0;
  }

  .big {
    margin: 0;
    font: 400 19px/1.4 var(--serif);
  }

  .count {
    margin: 0 0 8px;
    font: 400 14px/1.4 var(--sans);
  }

  .line {
    padding: 10px 0;
    border-top: 1px solid var(--line);
  }

  .when {
    font-size: 11px;
    letter-spacing: 0.1em;
  }

  .line p {
    margin: 6px 0 0;
    font: italic 400 17px/1.4 var(--serif);
  }

  .closing {
    margin: 24px 2px 8px;
    font: italic 400 19px/1.5 var(--serif);
    color: var(--ink-2);
  }

  @media (max-width: 560px) {
    .area {
      grid-template-columns: 12px 1fr 56px;
    }

    .abar,
    .diff {
      display: none;
    }

    .months {
      gap: 3px;
    }
  }
</style>
