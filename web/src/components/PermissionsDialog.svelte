<script>
  import { onMount } from 'svelte';
  import { t } from '../lib/i18n.svelte.js';

  let { name, permissions, busy = false, onconfirm, oncancel } = $props();

  let dialog;

  onMount(() => {
    dialog.showModal();
  });
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="permissions-title" onclose={oncancel}>
  <h2 id="permissions-title">{t('plugins.confirmTitle', { name })}</h2>
  <p class="intro">{permissions.length ? t('plugins.confirmBody') : t('plugins.confirmNone')}</p>
  {#if permissions.length}
    <ul>
      {#each permissions as permission}
        <li>{t(`permission.${permission}`)}</li>
      {/each}
    </ul>
  {/if}
  <div class="actions">
    <button class="btn solid" type="button" disabled={busy} onclick={onconfirm}>{t('plugins.confirmButton')}</button>
    <button class="btn" type="button" onclick={() => dialog.close()}>{t('common.cancel')}</button>
  </div>
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

  h2 {
    margin: 0;
    font: 400 26px/1.2 var(--serif);
  }

  .intro {
    margin: 12px 0;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  ul {
    margin: 0 0 20px;
    padding-left: 20px;
    font: 400 15px/1.6 var(--sans);
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
</style>
