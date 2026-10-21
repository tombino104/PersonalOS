<script>
  import { onMount } from 'svelte';
  import { pluginRequest } from '$core/lib/api.js';
  import { t } from '$core/lib/i18n.svelte.js';

  let { day } = $props();

  let value = $state(null);
  let note = $state('');

  onMount(async () => {
    try {
      const entry = await pluginRequest('mood', 'GET', `/entries/${day}`);
      value = entry.value;
      note = entry.note ?? '';
    } catch {
      value = null;
    }
  });
</script>

{#if value !== null || note}
  <div class="section">
    {#if value !== null}
      <div>
        <div class="eyebrow label-row">{t('plugin.mood.title')}</div>
        <div class="dots" role="img" aria-label={t('plugin.mood.levelLabel', { level: value })}>
          {#each [1, 2, 3, 4, 5] as level}
            <span class:filled={level <= value}></span>
          {/each}
        </div>
      </div>
    {/if}
    {#if note}
      <div class="note">
        <div class="eyebrow label-row">{t('plugin.mood.noteTitle')}</div>
        <p>«{note}»</p>
      </div>
    {/if}
  </div>
{/if}

<style>
  .section {
    display: flex;
    flex-wrap: wrap;
    gap: 20px 36px;
  }

  .label-row {
    margin-bottom: 8px;
  }

  .dots {
    display: flex;
    gap: 8px;
  }

  .dots span {
    width: 12px;
    height: 12px;
    border: 1.5px solid var(--ink-2);
    border-radius: 50%;
  }

  .dots span.filled {
    background: var(--ink-2);
  }

  .note {
    flex: 1 1 260px;
  }

  p {
    margin: 0;
    font: italic 400 18px/1.45 var(--serif);
    white-space: pre-wrap;
  }
</style>
