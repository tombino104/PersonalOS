<script>
  import { onMount, untrack } from 'svelte';
  import { ApiError, pluginRequest } from '$core/lib/api.js';
  import { addDays } from '$core/lib/dates.js';
  import { t } from '$core/lib/i18n.svelte.js';
  import { localDay } from './sleep.js';

  let { night = null, nights = [], onsaved, onclose } = $props();

  const today = localDay();
  let dialog;
  let day = $state(untrack(() => night?.day ?? today));
  let lightsOff = $state(untrack(() => night?.lights_off ?? ''));
  let wokeUp = $state(untrack(() => night?.woke_up ?? ''));
  let error = $state('');
  let busy = $state(false);
  let confirmDelete = $state(false);
  const exists = $derived(nights.some((item) => item.day === day));

  onMount(() => {
    dialog.showModal();
  });

  function changeDay() {
    const found = nights.find((item) => item.day === day);
    lightsOff = found?.lights_off ?? '';
    wokeUp = found?.woke_up ?? '';
    confirmDelete = false;
  }

  async function save(event) {
    event.preventDefault();
    if (!day || (!lightsOff && !wokeUp)) {
      error = t('plugin.sleep.invalid');
      return;
    }
    busy = true;
    error = '';
    try {
      await pluginRequest('sleep', 'PUT', `/nights/${day}`, { lights_off: lightsOff || null, woke_up: wokeUp || null });
      onsaved();
    } catch (failure) {
      error = failure instanceof ApiError && failure.status === 422 ? t('plugin.sleep.invalid') : t('error.generic');
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
      await pluginRequest('sleep', 'DELETE', `/nights/${day}`);
      onsaved();
    } catch {
      error = t('error.generic');
      busy = false;
    }
  }
</script>

<dialog bind:this={dialog} class="card" aria-labelledby="night-dialog-title" {onclose}>
  <form onsubmit={save}>
    <h2 id="night-dialog-title">{night ? t('plugin.sleep.editNight') : t('plugin.sleep.logNight')}</h2>

    <div>
      <label class="label" for="night-day">{t('plugin.sleep.morningOf')}</label>
      <input id="night-day" class="field" type="date" required max={addDays(today, 1)} bind:value={day} onchange={changeDay} />
      <p class="muted help">{t('plugin.sleep.morningOfHint')}</p>
    </div>

    <div class="times">
      <div>
        <label class="label" for="night-off">{t('plugin.sleep.lightsOff')}</label>
        <input id="night-off" class="field" type="time" bind:value={lightsOff} />
      </div>
      <div>
        <label class="label" for="night-up">{t('plugin.sleep.wokeUp')}</label>
        <input id="night-up" class="field" type="time" bind:value={wokeUp} />
      </div>
    </div>
    <p class="muted help hint">{t('plugin.sleep.timesHint')}</p>

    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}

    <div class="actions">
      <button class="btn solid" type="submit" disabled={busy}>{t('common.save')}</button>
      <button class="btn" type="button" onclick={() => dialog.close()}>{t('common.cancel')}</button>
      {#if exists}
        <button class="btn remove" type="button" disabled={busy} onclick={remove}>
          {confirmDelete ? t('plugin.sleep.deleteSure') : t('plugin.sleep.delete')}
        </button>
      {/if}
    </div>
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

  .times {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .help {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .hint {
    margin: -8px 0 0;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .remove {
    margin-left: auto;
    color: var(--danger);
  }
</style>
