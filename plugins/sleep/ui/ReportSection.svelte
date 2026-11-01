<script>
  import { onMount } from 'svelte';
  import { pluginRequest } from '$core/lib/api.js';
  import { t } from '$core/lib/i18n.svelte.js';
  import { hoursText } from './sleep.js';

  let { day } = $props();

  let night = $state(null);

  onMount(async () => {
    try {
      const found = await pluginRequest('sleep', 'GET', `/nights/${day}`);
      night = found.lights_off || found.woke_up ? found : null;
    } catch {
      night = null;
    }
  });
</script>

{#if night}
  <div class="section">
    <div class="eyebrow label-row">{t('plugin.sleep.reportTitle')}</div>
    {#if night.lights_off && night.woke_up}
      <p class="text">
        {t('plugin.sleep.reportRange', { from: night.lights_off, to: night.woke_up })}
        <span class="muted">· {hoursText(night.minutes)}</span>
      </p>
    {:else if night.lights_off}
      <p class="text">{t('plugin.sleep.onlyLightsOff', { time: night.lights_off })}</p>
    {:else}
      <p class="text">{t('plugin.sleep.onlyWokeUp', { time: night.woke_up })}</p>
    {/if}
  </div>
{/if}

<style>
  .label-row {
    margin-bottom: 8px;
  }

  .text {
    margin: 0;
    font: 400 18px/1.45 var(--serif);
  }

  .muted {
    font: 400 14px/1.4 var(--sans);
  }
</style>
