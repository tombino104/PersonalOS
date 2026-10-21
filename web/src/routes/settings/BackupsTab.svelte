<script>
  import { onMount } from 'svelte';
  import RestoreDialog from '../../components/RestoreDialog.svelte';
  import { ApiError, api } from '../../lib/api.js';
  import { locale, t } from '../../lib/i18n.svelte.js';
  import { formatBytes } from '../../lib/backups.js';

  let backups = $state([]);
  let keep = $state({ auto: 7 });
  let loaded = $state(false);
  let busy = $state(false);
  let failure = $state('');
  let restoring = $state(null);
  let restoreError = $state('');
  let fileInput;

  const when = (iso) =>
    new Intl.DateTimeFormat(locale(), { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso));

  async function load() {
    try {
      const result = await api.backups();
      backups = result.backups;
      keep = result.keep;
      failure = '';
    } catch {
      failure = t('error.generic');
    } finally {
      loaded = true;
    }
  }

  onMount(load);

  async function backUpNow() {
    busy = true;
    failure = '';
    try {
      const item = await api.createBackup();
      const link = document.createElement('a');
      link.href = api.backupUrl(item.name);
      link.download = item.name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      await load();
    } catch {
      failure = t('backups.failed');
    } finally {
      busy = false;
    }
  }

  function chooseFile(event) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';
    if (file) {
      restoreError = '';
      restoring = { label: file.name, file };
    }
  }

  async function confirmRestore() {
    busy = true;
    restoreError = '';
    try {
      if (restoring.file) await api.restoreUpload(restoring.file);
      else await api.restoreStored(restoring.name);
      location.assign('/');
    } catch (error) {
      if (error instanceof ApiError && error.code === 'invalid_backup') restoreError = t('backups.invalid');
      else if (error instanceof ApiError && error.code === 'too_large') restoreError = t('backups.tooLarge');
      else restoreError = t('backups.restoreFailed');
      busy = false;
    }
  }
</script>

<section class="card panel" aria-label={t('settings.backups')}>
  <h2>{t('settings.backups')}</h2>
  <p class="desc">{t('backups.lede', { count: keep.auto })}</p>
  <div class="actions">
    <button class="btn solid" type="button" disabled={busy} onclick={backUpNow}>{t('backups.now')}</button>
    <button class="btn" type="button" disabled={busy} onclick={() => fileInput.click()}>{t('backups.fromFile')}</button>
    <input
      bind:this={fileInput}
      class="hidden"
      type="file"
      accept=".zip,application/zip"
      aria-label={t('backups.fromFile')}
      onchange={chooseFile}
    />
  </div>
  <p class="muted note">{t('backups.nowNote')}</p>
  {#if failure}
    <p class="error" role="alert">{failure}</p>
  {/if}
</section>

<section class="card panel list" aria-label={t('backups.saved')}>
  <h2>{t('backups.saved')}</h2>
  {#if !loaded}
    <p class="muted" aria-live="polite">{t('common.loading')}</p>
  {:else if backups.length === 0}
    <p class="muted">{t('backups.none')}</p>
  {/if}
  {#each backups as item (item.name)}
    <div class="item">
      <div class="info">
        <span class="name">{when(item.created_at)}</span>
        <span class="muted meta">{t(`backups.kind.${item.kind}`)} · {formatBytes(item.size)}</span>
      </div>
      <a class="btn" href={api.backupUrl(item.name)} download={item.name}>{t('backups.download')}</a>
      <button
        class="btn"
        type="button"
        disabled={busy}
        onclick={() => {
          restoreError = '';
          restoring = { label: when(item.created_at), name: item.name };
        }}
      >
        {t('backups.restore')}
      </button>
    </div>
  {/each}
</section>

{#if restoring}
  <RestoreDialog
    label={restoring.label}
    {busy}
    error={restoreError}
    onconfirm={confirmRestore}
    oncancel={() => (restoring = null)}
  />
{/if}

<style>
  .panel {
    padding: 24px;
  }

  .list {
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

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .hidden {
    display: none;
  }

  .note {
    margin: 12px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .item {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    padding: 12px 0;
    border-top: 1px solid var(--line);
  }

  .item:first-of-type {
    margin-top: 12px;
  }

  .info {
    display: flex;
    flex: 1 1 200px;
    flex-direction: column;
    gap: 4px;
  }

  .name {
    font: 500 15px/1.3 var(--sans);
  }

  .meta {
    font: 400 13px/1.3 var(--sans);
  }
</style>
