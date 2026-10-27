<script>
  import { onMount } from 'svelte';
  import { pluginRequest } from '$core/lib/api.js';
  import { t } from '$core/lib/i18n.svelte.js';

  let { day, editable } = $props();

  let value = $state(null);
  let note = $state('');
  let saved = $state(false);
  let failed = $state(false);

  onMount(async () => {
    try {
      const entry = await pluginRequest('mood', 'GET', `/entries/${day}`);
      value = entry.value;
      note = entry.note ?? '';
    } catch {
      failed = true;
    }
  });

  async function save() {
    try {
      await pluginRequest('mood', 'PUT', `/entries/${day}`, {
        value,
        note: note === '' ? null : note,
      });
      saved = true;
      failed = false;
    } catch {
      failed = true;
    }
  }

  function choose(level) {
    value = value === level ? null : level;
    saved = false;
    save();
  }
</script>

<div class="head">
  <h2>{t('plugin.mood.title')}</h2>
  <span class="muted tag">{t('plugin.mood.tag') + (saved ? ` · ${t('plugin.mood.saved')}` : '')}</span>
</div>

<div class="scale" role="group" aria-label={t('plugin.mood.scaleLabel')}>
  {#each [1, 2, 3, 4, 5] as level}
    <button
      class="level"
      class:on={value === level}
      type="button"
      aria-pressed={value === level}
      aria-label={t('plugin.mood.levelLabel', { level })}
      disabled={!editable}
      onclick={() => choose(level)}
    >{level}</button>
  {/each}
</div>
<div class="ends muted"><span>{t('plugin.mood.low')}</span><span>{t('plugin.mood.high')}</span></div>
{#if failed}
  <p class="error" role="alert">{t('error.generic')}</p>
{/if}

<style>
  .head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  h2 {
    margin: 0;
    font: 500 20px/1 var(--serif);
  }

  .tag {
    font: 400 12px/1 var(--sans);
  }

  .scale {
    display: flex;
    justify-content: space-between;
  }

  .level {
    width: 48px;
    height: 48px;
    border: 1.5px solid var(--border);
    border-radius: 50%;
    background: var(--surface);
    color: var(--ink);
    font: 500 16px/1 var(--sans);
    cursor: pointer;
  }

  .level.on {
    background: var(--ink);
    border-color: var(--ink);
    color: var(--paper);
  }

  .level:disabled {
    cursor: default;
    opacity: 0.6;
  }

  .ends {
    display: flex;
    justify-content: space-between;
    margin: 8px 2px 0;
    font: 400 12px/1 var(--sans);
  }
</style>
