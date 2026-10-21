<script>
  import { onMount } from 'svelte';
  import { t } from '../lib/i18n.svelte.js';

  let { id, name, busy = false, error = '', onconfirm, oncancel } = $props();

  let dialog;
  let typed = $state('');

  onMount(() => {
    dialog.showModal();
  });
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="remove-title" onclose={oncancel}>
  <form
    onsubmit={(event) => {
      event.preventDefault();
      if (typed === id) onconfirm(typed);
    }}
  >
    <h2 id="remove-title">{t('plugins.removeTitle', { name })}</h2>
    <p class="intro">{t('plugins.removeBody')}</p>
    <label class="label" for="remove-confirm">{t('plugins.removeLabel', { id })}</label>
    <input
      id="remove-confirm"
      class="field"
      type="text"
      autocomplete="off"
      autocapitalize="none"
      spellcheck="false"
      bind:value={typed}
    />
    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}
    <div class="actions">
      <button class="btn danger" type="submit" disabled={busy || typed !== id}>{t('plugins.removeButton')}</button>
      <button class="btn" type="button" onclick={() => dialog.close()}>{t('common.cancel')}</button>
    </div>
  </form>
</dialog>

<style>
  dialog {
    width: min(440px, calc(100vw - 32px));
    padding: 24px;
    color: var(--ink);
    box-shadow: var(--shadow);
  }

  dialog::backdrop {
    background: rgba(28, 26, 23, 0.45);
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  h2 {
    margin: 0;
    font: 400 26px/1.2 var(--serif);
  }

  .intro {
    margin: 0;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 8px;
  }

  .danger {
    background: var(--danger);
    border-color: var(--danger);
    color: var(--paper);
  }

  .danger:hover {
    background: var(--danger);
  }
</style>
