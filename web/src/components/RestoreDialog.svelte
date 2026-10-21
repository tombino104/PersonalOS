<script>
  import { onMount } from 'svelte';
  import { t } from '../lib/i18n.svelte.js';

  let { label, busy = false, error = '', onconfirm, oncancel } = $props();

  const WORD = 'restore';

  let dialog;
  let typed = $state('');

  onMount(() => {
    dialog.showModal();
  });
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="restore-title" onclose={oncancel}>
  <form
    onsubmit={(event) => {
      event.preventDefault();
      if (typed.trim().toLowerCase() === WORD) onconfirm();
    }}
  >
    <h2 id="restore-title">{t('backups.restoreTitle')}</h2>
    <p class="source">{label}</p>
    <p class="intro">{t('backups.restoreBody')}</p>
    <label class="label" for="restore-confirm">{t('backups.restoreLabel', { word: WORD })}</label>
    <input
      id="restore-confirm"
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
      <button class="btn danger" type="submit" disabled={busy || typed.trim().toLowerCase() !== WORD}>
        {t('backups.restoreButton')}
      </button>
      <button class="btn" type="button" onclick={() => dialog.close()}>{t('common.cancel')}</button>
    </div>
  </form>
</dialog>

<style>
  dialog {
    width: min(460px, calc(100vw - 32px));
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

  .source {
    margin: 0;
    font: 500 14px/1.4 var(--sans);
    word-break: break-all;
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
