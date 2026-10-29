<script>
  import { onMount } from 'svelte';
  import { pluginRequest } from '$core/lib/api.js';
  import { t } from '$core/lib/i18n.svelte.js';
  import { EXCERPT_LENGTH, excerpt } from './journal.js';

  let { day } = $props();

  let entries = $state([]);
  let expanded = $state(new Set());

  onMount(async () => {
    try {
      const params = new URLSearchParams({ start: day, end: day, limit: 100 });
      const result = await pluginRequest('journal', 'GET', `/entries?${params}`);
      entries = [...result.entries].reverse();
    } catch {
      entries = [];
    }
  });

  function toggle(id) {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    expanded = next;
  }
</script>

{#if entries.length > 0}
  <div class="section">
    <div class="eyebrow label-row">{t('plugin.journal.reportTitle')}</div>
    {#each entries as entry (entry.id)}
      {@const shown = expanded.has(entry.id) ? { text: entry.body, truncated: false } : excerpt(entry.body, EXCERPT_LENGTH)}
      <article class="entry">
        {#if entry.title}
          <h3>{entry.title}</h3>
        {/if}
        {#if entry.mood}
          <p class="muted mood">{t('plugin.journal.moodShort', { level: entry.mood })}</p>
        {/if}
        <p class="body">{shown.text}</p>
        {#if shown.truncated || expanded.has(entry.id)}
          <button class="link" type="button" aria-expanded={expanded.has(entry.id)} onclick={() => toggle(entry.id)}>
            {expanded.has(entry.id) ? t('plugin.journal.less') : t('plugin.journal.more')}
          </button>
        {/if}
      </article>
    {/each}
  </div>
{/if}

<style>
  .label-row {
    margin-bottom: 8px;
  }

  .entry + .entry {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--line);
  }

  h3 {
    margin: 0 0 4px;
    font: 500 17px/1.3 var(--serif);
  }

  .mood {
    margin: 0 0 4px;
    font: 400 12.5px/1.4 var(--sans);
  }

  .body {
    margin: 0;
    font: italic 400 16px/1.55 var(--serif);
    white-space: pre-wrap;
  }

  .link {
    margin-top: 6px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-2);
    font: 500 13px/1 var(--sans);
    text-decoration: underline;
    cursor: pointer;
  }
</style>
