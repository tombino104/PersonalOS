<script>
  import Link from '../components/Link.svelte';
  import { reset } from '../lib/session.svelte.js';
  import { navigate } from '../lib/router.svelte.js';
  import { ApiError } from '../lib/api.js';
  import { t } from '../lib/i18n.svelte.js';

  let code = $state('');
  let name = $state('');
  let password = $state('');
  let repeat = $state('');
  let understood = $state(false);
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
      await reset(code.trim(), name.trim(), password);
      navigate('/', { replace: true });
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
  <div class="content narrow reset stagger">
    <header>
      <div class="eyebrow">Personal OS</div>
      <h1 class="title">{t('reset.title')}</h1>
      <p class="lede">{t('reset.lede')}</p>
    </header>

    <form class="card form" onsubmit={submit}>
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
        <p class="muted help">{t('reset.codeHelp')}</p>
      </div>
      <div>
        <label class="label" for="reset-name">{t('setup.name')}</label>
        <input
          id="reset-name"
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
        <label class="label" for="reset-password">{t('setup.password')}</label>
        <input
          id="reset-password"
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
        <label class="label" for="reset-repeat">{t('setup.repeat')}</label>
        <input
          id="reset-repeat"
          class="field"
          type="password"
          autocomplete="new-password"
          required
          bind:value={repeat}
        />
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

    <Link class="back" href="/">
      <svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('reset.back')}
    </Link>
  </div>
</main>

<style>
  .reset {
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
