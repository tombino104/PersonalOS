<script>
  import { onMount } from 'svelte';
  import { pluginRequest } from '$core/lib/api.js';
  import { t } from '$core/lib/i18n.svelte.js';

  let { day, editable } = $props();

  let text = $state('');
  let saved = $state(false);
  let failed = $state(false);
  let timer = null;

  onMount(async () => {
    try {
      const result = await pluginRequest('example', 'GET', `/notes/${day}`);
      text = result.text ?? '';
    } catch {
      failed = true;
    }
  });

  async function save() {
    try {
      await pluginRequest('example', 'PUT', `/notes/${day}`, { text: text.trim() === '' ? null : text });
      saved = true;
      failed = false;
    } catch {
      failed = true;
    }
  }

  function schedule() {
    saved = false;
    if (timer) clearTimeout(timer);
    timer = setTimeout(save, 700);
  }
</script>

<h2>{t('plugin.example.title')}</h2>
<label class="label" for="example-note">
  {t('plugin.example.label')}{#if saved} · {t('plugin.example.saved')}{/if}
</label>
<textarea
  id="example-note"
  class="field"
  rows="2"
  maxlength="300"
  placeholder={t('plugin.example.placeholder')}
  disabled={!editable}
  bind:value={text}
  oninput={schedule}
></textarea>
{#if failed}
  <p class="error" role="alert">{t('error.generic')}</p>
{/if}

<style>
  h2 {
    margin: 0 0 12px;
    font: 500 20px/1 var(--serif);
  }
</style>
