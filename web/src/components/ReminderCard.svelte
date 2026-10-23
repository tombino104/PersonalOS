<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';
  import { t } from '../lib/i18n.svelte.js';
  import { currentSubscription, disableDevice, enableDevice, supported, syncText } from '../lib/reminder.js';

  const available = supported();
  let on = $state(false);
  let at = $state('21:00');
  let busy = $state(false);
  let message = $state('');
  let failure = $state('');

  onMount(async () => {
    try {
      at = (await api.settings()).reminder_time;
    } catch {
    }
    if (!available) return;
    on = Boolean(await currentSubscription());
    if (on) syncText();
  });

  async function toggle() {
    busy = true;
    failure = '';
    message = '';
    try {
      if (on) {
        await disableDevice();
        on = false;
      } else if ((await enableDevice()) === 'granted') {
        on = true;
      } else {
        failure = t('reminder.denied');
      }
    } catch {
      failure = t('error.generic');
    }
    busy = false;
  }

  async function saveTime() {
    failure = '';
    try {
      await api.updateSettings({ reminder_time: at || '21:00' });
    } catch {
      failure = t('error.generic');
    }
  }

  async function test() {
    failure = '';
    message = '';
    try {
      await api.pushTest();
      message = t('reminder.testSent');
    } catch {
      failure = t('error.generic');
    }
  }
</script>

<section class="card panel" aria-label={t('reminder.title')}>
  <h2>{t('reminder.title')}</h2>
  <p class="desc">{t('reminder.lede')}</p>
  {#if available}
    <label class="check">
      <input type="checkbox" checked={on} disabled={busy} onchange={toggle} />
      <span>{t('reminder.enable')}</span>
    </label>
    <div class="when-field">
      <label class="label" for="reminder-time">{t('reminder.time')}</label>
      <input id="reminder-time" class="field" type="time" bind:value={at} onchange={saveTime} />
    </div>
    {#if on}
      <button class="btn test" type="button" onclick={test}>{t('reminder.test')}</button>
    {/if}
    <p class="muted note">{t('reminder.note')}</p>
  {:else}
    <p class="muted note">{t('reminder.unsupported')}</p>
  {/if}
  {#if message}
    <p class="muted note" role="status">{message}</p>
  {/if}
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

  .test {
    margin-top: 16px;
  }

  .note {
    margin: 12px 0 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
