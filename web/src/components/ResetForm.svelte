<script>
  import { api, ApiError } from '../lib/api.js';
  import { forgetLocalAppearance } from '../lib/appearance.js';
  import { t } from '../lib/i18n.svelte.js';

  let { onreset, plain = false } = $props();

  let code = $state(__DEMO__ ? 'DEMO' : '');
  let understood = $state(false);
  let error = $state('');
  let busy = $state(false);

  async function submit(event) {
    event.preventDefault();
    error = '';
    busy = true;
    try {
      await api.reset(code.trim());
      forgetLocalAppearance();
      onreset();
    } catch (failure) {
      if (failure instanceof ApiError && failure.code === 'invalid_setup_code') error = t('setup.invalidCode');
      else if (failure instanceof ApiError && failure.code === 'locked_out') error = t('login.locked', { minutes: Math.ceil((failure.retryAfter ?? 900) / 60) });
      else error = t('error.generic');
      busy = false;
    }
  }
</script>

<form class="form" class:card={!plain} class:plain onsubmit={submit}>
  <div>
    <label class="label" for="reset-code">{t('setup.code')}</label>
    <input
      id="reset-code"
      class="field code"
      type="text"
      autocomplete="off"
      autocapitalize="characters"
      autocorrect="off"
      spellcheck="false"
      required
      bind:value={code}
    />
    <p class="muted help">{__DEMO__ ? t('reset.demoHelp') : t('reset.codeHelp')}</p>
  </div>
  <label class="confirm">
    <input type="checkbox" required bind:checked={understood} />
    <span>{t('reset.confirm')}</span>
  </label>
  {#if error}
    <p class="error" role="alert">{error}</p>
  {/if}
  <button class="btn solid" type="submit" disabled={busy || !understood}>{t('reset.submit')}</button>
</form>

<style>
  .form {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .form:not(.plain) {
    padding: 24px;
  }

  .code {
    font-family: ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .help {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .confirm {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .confirm input {
    flex: none;
    width: 20px;
    height: 20px;
    margin: 2px 0 0;
    accent-color: var(--ink);
  }
</style>
