<script>
  import { onMount, untrack } from 'svelte';
  import { api, ApiError } from '../lib/api.js';
  import { AREAS } from '../lib/charts.js';
  import { weekdayInitials } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { SUGGESTIONS } from '../lib/suggestions.js';

  let { activity = null, area = 'physical', onsaved, onclose } = $props();

  let dialog;
  let name = $state(untrack(() => activity?.name ?? ''));
  let description = $state(untrack(() => activity?.description ?? ''));
  let chosenArea = $state(untrack(() => activity?.area ?? area));
  let weight = $state(untrack(() => activity?.weight ?? 2));
  let days = $state(untrack(() => activity?.days ?? [0, 1, 2, 3, 4, 5, 6]));
  let times = $state(untrack(() => activity?.times_per_week ?? 0));
  const initials = $derived(weekdayInitials(locale()));
  let ideasOpen = $state(false);
  const ideas = $derived(SUGGESTIONS[chosenArea] ?? []);

  function pick(idea) {
    name = t(`suggestion.${chosenArea}.${idea.id}`);
    weight = idea.weight;
    times = idea.times;
    ideasOpen = false;
  }

  function toggleDay(index) {
    if (days.includes(index)) {
      if (days.length > 1) days = days.filter((day) => day !== index);
    } else {
      days = [...days, index].sort();
    }
  }
  let error = $state('');
  let busy = $state(false);
  let confirmDelete = $state(false);

  onMount(() => {
    dialog.showModal();
  });

  async function save(event) {
    event.preventDefault();
    busy = true;
    error = '';
    try {
      if (activity) {
        await api.updateActivity(activity.id, { name: name.trim(), description: description.trim(), area: chosenArea, weight, days, times_per_week: times });
      } else {
        await api.createActivity({ name: name.trim(), description: description.trim(), area: chosenArea, weight, days, times_per_week: times });
      }
      onsaved();
    } catch (failure) {
      error = failure instanceof ApiError && failure.status === 422 ? t('activity.invalid') : t('error.generic');
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
      await api.deleteActivity(activity.id);
      onsaved();
    } catch {
      error = t('error.generic');
      busy = false;
    }
  }

  async function toggleArchive() {
    busy = true;
    error = '';
    try {
      await api.updateActivity(activity.id, { archived: !activity.archived_at });
      onsaved();
    } catch {
      error = t('error.generic');
      busy = false;
    }
  }
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="activity-dialog-title" {onclose}>
  <form onsubmit={save}>
    <h2 id="activity-dialog-title">{activity ? t('activity.edit') : t('activity.add')}</h2>

    <div>
      <label class="label" for="activity-name">{t('activity.name')}</label>
      <input id="activity-name" class="field" type="text" maxlength="100" required bind:value={name} />
      {#if !activity}
        <button class="ideas-toggle" type="button" aria-expanded={ideasOpen} onclick={() => (ideasOpen = !ideasOpen)}>{t('activity.ideas')}</button>
        {#if ideasOpen}
          <div class="chips" role="group" aria-label={t('activity.ideas')}>
            {#each ideas as idea (idea.id)}
              <button class="chip" type="button" onclick={() => pick(idea)}>{t(`suggestion.${chosenArea}.${idea.id}`)}</button>
            {/each}
          </div>
          <p class="muted help">{t('activity.ideasHelp')}</p>
        {/if}
      {/if}
    </div>

    <div>
      <label class="label" for="activity-description">{t('activity.description')}</label>
      <textarea
        id="activity-description"
        class="field"
        rows="2"
        maxlength="300"
        placeholder={t('activity.descriptionPlaceholder')}
        bind:value={description}
      ></textarea>
    </div>

    <div>
      <label class="label" for="activity-area">{t('activity.area')}</label>
      <select id="activity-area" class="field" bind:value={chosenArea}>
        {#each AREAS as item}
          <option value={item}>{t(`area.${item}`)}</option>
        {/each}
      </select>
    </div>

    <div>
      <span class="label" id="activity-weight-label">{t('activity.weight')}</span>
      <div class="segmented" role="group" aria-labelledby="activity-weight-label">
        {#each [1, 2, 3] as option}
          <button type="button" class="seg" class:on={weight === option} aria-pressed={weight === option} onclick={() => (weight = option)}>{option}</button>
        {/each}
      </div>
      <p class="muted help">{t('activity.weightHelp')}</p>
    </div>

    <div>
      <span class="label" id="activity-days-label">{t('activity.days')}</span>
      <div class="days" role="group" aria-labelledby="activity-days-label">
        {#each initials as letter, index}
          <button type="button" class="day" class:on={days.includes(index)} aria-pressed={days.includes(index)} onclick={() => toggleDay(index)}>
            <span aria-hidden="true">{letter}</span>
            <span class="sr">{new Intl.DateTimeFormat(locale(), { weekday: 'long', timeZone: 'UTC' }).format(new Date(Date.UTC(2024, 0, 1 + index)))}</span>
          </button>
        {/each}
      </div>
      <p class="muted help">{t('activity.daysHelp')}</p>
    </div>

    <div>
      <label class="label" for="activity-times">{t('activity.times')}</label>
      <select id="activity-times" class="field" bind:value={times}>
        <option value={0}>{t('activity.timesNone')}</option>
        {#each [1, 2, 3, 4, 5, 6, 7] as count}
          <option value={count}>{t(count === 1 ? 'activity.timesOne' : 'activity.timesMany', { count })}</option>
        {/each}
      </select>
      <p class="muted help">{t('activity.timesHelp')}</p>
    </div>

    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}

    <div class="actions">
      <button class="btn solid" type="submit" disabled={busy}>{t('common.save')}</button>
      <button class="btn" type="button" onclick={() => dialog.close()}>{t('common.cancel')}</button>
      {#if activity}
        <button class="btn archive" type="button" disabled={busy} onclick={toggleArchive}>
          {activity.archived_at ? t('activity.restore') : t('activity.archive')}
        </button>
      {/if}
      {#if activity?.archived_at}
        <button class="btn remove" type="button" disabled={busy} onclick={remove}>
          {confirmDelete ? t('activity.deleteSure') : t('activity.delete')}
        </button>
      {/if}
    </div>
    {#if activity && !activity.archived_at}
      <p class="muted help">{t('activity.archiveHelp')}</p>
    {/if}
    {#if activity?.archived_at}
      <p class="muted help">{t('activity.deleteHelp')}</p>
    {/if}
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
    gap: 20px;
  }

  h2 {
    margin: 0;
    font: 400 26px/1.2 var(--serif);
  }

  select.field {
    appearance: auto;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .archive {
    margin-left: auto;
  }

  .remove {
    color: var(--danger);
  }

  .help {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .segmented {
    width: fit-content;
  }

  .ideas-toggle {
    margin-top: 8px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-2);
    font: 500 13px/1 var(--sans);
    text-decoration: underline;
    cursor: pointer;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
  }

  .chip {
    min-height: 36px;
    padding: 0 14px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--surface);
    color: var(--ink);
    font: 400 13.5px/1.2 var(--sans);
    text-align: left;
    cursor: pointer;
  }

  .chip:hover {
    border-color: var(--ink);
  }

  .days {
    display: flex;
    gap: 6px;
  }

  .day {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border: 1px solid var(--border);
    border-radius: 50%;
    background: var(--paper);
    color: var(--ink-2);
    font: 500 14px/1 var(--sans);
    cursor: pointer;
  }

  .day.on {
    border-color: var(--ink);
    background: var(--ink);
    color: var(--paper);
  }

  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
</style>
