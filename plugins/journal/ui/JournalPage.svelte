<script>
  import { onMount } from 'svelte';
  import { api, pluginRequest } from '$core/lib/api.js';
  import Link from '$core/components/Link.svelte';
  import { formatDate } from '$core/lib/dates.js';
  import { locale, t } from '$core/lib/i18n.svelte.js';
  import EntryDialog from './EntryDialog.svelte';
  import { EXCERPT_LENGTH, PAGE_SIZE, MEMORY_LENGTH, SHEET_LENGTH, excerpt, groupByMonth, mergeEntries, pinFor, tiltFor } from './journal.js';

  let today = $state('');
  let entries = $state([]);
  let total = $state(0);
  let memories = $state([]);
  let query = $state('');
  let status = $state('loading');
  let loadingMore = $state(false);
  let dialogOpen = $state(false);
  let editing = $state(null);
  let expanded = $state(new Set());
  let reload = $state(0);
  let timer = null;
  let view = $state(storedView());

  function storedView() {
    try {
      return localStorage.getItem('personal-os-journal-view') === 'board' ? 'board' : 'list';
    } catch {
      return 'list';
    }
  }

  function chooseView(next) {
    view = next;
    try {
      localStorage.setItem('personal-os-journal-view', next);
    } catch {
    }
  }

  const groups = $derived(groupByMonth(entries));

  onMount(() => {
    api
      .today()
      .then((result) => {
        today = result.day;
      })
      .catch(() => {});
    return () => clearTimeout(timer);
  });

  $effect(() => {
    const text = query.trim();
    reload;
    pluginRequest('journal', 'GET', `/entries?${new URLSearchParams({ limit: PAGE_SIZE, q: text })}`)
      .then((result) => {
        if (text === query.trim()) {
          entries = result.entries;
          total = result.total;
          status = 'ready';
        }
      })
      .catch(() => {
        status = 'error';
      });
  });

  $effect(() => {
    reload;
    pluginRequest('journal', 'GET', '/memories')
      .then((result) => {
        memories = result.entries;
      })
      .catch(() => {
        memories = [];
      });
  });

  async function more() {
    loadingMore = true;
    try {
      const params = new URLSearchParams({ limit: PAGE_SIZE, offset: entries.length, q: query.trim() });
      const result = await pluginRequest('journal', 'GET', `/entries?${params}`);
      entries = mergeEntries(entries, result.entries);
      total = result.total;
    } catch {
      status = 'error';
    } finally {
      loadingMore = false;
    }
  }

  function onSearch(event) {
    clearTimeout(timer);
    const value = event.currentTarget.value;
    timer = setTimeout(() => {
      query = value;
    }, 250);
  }

  function open(entry) {
    editing = entry;
    dialogOpen = true;
  }

  function saved() {
    dialogOpen = false;
    reload += 1;
  }

  function toggle(id) {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    expanded = next;
  }

  const monthLabel = (month) => formatDate(`${month}-01`, locale(), { month: 'long', year: 'numeric' });
  const shortDay = (day) => formatDate(day, locale(), { day: 'numeric', month: 'short', year: 'numeric' });
  const dayLabel = (day) => formatDate(day, locale(), { weekday: 'long', day: 'numeric', month: 'long' });
</script>

<Link class="back" href="/more">
  <svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('nav.more')}
</Link>
<header class="head">
  <div>
    <div class="eyebrow">{t('plugin.journal.eyebrow')}</div>
    <h1 class="title">{t('plugin.journal.heading')} <em>{t('plugin.journal.headingEmphasis')}</em></h1>
    <p class="lede">{t('plugin.journal.lede')}</p>
  </div>
  <button class="btn solid" type="button" disabled={!today} onclick={() => open(null)}>{t('plugin.journal.write')}</button>
</header>

{#if status === 'ready' && memories.length && !query.trim()}
  <section class="card memories" aria-label={t('plugin.journal.memories')}>
    <div class="eyebrow">{t('plugin.journal.memories')}</div>
    {#each memories as entry (entry.id)}
      <button class="memory" type="button" onclick={() => open(entry)}>
        <span class="muted ago">{entry.years_ago === 1 ? t('plugin.journal.yearAgo') : t('plugin.journal.yearsAgo', { count: entry.years_ago })}</span>
        {#if entry.title}
          <span class="memory-title">{entry.title}</span>
        {/if}
        <span class="memory-body">{excerpt(entry.body, MEMORY_LENGTH).text}</span>
      </button>
    {/each}
  </section>
{/if}

<div class="tools">
  <div class="search">
    <label class="label" for="journal-search">{t('plugin.journal.search')}</label>
    <input id="journal-search" class="field" type="search" maxlength="100" placeholder={t('plugin.journal.searchPlaceholder')} oninput={onSearch} />
  </div>
  <div class="segmented" role="group" aria-label={t('plugin.journal.view')}>
    <button class="seg" class:on={view === 'list'} aria-pressed={view === 'list'} onclick={() => chooseView('list')}>{t('plugin.journal.viewList')}</button>
    <button class="seg" class:on={view === 'board'} aria-pressed={view === 'board'} onclick={() => chooseView('board')}>{t('plugin.journal.viewBoard')}</button>
  </div>
</div>

{#if status === 'error'}
  <p class="error" role="alert">{t('error.generic')}</p>
{:else if status === 'loading'}
  <p class="lede" aria-live="polite">{t('common.loading')}</p>
{:else if entries.length === 0}
  <section class="card empty">
    <p class="lede">{query.trim() ? t('plugin.journal.noMatches') : t('plugin.journal.empty')}</p>
  </section>
{:else if view === 'board'}
  <div class="board">
    {#each entries as entry (entry.id)}
      <button
        class="sheet"
        type="button"
        style:--tilt="{tiltFor(entry.id)}deg"
        style:--pin="var(--area-{pinFor(entry.id)})"
        onclick={() => open(entry)}
      >
        <span class="pin" aria-hidden="true"></span>
        <span class="eyebrow when">{shortDay(entry.day)}</span>
        {#if entry.title}
          <span class="sheet-title">{entry.title}</span>
        {/if}
        <span class="sheet-body">{excerpt(entry.body, SHEET_LENGTH).text}</span>
        {#if entry.mood}
          <span class="muted sheet-mood">{t('plugin.journal.moodShort', { level: entry.mood })}</span>
        {/if}
      </button>
    {/each}
  </div>
  {#if entries.length < total}
    <button class="btn more-btn" type="button" disabled={loadingMore} onclick={more}>{t('plugin.journal.loadMore', { count: total - entries.length })}</button>
  {/if}
{:else}
  {#each groups as group (group.month)}
    <section class="month" aria-label={monthLabel(group.month)}>
      <h2 class="eyebrow month-title">{monthLabel(group.month)}</h2>
      {#each group.entries as entry (entry.id)}
        {@const shown = expanded.has(entry.id) ? { text: entry.body, truncated: false } : excerpt(entry.body, EXCERPT_LENGTH)}
        <article class="card entry rise">
          <div class="entry-head">
            <div>
              <div class="eyebrow when">{dayLabel(entry.day)}</div>
              {#if entry.title}
                <h3>{entry.title}</h3>
              {/if}
            </div>
            <button class="btn" type="button" onclick={() => open(entry)}>{t('plugin.journal.editShort')}</button>
          </div>
          {#if entry.mood}
            <p class="muted entry-mood">{t('plugin.journal.moodShort', { level: entry.mood })}</p>
          {/if}
          <p class="body">{shown.text}</p>
          {#if entry.body.length > EXCERPT_LENGTH}
            <button class="link" type="button" aria-expanded={expanded.has(entry.id)} onclick={() => toggle(entry.id)}>
              {expanded.has(entry.id) ? t('plugin.journal.less') : t('plugin.journal.more')}
            </button>
          {/if}
        </article>
      {/each}
    </section>
  {/each}
  {#if entries.length < total}
    <button class="btn more-btn" type="button" disabled={loadingMore} onclick={more}>{t('plugin.journal.loadMore', { count: total - entries.length })}</button>
  {/if}
{/if}

<p class="muted foot">{t('plugin.journal.foot')}</p>

{#if dialogOpen}
  {#key editing?.id ?? 'new'}
    <EntryDialog entry={editing} {today} onsaved={saved} onclose={() => (dialogOpen = false)} />
  {/key}
{/if}

<style>
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
  }

  .tools {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    margin: 24px 0 8px;
  }

  .search {
    flex: 1 1 260px;
    max-width: 420px;
  }

  .memories {
    margin-top: 24px;
    padding: 18px 24px 8px;
  }

  .memory {
    display: block;
    width: 100%;
    padding: 12px 0;
    border: 0;
    border-top: 1px solid var(--line);
    background: none;
    color: var(--ink);
    text-align: left;
    cursor: pointer;
  }

  .memory:first-of-type {
    margin-top: 10px;
  }

  .ago {
    display: block;
    font: 400 13px/1.4 var(--sans);
  }

  .memory-title {
    display: block;
    margin-top: 4px;
    font: 500 18px/1.3 var(--serif);
  }

  .memory-body {
    display: block;
    margin-top: 4px;
    font: 400 16px/1.5 var(--serif);
    overflow-wrap: anywhere;
  }

  .entry-mood {
    margin: 8px 0 0;
    font: 400 13px/1.4 var(--sans);
  }

  .board {
    columns: 240px;
    column-gap: 22px;
    margin-top: 24px;
    padding: 0 4px;
  }

  .sheet {
    position: relative;
    display: block;
    width: 100%;
    margin: 0 0 22px;
    padding: 30px 18px 16px;
    border: 1px solid var(--line);
    border-radius: 3px 3px 6px 3px;
    background: var(--surface);
    box-shadow: var(--shadow);
    color: var(--ink);
    text-align: left;
    cursor: pointer;
    break-inside: avoid;
    transform: rotate(var(--tilt));
    transition:
      transform 0.2s ease,
      box-shadow 0.2s ease;
  }

  .sheet:hover,
  .sheet:focus-visible {
    transform: rotate(0deg) translateY(-3px);
  }

  .pin {
    position: absolute;
    top: 10px;
    left: 50%;
    width: 12px;
    height: 12px;
    margin-left: -6px;
    border-radius: 50%;
    background: var(--pin);
    box-shadow: 0 2px 3px rgba(28, 26, 23, 0.3);
  }

  .sheet .when {
    display: block;
  }

  .sheet-title {
    display: block;
    margin-top: 6px;
    font: 500 19px/1.25 var(--serif);
  }

  .sheet-body {
    display: block;
    margin-top: 10px;
    font: 400 15px/28px var(--serif);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    background-image: repeating-linear-gradient(to bottom, transparent 0 27px, var(--line) 27px 28px);
  }

  .sheet-mood {
    display: block;
    margin-top: 10px;
    font: 400 12px/1.4 var(--sans);
  }

  @media (prefers-reduced-motion: reduce) {
    .sheet {
      transition: none;
    }
  }

  .empty {
    margin-top: 16px;
    padding: 20px 24px;
  }

  .month {
    margin-top: 24px;
  }

  .month-title {
    margin: 0 0 12px;
  }

  .entry {
    margin-bottom: 12px;
    padding: 20px 24px;
  }

  .entry-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .when {
    font-size: 11px;
    letter-spacing: 0.1em;
  }

  h3 {
    margin: 6px 0 0;
    font: 500 22px/1.25 var(--serif);
  }

  .body {
    margin: 12px 0 0;
    font: 400 17px/1.6 var(--serif);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .link {
    margin-top: 8px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-2);
    font: 500 14px/1.4 var(--sans);
    text-decoration: underline;
    cursor: pointer;
  }

  .more-btn {
    margin-top: 8px;
  }

  .foot {
    margin: 24px 0 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
