<script>
  import { pluginRequest } from '$core/lib/api.js';
  import Icon from '$core/components/Icon.svelte';
  import { addDays, formatDate } from '$core/lib/dates.js';
  import { locale, t } from '$core/lib/i18n.svelte.js';
  import EventDialog from './EventDialog.svelte';
  import {
    categoryColor,
    dotCategories,
    gridDays,
    groupByDay,
    monthStart,
    shiftMonth,
    todayIso,
  } from './calendar.js';

  const today = todayIso();

  let cursor = $state(monthStart(today));
  let selected = $state(today);
  let occurrences = $state([]);
  let failed = $state(false);
  let editing = $state(null);
  let reload = $state(0);

  const days = $derived(gridDays(cursor));
  const groups = $derived(groupByDay(occurrences));
  const agenda = $derived(groups[selected] ?? []);
  const weekdays = $derived(
    Array.from({ length: 7 }, (_, index) =>
      formatDate(addDays('2024-01-01', index), locale(), { weekday: 'short' }),
    ),
  );

  $effect(() => {
    const first = days[0];
    const last = days[days.length - 1];
    reload;
    pluginRequest('calendar', 'GET', `/events?start=${first}&end=${last}`)
      .then((result) => {
        if (days[0] === first) {
          occurrences = result.occurrences;
          failed = false;
        }
      })
      .catch(() => {
        failed = true;
      });
  });

  function go(delta) {
    cursor = shiftMonth(cursor, delta);
    selected = cursor === monthStart(today) ? today : cursor;
  }

  function goToday() {
    cursor = monthStart(today);
    selected = today;
  }

  function pick(day) {
    selected = day;
    if (monthStart(day) !== cursor) cursor = monthStart(day);
  }

  async function fetchEvent(item) {
    try {
      editing = { event: await pluginRequest('calendar', 'GET', `/events/${item.event_id}`) };
    } catch {
      failed = true;
    }
  }

  function saved() {
    editing = null;
    reload += 1;
  }

  const longDate = (day) =>
    formatDate(day, locale(), { weekday: 'long', day: 'numeric', month: 'long' });
</script>

<header class="header-row">
  <div>
    <div class="eyebrow">{t('plugin.calendar.eyebrow')}</div>
    <h1 class="title">
      {formatDate(cursor, locale(), { month: 'long' })}
      <em>{formatDate(cursor, locale(), { year: 'numeric' })}</em>
    </h1>
  </div>
  <div class="nav">
    <button class="btn" type="button" onclick={goToday}>{t('plugin.calendar.today')}</button>
    <button class="btn round" type="button" aria-label={t('plugin.calendar.previous')} onclick={() => go(-1)}>
      <Icon name="back" small />
    </button>
    <button class="btn round" type="button" aria-label={t('plugin.calendar.next')} onclick={() => go(1)}>
      <Icon name="forward" small />
    </button>
  </div>
</header>

{#if failed}
  <p class="error" role="alert">{t('error.generic')}</p>
{/if}

<div class="layout">
  <section class="card month rise" aria-label={t('plugin.calendar.monthLabel')}>
    <div class="grid head" aria-hidden="true">
      {#each weekdays as name}
        <span>{name}</span>
      {/each}
    </div>
    <div class="grid">
      {#each days as day (day)}
        {@const items = groups[day] ?? []}
        <button
          type="button"
          class="cell"
          class:outside={monthStart(day) !== cursor}
          class:today={day === today}
          class:selected={day === selected}
          aria-pressed={day === selected}
          aria-label={`${longDate(day)}${items.length ? `, ${t('plugin.calendar.count', { count: items.length })}` : ''}`}
          onclick={() => pick(day)}
        >
          <span class="number">{Number(day.slice(8))}</span>
          <span class="dots">
            {#each dotCategories(items) as category}
              <span class="mark" style:background={categoryColor(category)}></span>
            {/each}
          </span>
        </button>
      {/each}
    </div>
  </section>

  <section class="card agenda rise" aria-label={t('plugin.calendar.agendaLabel')}>
    <div class="eyebrow">{selected === today ? t('plugin.calendar.todayLabel') : t('plugin.calendar.dayLabel')}</div>
    <h2>{longDate(selected)}</h2>
    {#each agenda as item (`${item.event_id}-${item.day}`)}
      <button type="button" class="entry" onclick={() => fetchEvent(item)}>
        <span class="when">{item.time ?? t('plugin.calendar.allDayShort')}</span>
        <span class="what">
          <span class="name">{item.title}</span>
          <span class="meta">
            <span class="mark" style:background={categoryColor(item.category)}></span>
            {t(`plugin.calendar.category.${item.category}`)}
            {#if item.repeat !== 'none'}· {t(`plugin.calendar.repeat.${item.repeat}`)}{/if}
          </span>
        </span>
      </button>
    {:else}
      <p class="muted empty">{t('plugin.calendar.empty')}</p>
    {/each}
    <button class="btn add" type="button" onclick={() => (editing = { event: null })}>
      {t('plugin.calendar.add')}
    </button>
    <p class="muted foot">{t('plugin.calendar.foot')}</p>
  </section>
</div>

{#if editing}
  <EventDialog event={editing.event} day={selected} onsaved={saved} onclose={() => (editing = null)} />
{/if}

<style>
  .nav {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .round {
    width: 44px;
    padding: 0;
  }

  .layout {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 16px;
  }

  .month {
    flex: 2 1 480px;
    padding: 16px;
  }

  .agenda {
    flex: 1 1 300px;
    padding: 24px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 4px;
  }

  .head {
    margin-bottom: 4px;
  }

  .head span {
    padding: 8px 0;
    text-align: center;
    font: 500 11px/1 var(--sans);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-3);
  }

  .cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    min-height: 56px;
    padding: 6px 0;
    border: 1px solid transparent;
    border-radius: 12px;
    background: transparent;
    cursor: pointer;
  }

  .cell:hover {
    background: var(--paper-2);
  }

  .cell.outside .number {
    color: var(--ink-3);
    opacity: 0.6;
  }

  .cell.today .number {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    margin: -4px 0;
    border: 1px solid var(--ink);
    border-radius: 50%;
  }

  .cell.selected {
    background: var(--ink);
    border-color: var(--ink);
  }

  .cell.selected .number {
    color: var(--paper);
    border-color: var(--paper);
  }

  .number {
    font: 500 15px/1 var(--sans);
  }

  .dots {
    display: flex;
    gap: 3px;
    height: 6px;
  }

  .mark {
    display: inline-block;
    flex: none;
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .agenda h2 {
    margin: 12px 0 16px;
    font: 400 26px/1.2 var(--serif);
    text-transform: capitalize;
  }

  .entry {
    display: flex;
    align-items: baseline;
    gap: 16px;
    width: 100%;
    min-height: 56px;
    padding: 12px 0;
    border: 0;
    border-top: 1px solid var(--line);
    background: transparent;
    text-align: left;
    cursor: pointer;
  }

  .when {
    flex: none;
    width: 56px;
    font: 500 13px/1.4 var(--sans);
    color: var(--ink-2);
  }

  .what {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .name {
    font: 400 16px/1.3 var(--sans);
  }

  .meta {
    display: flex;
    align-items: center;
    gap: 6px;
    font: 400 12px/1.3 var(--sans);
    color: var(--ink-3);
  }

  .empty {
    margin: 0 0 16px;
    font: italic 400 17px/1.4 var(--serif);
  }

  .add {
    margin-top: 16px;
  }

  .foot {
    margin: 20px 0 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
