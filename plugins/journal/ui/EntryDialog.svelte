<script>
  import { onMount, untrack } from 'svelte';
  import { ApiError, pluginRequest } from '$core/lib/api.js';
  import Link from '$core/components/Link.svelte';
  import { t } from '$core/lib/i18n.svelte.js';
  import { clearDraft, draftKey, loadDraft, pickPrompt, saveDraft } from './journal.js';

  let { entry = null, today, reportDay = null, onsaved, onclose } = $props();

  let dialog;
  const key = untrack(() => draftKey(entry));
  const start = untrack(() => ({
    day: entry?.day ?? today,
    title: entry?.title ?? '',
    body: entry?.body ?? '',
    mood: entry?.mood ?? null,
  }));
  const draft = loadDraft(key);
  const restored = !!draft && (draft.day !== start.day || (draft.title ?? '') !== start.title || draft.body !== start.body || (draft.mood ?? null) !== start.mood);
  const initial = restored ? { ...start, ...draft } : start;

  let day = $state(initial.day);
  let title = $state(initial.title ?? '');
  let body = $state(initial.body);
  let mood = $state(initial.mood ?? null);
  let error = $state('');
  let busy = $state(false);
  let confirmDelete = $state(false);
  let kept = $state(false);
  const prompt = pickPrompt();

  const dirty = $derived(day !== start.day || title !== start.title || body !== start.body || mood !== start.mood);

  $effect(() => {
    if (dirty) saveDraft(key, { day, title, body, mood });
    else clearDraft(key);
  });

  onMount(() => {
    dialog.showModal();
  });

  function guard(event) {
    if (dirty) {
      event.preventDefault();
      kept = true;
    }
  }

  function discard() {
    clearDraft(key);
    dialog.close();
  }

  async function save(event) {
    event.preventDefault();
    busy = true;
    error = '';
    const payload = { day, title: title.trim() || null, body: body.trim(), mood };
    try {
      if (entry) await pluginRequest('journal', 'PUT', `/entries/${entry.id}`, payload);
      else await pluginRequest('journal', 'POST', '/entries', payload);
      clearDraft(key);
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
      clearDraft(key);
      onsaved();
    } catch {
      error = t('error.generic');
      busy = false;
    }
  }
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="entry-dialog-title" {onclose} oncancel={guard}>
  <form onsubmit={save}>
    <h2 id="entry-dialog-title">{entry ? t('plugin.journal.edit') : t('plugin.journal.write')}</h2>
    {#if reportDay}
      <p class="report-link"><Link href={`/review?day=${reportDay}`}>{t('plugin.journal.openReport')}</Link></p>
    {/if}

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

    <div>
      <span class="label" id="entry-mood-label">{t('plugin.journal.mood')}</span>
      <div class="scale" role="group" aria-labelledby="entry-mood-label">
        {#each [1, 2, 3, 4, 5] as level}
          <button
            class="level"
            class:on={mood === level}
            type="button"
            aria-pressed={mood === level}
            aria-label={t('plugin.journal.moodLevel', { level })}
            onclick={() => (mood = mood === level ? null : level)}
          >{level}</button>
        {/each}
      </div>
      <p class="muted hint">{t('plugin.journal.moodHint')}</p>
    </div>

    {#if error}
      <p class="error" role="alert">{error}</p>
    {:else if kept}
      <p class="muted hint" role="status">{t('plugin.journal.kept')}</p>
    {:else if restored}
      <p class="muted hint" role="status">{t('plugin.journal.restored')}</p>
    {/if}

    <div class="actions">
      <button class="btn solid" type="submit" disabled={busy || body.trim() === ''}>{t('common.save')}</button>
      <button class="btn" type="button" onclick={discard}>{t('common.cancel')}</button>
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

  .report-link {
    margin: -4px 0 12px;
    font: 500 13px/1 var(--sans);
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

  .scale {
    display: flex;
    gap: 10px;
  }

  .level {
    width: 42px;
    height: 42px;
    border: 1.5px solid var(--border);
    border-radius: 50%;
    background: var(--surface);
    color: var(--ink);
    font: 500 15px/1 var(--sans);
    cursor: pointer;
  }

  .level.on {
    background: var(--ink);
    border-color: var(--ink);
    color: var(--paper);
  }

  .hint {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
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
