<script>
  import { onMount } from 'svelte';
  import ResetForm from './ResetForm.svelte';
  import { t } from '../lib/i18n.svelte.js';
  import { withBase } from '../lib/router.svelte.js';

  let { onclose } = $props();

  let dialog;

  onMount(() => {
    dialog.showModal();
  });
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="erase-title" {onclose}>
  <h2 id="erase-title">{t('account.eraseTitle')}</h2>
  <p class="intro">{t('reset.lede')}</p>
  <ResetForm plain onreset={() => location.assign(withBase('/'))} />
  <button class="btn cancel" type="button" onclick={() => dialog.close()}>{t('common.cancel')}</button>
</dialog>

<style>
  dialog {
    width: min(480px, calc(100vw - 32px));
    max-height: calc(100dvh - 32px);
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
    margin: 8px 0 20px;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .cancel {
    margin-top: 12px;
  }
</style>
