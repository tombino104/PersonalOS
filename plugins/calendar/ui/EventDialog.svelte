<script>
  import { onMount, untrack } from 'svelte';
  import { ApiError, pluginRequest } from '$core/lib/api.js';
  import { t } from '$core/lib/i18n.svelte.js';
  import { CATEGORIES, REPEATS } from './calendar.js';

  let { event = null, day, onsaved, onclose } = $props();

  let dialog;
  let title = $state(untrack(() => event?.title ?? ''));
  let date = $state(untrack(() => event?.day ?? day));
  let allDay = $state(untrack(() => !event?.time));
  let time = $state(untrack(() => event?.time ?? '09:00'));
  let category = $state(untrack(() => event?.category ?? 'personal'));
  let repeat = $state(untrack(() => event?.repeat ?? 'none'));
  let until = $state(untrack(() => event?.until ?? ''));
  let notes = $state(untrack(() => event?.notes ?? ''));
  let error = $state('');
  let busy = $state(false);
  let confirmDelete = $state(false);

  onMount(() => {
    dialog.showModal();
  });

  async function save(submitEvent) {
    submitEvent.preventDefault();
    busy = true;
    error = '';
    const body = {
      title: title.trim(),
      day: date,
      time: allDay ? null : time,
      category,
      notes: notes.trim() || null,
      repeat,
      until: repeat === 'none' || !until ? null : until,
    };
    try {
      if (event) await pluginRequest('calendar', 'PUT', `/events/${event.id}`, body);
      else await pluginRequest('calendar', 'POST', '/events', body);
      onsaved();
    } catch (failure) {
      error = failure instanceof ApiError && failure.status === 422 ? t('plugin.calendar.invalid') : t('error.generic');
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
      await pluginRequest('calendar', 'DELETE', `/events/${event.id}`);
      onsaved();
    } catch {
      error = t('error.generic');
      busy = false;
    }
  }
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="event-dialog-title" {onclose}>
  <form onsubmit={save}>
    <h2 id="event-dialog-title">{event ? t('plugin.calendar.edit') : t('plugin.calendar.add')}</h2>

    <div>
      <label class="label" for="event-title">{t('plugin.calendar.title')}</label>
      <input id="event-title" class="field" type="text" maxlength="120" required bind:value={title} />
    </div>

    <div class="row">
      <div class="grow">
        <label class="label" for="event-day">{t('plugin.calendar.day')}</label>
        <input id="event-day" class="field" type="date" required bind:value={date} />
      </div>
      <div class="grow">
        <label class="label" for="event-time">{t('plugin.calendar.time')}</label>
        <input id="event-time" class="field" type="time" required={!allDay} disabled={allDay} bind:value={time} />
      </div>
    </div>
    <label class="check">
      <input type="checkbox" bind:checked={allDay} />
      <span>{t('plugin.calendar.allDay')}</span>
    </label>

    <div class="row">
      <div class="grow">
        <label class="label" for="event-category">{t('plugin.calendar.category')}</label>
        <select id="event-category" class="field" bind:value={category}>
          {#each CATEGORIES as item}
            <option value={item}>{t(`plugin.calendar.category.${item}`)}</option>
          {/each}
        </select>
      </div>
      <div class="grow">
        <label class="label" for="event-repeat">{t('plugin.calendar.repeat')}</label>
        <select id="event-repeat" class="field" bind:value={repeat}>
          {#each REPEATS as item}
            <option value={item}>{t(`plugin.calendar.repeat.${item}`)}</option>
          {/each}
        </select>
      </div>
    </div>

    {#if repeat !== 'none'}
      <div>
        <label class="label" for="event-until">{t('plugin.calendar.until')}</label>
        <input id="event-until" class="field" type="date" min={date} bind:value={until} />
        <p class="muted help">{t('plugin.calendar.untilHelp')}</p>
      </div>
    {/if}

    <div>
      <label class="label" for="event-notes">{t('plugin.calendar.notes')}</label>
      <textarea id="event-notes" class="field" rows="3" maxlength="500" bind:value={notes}></textarea>
    </div>

    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}

    <div class="actions">
      <button class="btn solid" type="submit" disabled={busy}>{t('common.save')}</button>
      <button class="btn" type="button" onclick={() => dialog.close()}>{t('common.cancel')}</button>
      {#if event}
        <button class="btn remove" type="button" disabled={busy} onclick={remove}>
          {confirmDelete ? t('plugin.calendar.deleteSure') : t('plugin.calendar.delete')}
        </button>
      {/if}
    </div>
    {#if event && confirmDelete && event.repeat !== 'none'}
      <p class="muted help">{t('plugin.calendar.deleteSeries')}</p>
    {/if}
  </form>
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

  form {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  h2 {
    margin: 0;
    font: 400 26px/1.2 var(--serif);
  }

  select.field {
    appearance: auto;
  }

  .field:disabled {
    opacity: 0.5;
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  .grow {
    flex: 1 1 160px;
  }

  .check {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: -8px;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .check input {
    width: 20px;
    height: 20px;
    margin: 0;
    accent-color: var(--ink);
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .remove {
    margin-left: auto;
  }

  .help {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
