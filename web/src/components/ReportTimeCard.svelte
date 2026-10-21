<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';
  import { t } from '../lib/i18n.svelte.js';

  let locked = $state(false);
  let at = $state('20:00');
  let failure = $state('');

  onMount(() => {
    api
      .settings()
      .then((result) => {
        locked = result.report_lock;
        at = result.report_time;
      })
      .catch(() => {});
  });

  async function save() {
    failure = '';
    try {
      await api.updateSettings({ report_lock: locked, report_time: at || '20:00' });
    } catch {
      failure = t('error.generic');
    }
  }
</script>

<section class="card panel" aria-label={t('reportTime.title')}>
  <h2>{t('reportTime.title')}</h2>
  <p class="desc">{t('reportTime.lede')}</p>
  <label class="check">
    <input type="checkbox" bind:checked={locked} onchange={save} />
    <span>{t('reportTime.lock')}</span>
  </label>
  <div class="when-field">
    <label class="label" for="report-time">{t('reportTime.time')}</label>
    <input id="report-time" class="field" type="time" disabled={!locked} bind:value={at} onchange={save} />
  </div>
  <p class="muted note">{t('reportTime.note')}</p>
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

  .check {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    font: 400 15px/1.5 var(--sans);
  }

  .check input {
    width: 20px;
    height: 20px;
    margin: 0;
    accent-color: var(--ink);
  }

  .when-field {
    width: 160px;
  }

  .field:disabled {
    opacity: 0.5;
  }

  .note {
    margin: 12px 0 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
