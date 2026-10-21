<script>
  import { onMount, untrack } from 'svelte';
  import { ApiError, pluginRequest } from '$core/lib/api.js';
  import { t } from '$core/lib/i18n.svelte.js';
  import { pickPrompt } from './journal.js';

  let { entry = null, today, onsaved, onclose } = $props();

  let dialog;
  let day = $state(untrack(() => entry?.day ?? today));
  let title = $state(untrack(() => entry?.title ?? ''));
  let body = $state(untrack(() => entry?.body ?? ''));
  let error = $state('');
  let busy = $state(false);
  let confirmDelete = $state(false);
  const prompt = pickPrompt();

  onMount(() => {
    dialog.showModal();
  });

  async function save(event) {
    event.preventDefault();
    busy = true;
    error = '';
    const payload = { day, title: title.trim() || null, body: body.trim() };
    try {
      if (entry) await pluginRequest('journal', 'PUT', `/entries/${entry.id}`, payload);
      else await pluginRequest('journal', 'POST', '/entries', payload);
      onsaved();
    } catch (failure) {
      error = failure instanceof ApiError && failure.status === 422 ? t('plugin.journal.invalid') : t('error.generic');
      busy = false;
    }
  }

  async function remove() {
    if (!confirmDelete) {
      confirmDelete = true;
      return;
    }
    busy = true;
    error = '';
    try {
      await pluginRequest('journal', 'DELETE', `/entries/${entry.id}`);
      onsaved();
    } catch {
      error = t('error.generic');
      busy = false;
    }
  }
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="entry-dialog-title" {onclose}>
  <form onsubmit={save}>
    <h2 id="entry-dialog-title">{entry ? t('plugin.journal.edit') : t('plugin.journal.write')}</h2>

    <div class="row">
      <div class="grow">
        <label class="label" for="entry-title">{t('plugin.journal.title')}</label>
        <input id="entry-title" class="field" type="text" maxlength="120" placeholder={t('plugin.journal.titleOptional')} bind:value={title} />
      </div>
      <div class="when">
        <label class="label" for="entry-day">{t('plugin.journal.day')}</label>
        <input id="entry-day" class="field" type="date" required max={today} bind:value={day} />
      </div>
    </div>

    <div>
      <label class="label" for="entry-body">{t('plugin.journal.text')}</label>
      <textarea
        id="entry-body"
        class="field"
        rows="12"
        maxlength="20000"
        required
        placeholder={t(`plugin.journal.prompt.${prompt}`)}
        bind:value={body}
      ></textarea>
    </div>

    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}

    <div class="actions">
      <button class="btn solid" type="submit" disabled={busy || body.trim() === ''}>{t('common.save')}</button>
      <button class="btn" type="button" onclick={() => dialog.close()}>{t('common.cancel')}</button>
      {#if entry}
        <button class="btn remove" type="button" disabled={busy} onclick={remove}>
          {confirmDelete ? t('plugin.journal.deleteSure') : t('plugin.journal.delete')}
        </button>
      {/if}
    </div>
  </form>
</dialog>

<style>
  dialog {
    width: min(640px, calc(100vw - 32px));
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
    gap: 20px;
  }

  h2 {
    margin: 0;
    font: 400 26px/1.2 var(--serif);
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  .grow {
    flex: 1 1 220px;
  }

  .when {
    flex: 0 0 170px;
  }

  textarea.field {
    min-height: 220px;
    resize: vertical;
    font: 400 16px/1.6 var(--serif);
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .remove {
    margin-left: auto;
  }
</style>
