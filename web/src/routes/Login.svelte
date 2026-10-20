<script>
  import { login } from '../lib/session.svelte.js';
  import { ApiError } from '../lib/api.js';
  import { t } from '../lib/i18n.svelte.js';

  let name = $state('');
  let password = $state('');
  let error = $state('');
  let busy = $state(false);

  async function submit(event) {
    event.preventDefault();
    busy = true;
    error = '';
    try {
      await login(name.trim(), password);
    } catch (failure) {
      if (failure instanceof ApiError && failure.code === 'locked_out') {
        error = t('login.locked', { minutes: Math.ceil((failure.retryAfter ?? 900) / 60) });
      } else if (failure instanceof ApiError && failure.code === 'invalid_credentials') {
        error = t('login.invalid');
      } else {
        error = t('error.generic');
      }
    } finally {
      busy = false;
    }
  }
</script>

<main class="page">
  <div class="content narrow login stagger">
    <header>
      <div class="eyebrow">Personal OS</div>
      <h1 class="title">{t('login.title')}</h1>
      <p class="lede">{t('login.lede')}</p>
    </header>

    <form class="card form" onsubmit={submit}>
      <div>
        <label class="label" for="login-name">{t('login.name')}</label>
        <input
          id="login-name"
          class="field"
          type="text"
          name="username"
          autocomplete="username"
          autocapitalize="none"
          autocorrect="off"
          required
          bind:value={name}
        />
      </div>
      <div>
        <label class="label" for="login-password">{t('login.password')}</label>
        <input
          id="login-password"
          class="field"
          type="password"
          name="password"
          autocomplete="current-password"
          required
          bind:value={password}
        />
      </div>
      {#if error}
        <p class="error" role="alert">{error}</p>
      {/if}
      <button class="btn solid" type="submit" disabled={busy}>{t('login.submit')}</button>
    </form>
  </div>
</main>

<style>
  .login {
    justify-content: center;
    padding-bottom: 48px;
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding: 24px;
  }
</style>
