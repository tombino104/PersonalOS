<script>
  import { api } from '../lib/api.js';
  import { t } from '../lib/i18n.svelte.js';

  let busy = $state(false);
  let failure = $state('');

  async function download() {
    busy = true;
    failure = '';
    try {
      const { blob, name } = await api.exportData();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      failure = t('export.failed');
    } finally {
      busy = false;
    }
  }
</script>

<section class="card panel" aria-label={t('export.title')}>
  <h2>{t('export.title')}</h2>
  <p class="desc">{t('export.lede')}</p>
  <button class="btn solid" type="button" disabled={busy} onclick={download}>{t('export.button')}</button>
  <p class="muted note">{t('export.note')}</p>
  {#if failure}
    <p class="error" role="alert">{failure}</p>
  {/if}
</section>

<style>
  .panel {
    padding: 24px;
    margin-top: 16px;
  }

  h2 {
    margin: 0;
    font: 400 26px/1.2 var(--serif);
  }

  .desc {
    margin: 8px 0 16px;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .note {
    margin: 12px 0 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
