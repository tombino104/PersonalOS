<script>
  import { setup } from '../lib/session.svelte.js';
  import { ApiError } from '../lib/api.js';
  import { t } from '../lib/i18n.svelte.js';

  let code = $state('');
  let name = $state('');
  let password = $state('');
  let repeat = $state('');
  let error = $state('');
  let busy = $state(false);

  async function submit(event) {
    event.preventDefault();
    error = '';
    if (password !== repeat) {
      error = t('setup.mismatch');
      return;
    }
    busy = true;
    try {
      await setup(code.trim(), name.trim(), password);
    } catch (failure) {
      if (failure instanceof ApiError && failure.code === 'invalid_setup_code') error = t('setup.invalidCode');
      else if (failure instanceof ApiError && failure.code === 'weak_password') error = t('setup.weak');
      else if (failure instanceof ApiError && failure.code === 'locked_out') error = t('login.locked', { minutes: Math.ceil((failure.retryAfter ?? 900) / 60) });
      else error = t('error.generic');
    } finally {
      busy = false;
    }
  }
</script>

<main class="page bare">
  <div class="content narrow setup stagger">
    <header>
      <div class="eyebrow">Personal OS</div>
      <h1 class="title">{t('setup.title')}</h1>
      <p class="lede">{t('setup.lede')}</p>
    </header>

    <form class="card form" onsubmit={submit}>
      <div>
        <label class="label" for="setup-code">{t('setup.code')}</label>
        <input
          id="setup-code"
          class="field code"
          type="text"
          autocomplete="off"
          autocapitalize="characters"
          autocorrect="off"
          spellcheck="false"
          required
          bind:value={code}
        />
        <p class="muted help">{t('setup.codeHelp')}</p>
      </div>
      <div>
        <label class="label" for="setup-name">{t('setup.name')}</label>
        <input
          id="setup-name"
          class="field"
          type="text"
          name="username"
          autocomplete="username"
          autocapitalize="words"
          autocorrect="off"
          required
          bind:value={name}
        />
      </div>
      <div>
        <label class="label" for="setup-password">{t('setup.password')}</label>
        <input
          id="setup-password"
          class="field"
          type="password"
          name="password"
          autocomplete="new-password"
          minlength="10"
          required
          bind:value={password}
        />
      </div>
      <div>
        <label class="label" for="setup-repeat">{t('setup.repeat')}</label>
        <input
          id="setup-repeat"
          class="field"
          type="password"
          autocomplete="new-password"
          required
          bind:value={repeat}
        />
      </div>
      {#if error}
        <p class="error" role="alert">{error}</p>
      {/if}
      <button class="btn solid" type="submit" disabled={busy}>{t('setup.submit')}</button>
    </form>
  </div>
</main>

<style>
  .setup {
    justify-content: center;
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 20px;
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
</style>
