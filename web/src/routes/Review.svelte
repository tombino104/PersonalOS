<script>
  import { onMount } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import { api } from '../lib/api.js';
  import { AREAS } from '../lib/charts.js';
  import { isOpen, setOpen } from '../lib/collapse.js';
  import { addDays, formatDate } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { change, groupActivities, mondayOf, signed, weekRange } from '../lib/review.js';

  let currentWeek = $state('');
  let week = $state('');
  let data = $state(null);
  let note = $state('');
  let status = $state('loading');
  let saved = $state(false);
  let failure = $state('');
  let timer = null;

  onMount(async () => {
    try {
      currentWeek = mondayOf((await api.today()).day);
      week = currentWeek;
    } catch {
      status = 'error';
    }
    return () => clearTimeout(timer);
  });

  $effect(() => {
    if (!week) return;
    const requested = week;
    status = 'loading';
    api
      .review(requested)
      .then((result) => {
        if (requested !== week) return;
        data = result;
        note = result.note ?? '';
        saved = false;
        status = 'ready';
      })
      .catch(() => {
        status = 'error';
      });
  });

  const round = (value) => Math.round(value);
  const groups = $derived(data ? groupActivities(data.activities.filter((item) => !item.archived), AREAS) : []);
  const lines = $derived(data ? data.days.filter((day) => day.reflection) : []);
  const isCurrent = $derived(week === currentWeek);

  async function save() {
    clearTimeout(timer);
    timer = null;
    failure = '';
    try {
      await api.saveReviewNote(week, note.trim() === '' ? null : note);
      saved = true;
    } catch {
      failure = t('error.generic');
    }
  }

  function onInput() {
    saved = false;
    clearTimeout(timer);
    timer = setTimeout(save, 800);
  }

  const weekday = (day) => formatDate(day, locale(), { weekday: 'narrow' });
  const dayNumber = (day) => formatDate(day, locale(), { day: 'numeric' });
  const dayLong = (day) => formatDate(day, locale(), { weekday: 'long', day: 'numeric', month: 'long' });
</script>

<div class="content stagger">
  <header class="header-row">
    <div>
      <div class="eyebrow">{t('nav.review')}</div>
      <h1 class="title">
        {t('review.titleLead')} <em>{week ? weekRange(week, locale()) : ''}</em>
      </h1>
      {#if data}
        <p class="lede">{t('review.lede', { count: data.filled_days })}</p>
      {/if}
    </div>
    <div class="nav" role="group" aria-label={t('review.weeks')}>
      <button class="btn" type="button" aria-label={t('review.previous')} disabled={!week} onclick={() => (week = addDays(week, -7))}>
        <Icon name="back" small />
      </button>
      <button class="btn" type="button" aria-label={t('review.next')} disabled={isCurrent || !week} onclick={() => (week = addDays(week, 7))}>
        <Icon name="forward" small />
      </button>
    </div>
  </header>

  {#if status === 'error'}
    <p class="error" role="alert">{t('error.generic')}</p>
  {:else if status === 'loading' || !data}
    <p class="lede" aria-live="polite">{t('common.loading')}</p>
  {:else}
    <section class="card days rise" aria-label={t('review.days')}>
      {#each data.days as day (day.day)}
        <div class="day" class:filled={day.completed} title={dayLong(day.day)}>
          <span class="wd">{weekday(day.day)}</span>
          <span class="num">{dayNumber(day.day)}</span>
          <span class="val">{day.completed && day.overall !== null ? `${round(day.overall)}` : '–'}</span>
        </div>
      {/each}
    </section>
    <p class="muted foot">{t('review.empty')}</p>

    <section class="card block rise" aria-label={t('review.areas')}>
      <h2 class="eyebrow">{t('review.areas')}</h2>
      {#each data.areas as item (item.area)}
        {@const diff = change(item.average, item.previous)}
        <div class="area" data-area={item.area}>
          <span class="dot"></span>
          <span class="name">{t(`area.${item.area}`)}</span>
          <span class="bar" aria-hidden="true"><span style:width="{item.average === null ? 0 : round(item.average)}%"></span></span>
          <span class="value">{item.average === null ? '–' : `${round(item.average)} %`}</span>
          <span class="diff muted">{diff === null ? '' : t('review.change', { value: signed(diff) })}</span>
        </div>
      {/each}
      <p class="muted foot">{t('review.areasNote')}</p>
    </section>

    {#if groups.length > 0}
      <section class="card block rise" aria-label={t('review.habits')}>
        <details open={isOpen('review.habits')} ontoggle={(event) => setOpen('review.habits', event.currentTarget.open)}>
          <summary><h2 class="eyebrow">{t('review.habits')}</h2><span class="chev"><Icon name="down" small /></span></summary>
          <div class="fold">
        {#each groups as group (group.area)}
          <div class="group" data-area={group.area}>
            <div class="group-head"><span class="dot"></span><span>{t(`area.${group.area}`)}</span></div>
            {#each group.items as item (item.activity_id)}
              <div class="habit">
                <span class="name">{item.name}</span>
                <span class="muted">{t(item.done === 1 ? 'review.habitDaysOne' : 'review.habitDays', { done: item.done, total: item.total })}</span>
              </div>
            {/each}
          </div>
        {/each}
          </div>
        </details>
      </section>
    {/if}

    {#if lines.length > 0}
      <section class="card block rise" aria-label={t('review.lines')}>
        <details open={isOpen('review.lines')} ontoggle={(event) => setOpen('review.lines', event.currentTarget.open)}>
          <summary><h2 class="eyebrow">{t('review.lines')}</h2><span class="chev"><Icon name="down" small /></span></summary>
          <div class="fold">
            {#each lines as day (day.day)}
              <div class="line">
                <div class="eyebrow when">{dayLong(day.day)}</div>
                <p>«{day.reflection}»</p>
              </div>
            {/each}
          </div>
        </details>
      </section>
    {/if}

    <section class="card block rise" aria-label={t('review.note')}>
      <details open={isOpen('review.note')} ontoggle={(event) => setOpen('review.note', event.currentTarget.open)}>
        <summary><h2 class="eyebrow">{t('review.note')}</h2><span class="chev"><Icon name="down" small /></span></summary>
        <div class="fold">
          <textarea
            id="week-note"
            class="field"
            rows="5"
            maxlength="5000"
            aria-label={t('review.note')}
            placeholder={t('review.notePlaceholder')}
            bind:value={note}
            oninput={onInput}
            onblur={() => timer && save()}
          ></textarea>
          <p class="muted foot" aria-live="polite">{saved ? t('review.saved') : ''}</p>
          {#if failure}
            <p class="error" role="alert">{failure}</p>
          {/if}
        </div>
      </details>
    </section>
  {/if}
</div>

<style>
  .nav {
    display: flex;
    gap: 8px;
  }

  .nav .btn {
    width: 44px;
    padding: 0;
  }

  .days {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    padding: 16px;
  }

  .day {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 10px 0;
    border-radius: 12px;
    color: var(--ink-3);
  }

  .day.filled {
    background: var(--paper-2);
    color: var(--ink);
  }

  .wd {
    font: 500 11px/1 var(--sans);
    text-transform: uppercase;
  }

  .num {
    font: 500 20px/1 var(--serif);
  }

  .val {
    font: 400 13px/1 var(--sans);
  }

  .foot {
    margin: 8px 2px 0;
    font: 400 13px/1.5 var(--sans);
  }

  .block {
    margin-top: 16px;
    padding: 24px;
  }

  .block h2 {
    display: block;
    margin: 0;
  }

  .block > h2 {
    margin-bottom: 12px;
  }

  summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 32px;
    cursor: pointer;
    list-style: none;
  }

  summary::-webkit-details-marker {
    display: none;
  }

  .chev {
    display: inline-flex;
    color: var(--ink-3);
    transition: transform 0.2s;
  }

  details[open] .chev {
    transform: rotate(180deg);
  }

  .fold {
    margin-top: 14px;
  }

  @media (prefers-reduced-motion: reduce) {
    .chev {
      transition: none;
    }
  }

  .area {
    display: grid;
    grid-template-columns: 12px 110px 1fr 56px 110px;
    align-items: center;
    gap: 12px;
    min-height: 40px;
  }

  .name {
    font: 400 15px/1.3 var(--sans);
  }

  .bar {
    height: 8px;
    border-radius: 4px;
    background: var(--paper-2);
  }

  .bar span {
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

  .group + .group {
    margin-top: 16px;
  }

  .group-head {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
    font: 500 15px/1 var(--sans);
  }

  .habit {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 8px 0 8px 22px;
    border-top: 1px solid var(--line);
    font: 400 14px/1.4 var(--sans);
  }

  .line {
    padding: 10px 0;
    border-top: 1px solid var(--line);
  }

  .line:first-of-type {
    border-top: 0;
  }

  .when {
    font-size: 11px;
    letter-spacing: 0.1em;
  }

  .line p {
    margin: 6px 0 0;
    font: italic 400 17px/1.4 var(--serif);
  }

  textarea.field {
    font: 400 16px/1.6 var(--serif);
  }

  @media (max-width: 560px) {
    .area {
      grid-template-columns: 12px 1fr 56px;
    }

    .bar,
    .diff {
      display: none;
    }
  }
</style>
