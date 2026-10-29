<script>
  import { onMount } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import Link from '../components/Link.svelte';
  import { api } from '../lib/api.js';
  import { AREAS } from '../lib/charts.js';
  import { addDays, formatDate } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { reportSections } from '../lib/plugins.svelte.js';
  import { router } from '../lib/router.svelte.js';
  import { mondayOf, weekRange } from '../lib/review.js';

  let status = $state('loading');
  let today = $state('');
  let firstDay = $state(null);
  let weekStart = $state('');
  let scoreByDay = $state({});
  let selected = $state('');
  let detail = $state(null);
  let detailStatus = $state('idle');
  let wanted = '';

  const currentWeek = $derived(today ? mondayOf(today) : '');
  const isCurrent = $derived(Boolean(weekStart) && weekStart === currentWeek);
  const canGoBack = $derived(Boolean(weekStart) && Boolean(firstDay) && weekStart > mondayOf(firstDay));
  const days = $derived(
    weekStart ? Array.from({ length: 7 }, (_, offset) => addDays(weekStart, offset)).filter((day) => day <= today) : [],
  );
  const yesterday = $derived(today ? addDays(today, -1) : '');
  const round = (value) => Math.round(value);

  onMount(async () => {
    try {
      const info = await api.today();
      today = info.day;
      firstDay = info.first_day;
      const asked = router.query.get('day');
      if (asked && /^\d{4}-\d{2}-\d{2}$/.test(asked) && asked <= today) wanted = asked;
      weekStart = mondayOf(wanted || today);
    } catch {
      status = 'error';
    }
  });

  $effect(() => {
    if (!weekStart) return;
    const requested = weekStart;
    api
      .scores(requested, addDays(requested, 6))
      .then((result) => {
        if (requested !== weekStart) return;
        const byDay = {};
        for (const entry of result.days) {
          byDay[entry.day] = {
            overall: entry.overall,
            areas: Object.fromEntries(entry.areas.map((area) => [area.area, area.score])),
          };
        }
        scoreByDay = byDay;
        const shown = Array.from({ length: 7 }, (_, offset) => addDays(requested, offset)).filter((day) => day <= today);
        const keep = wanted && shown.includes(wanted) ? wanted : '';
        wanted = '';
        selected = keep || [...shown].reverse().find((day) => byDay[day]) || shown[shown.length - 1];
        status = 'ready';
      })
      .catch(() => {
        status = 'error';
      });
  });

  $effect(() => {
    const day = selected;
    if (!day || status !== 'ready') return;
    if (!scoreByDay[day]) {
      detail = null;
      detailStatus = 'empty';
      return;
    }
    detailStatus = 'loading';
    api
      .getReport(day)
      .then((report) => {
        if (selected !== day) return;
        detail = report;
        detailStatus = 'ready';
      })
      .catch(() => {
        detailStatus = 'error';
      });
  });

  const groups = $derived(
    detail
      ? AREAS.map((area) => ({
          area,
          items: detail.completions.filter((completion) => completion.area === area),
        })).filter((group) => group.items.length > 0)
      : [],
  );
  const sections = $derived(reportSections());
  const editable = $derived(selected !== '' && (selected === today || selected === yesterday));
  const filled = $derived(Boolean(scoreByDay[selected]));
  const longTitle = $derived(
    selected ? formatDate(selected, locale(), { weekday: 'long', day: 'numeric', month: 'long' }) : '',
  );

  function rowLabel(day) {
    const entry = scoreByDay[day];
    if (entry) return entry.overall === null ? '–' : `${round(entry.overall)} %`;
    return day === today ? t('archive.today') : t('archive.empty');
  }
</script>

<div class="content stagger">
  <Link class="back" href="/more"><svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('nav.more')}</Link>
  <header>
    <div class="eyebrow">{t('nav.archive')}</div>
    <h1 class="title">{t('archive.title')}</h1>
    <p class="lede">{t('archive.lede')}</p>
  </header>

  {#if status === 'loading'}
    <p class="lede" aria-live="polite">{t('common.loading')}</p>
  {:else if status === 'error'}
    <p class="error" role="alert">{t('error.generic')}</p>
  {:else}
    <div class="weekbar">
      <span class="range">{weekRange(weekStart, locale())}</span>
      <div class="nav" role="group" aria-label={t('archive.weeks')}>
        <button class="btn" type="button" aria-label={t('archive.previous')} disabled={!canGoBack} onclick={() => (weekStart = addDays(weekStart, -7))}>
          <Icon name="back" small />
        </button>
        <button class="btn" type="button" disabled={isCurrent} onclick={() => (weekStart = currentWeek)}>{t('archive.thisWeek')}</button>
        <button class="btn" type="button" aria-label={t('archive.next')} disabled={isCurrent} onclick={() => (weekStart = addDays(weekStart, 7))}>
          <Icon name="forward" small />
        </button>
      </div>
    </div>

    <div class="layout">
      <section class="card days rise" aria-label={t('archive.days')}>
        {#each days as day (day)}
          {@const entry = scoreByDay[day]}
          <button class="row" class:sel={selected === day} class:blank={!entry} aria-pressed={selected === day} onclick={() => (selected = day)}>
            <span class="date">
              <span class="num">{Number(day.slice(8))}</span>
              <span class="dow">{formatDate(day, locale(), { weekday: 'short' })}</span>
            </span>
            <span class="points">
              {#each AREAS as area}
                <span class="pt" class:filled={entry && entry.areas[area] > 0} data-area={area}></span>
              {/each}
            </span>
            <span class="label-text">{rowLabel(day)}</span>
          </button>
        {/each}
      </section>

      <section class="card detail rise" aria-label={t('archive.detail')}>
        <div class="detail-head">
          <div>
            <div class="eyebrow">{selected ? formatDate(selected, locale(), { weekday: 'long' }) : ''}</div>
            <h2>{longTitle}</h2>
          </div>
          {#if editable}
            <Link class="btn solid" href={`/questionnaire?day=${selected}`}>{filled ? t('archive.edit') : t('archive.fill')}</Link>
          {/if}
        </div>
        {#if editable}
          <p class="muted note">{t(selected === today ? 'archive.editToday' : 'archive.editYesterday')}</p>
        {/if}

        {#if detailStatus === 'empty'}
          <div class="blank-box">
            <p>{t('archive.notFilled')}</p>
            <span>{t('archive.notFilledNote')}</span>
          </div>
        {:else if detailStatus === 'error'}
          <p class="error" role="alert">{t('error.generic')}</p>
        {:else if detail && detailStatus === 'ready'}
          <div class="groups">
            {#each groups as group (group.area)}
              <div data-area={group.area}>
                <div class="group-head"><span class="dot small"></span><span>{t(`area.${group.area}`)}</span></div>
                {#each group.items as item (item.activity_id)}
                  <div class="activity">
                    <span class="mark" class:done={item.done}>{item.done ? '✓' : '○'}</span>
                    <span class:muted={!item.done}>{item.name}</span>
                  </div>
                {/each}
              </div>
            {/each}
          </div>
          {#if detail.reflection}
            <div class="reflection">
              <div class="eyebrow">{t('questionnaire.reflection')}</div>
              <p>«{detail.reflection}»</p>
            </div>
          {/if}
          {#key selected}
            {#each sections as section (section.pluginId + section.sectionId)}
              <div class="plugin-section"><section.component day={selected} /></div>
            {/each}
          {/key}
        {/if}
      </section>
    </div>
  {/if}
</div>

<style>
  .weekbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

  .range {
    font: italic 400 20px/1.3 var(--serif);
  }

  .nav {
    display: flex;
    gap: 8px;
  }

  .nav .btn:not(:nth-child(2)) {
    width: 44px;
    padding: 0;
  }

  .layout {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 20px;
  }

  .days {
    flex: 1 1 320px;
    max-width: 420px;
    padding: 12px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-height: 56px;
    padding: 8px 16px;
    border: 1px solid transparent;
    border-radius: 12px;
    background: transparent;
    text-align: left;
    cursor: pointer;
  }

  .row:hover,
  .row.sel {
    background: var(--paper-2);
  }

  .row.sel {
    border-color: var(--line);
  }

  .row.blank {
    background-image: repeating-linear-gradient(135deg, transparent 0 4px, var(--line) 4px 5px);
  }

  .date {
    flex: none;
    width: 48px;
  }

  .num {
    display: block;
    font: 400 24px/1 var(--serif);
  }

  .dow {
    display: block;
    margin-top: 3px;
    font: 500 11px/1 var(--sans);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-3);
  }

  .points {
    display: flex;
    flex-grow: 1;
    gap: 4px;
  }

  .pt {
    width: 8px;
    height: 8px;
    border: 1.5px solid var(--line);
    border-radius: 50%;
  }

  .pt.filled {
    background: var(--area);
    border-color: var(--area);
  }

  .label-text {
    font: 400 13px/1 var(--sans);
    color: var(--ink-2);
  }

  .detail {
    flex: 2 1 480px;
    min-width: 0;
    padding: 24px 28px;
  }

  .detail-head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .detail-head h2 {
    margin: 8px 0 0;
    font: 400 32px/1.1 var(--serif);
  }

  .note {
    margin: 12px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .blank-box {
    margin-top: 20px;
    padding: 40px 20px;
    border: 1px dashed var(--line);
    border-radius: 12px;
    text-align: center;
    color: var(--ink-2);
  }

  .blank-box p {
    margin: 0;
    font: italic 400 18px/1.4 var(--serif);
  }

  .blank-box span {
    font: 400 13px/1.5 var(--sans);
    color: var(--ink-3);
  }

  .groups {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px 28px;
    margin-top: 20px;
  }

  .group-head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    font: 500 12px/1 var(--sans);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-2);
  }

  .dot.small {
    width: 9px;
    height: 9px;
  }

  .activity {
    display: flex;
    align-items: baseline;
    gap: 12px;
    padding: 4px 0;
    font: 400 15px/1.35 var(--sans);
  }

  .mark {
    flex: none;
    width: 14px;
    font-weight: 600;
    color: var(--ink-3);
  }

  .mark.done {
    color: var(--area);
  }

  .plugin-section {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--line);
  }

  .reflection {
    margin-top: 24px;
    padding-top: 20px;
    border-top: 1px solid var(--line);
  }

  .reflection p {
    margin: 8px 0 0;
    font: italic 400 18px/1.45 var(--serif);
    white-space: pre-wrap;
  }
</style>
