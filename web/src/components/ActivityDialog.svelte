<script>
  import { onMount, untrack } from 'svelte';
  import { api, ApiError } from '../lib/api.js';
  import { AREAS } from '../lib/charts.js';
  import { t } from '../lib/i18n.svelte.js';

  let { activity = null, area = 'physical', onsaved, onclose } = $props();

  let dialog;
  let name = $state(untrack(() => activity?.name ?? ''));
  let chosenArea = $state(untrack(() => activity?.area ?? area));
  let weight = $state(untrack(() => activity?.weight ?? 2));
  let error = $state('');
  let busy = $state(false);

  onMount(() => {
    dialog.showModal();
  });

  async function save(event) {
    event.preventDefault();
    busy = true;
    error = '';
    try {
      if (activity) {
        await api.updateActivity(activity.id, { name: name.trim(), area: chosenArea, weight });
      } else {
        await api.createActivity({ name: name.trim(), area: chosenArea, weight });
      }
      onsaved();
    } catch (failure) {
      error = failure instanceof ApiError && failure.status === 422 ? t('activity.invalid') : t('error.generic');
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
    </div>
    {#if activity && !activity.archived_at}
      <p class="muted help">{t('activity.archiveHelp')}</p>
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

  .help {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .segmented {
    width: fit-content;
  }
</style>
