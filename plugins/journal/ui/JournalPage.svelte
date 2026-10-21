<script>
  import { onMount } from 'svelte';
  import { api, pluginRequest } from '$core/lib/api.js';
  import Link from '$core/components/Link.svelte';
  import { formatDate } from '$core/lib/dates.js';
  import { locale, t } from '$core/lib/i18n.svelte.js';
  import EntryDialog from './EntryDialog.svelte';
  import { EXCERPT_LENGTH, PAGE_SIZE, excerpt, groupByMonth, mergeEntries } from './journal.js';

  let today = $state('');
  let entries = $state([]);
  let total = $state(0);
  let query = $state('');
  let status = $state('loading');
  let loadingMore = $state(false);
  let dialogOpen = $state(false);
  let editing = $state(null);
  let expanded = $state(new Set());
  let reload = $state(0);
  let timer = null;

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

<div class="search">
  <label class="label" for="journal-search">{t('plugin.journal.search')}</label>
  <input id="journal-search" class="field" type="search" maxlength="100" placeholder={t('plugin.journal.searchPlaceholder')} oninput={onSearch} />
</div>

{#if status === 'error'}
  <p class="error" role="alert">{t('error.generic')}</p>
{:else if status === 'loading'}
  <p class="lede" aria-live="polite">{t('common.loading')}</p>
{:else if entries.length === 0}
  <section class="card empty">
    <p class="lede">{query.trim() ? t('plugin.journal.noMatches') : t('plugin.journal.empty')}</p>
  </section>
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

  .search {
    max-width: 420px;
    margin: 24px 0 8px;
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
