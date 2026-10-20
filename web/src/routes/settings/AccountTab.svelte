<script>
  import { api, ApiError } from '../../lib/api.js';
  import { t } from '../../lib/i18n.svelte.js';
  import { logout } from '../../lib/session.svelte.js';

  let currentPassword = $state('');
  let newPassword = $state('');
  let repeatPassword = $state('');
  let message = $state('');
  let failed = $state(false);
  let busy = $state(false);

  async function changePassword(event) {
    event.preventDefault();
    message = '';
    failed = true;
    if (newPassword !== repeatPassword) {
      message = t('account.mismatch');
      return;
    }
    busy = true;
    try {
      await api.changePassword(currentPassword, newPassword);
      failed = false;
      message = t('account.changed');
      currentPassword = newPassword = repeatPassword = '';
    } catch (failure) {
      if (failure instanceof ApiError && failure.code === 'invalid_credentials') message = t('account.wrongCurrent');
      else if (failure instanceof ApiError && failure.code === 'weak_password') message = t('account.weak');
      else if (failure instanceof ApiError && failure.code === 'locked_out') message = t('login.locked', { minutes: Math.ceil((failure.retryAfter ?? 900) / 60) });
      else message = t('error.generic');
    } finally {
      busy = false;
    }
  }
</script>

<section class="card panel" aria-label={t('settings.account')}>
  <h2>{t('settings.account')}</h2>
  <p class="desc">{t('settings.accountLede')}</p>
  <form class="password" onsubmit={changePassword}>
    <div>
      <label class="label" for="current-password">{t('account.current')}</label>
      <input id="current-password" class="field" type="password" autocomplete="current-password" required bind:value={currentPassword} />
    </div>
    <div>
      <label class="label" for="new-password">{t('account.new')}</label>
      <input id="new-password" class="field" type="password" autocomplete="new-password" minlength="10" required bind:value={newPassword} />
    </div>
    <div>
      <label class="label" for="repeat-password">{t('account.repeat')}</label>
      <input id="repeat-password" class="field" type="password" autocomplete="new-password" required bind:value={repeatPassword} />
    </div>
    {#if message}
      <p class={failed ? 'error' : 'ok'} role="status">{message}</p>
    {/if}
    <div class="actions">
      <button class="btn solid" type="submit" disabled={busy}>{t('account.change')}</button>
      <button class="btn" type="button" onclick={logout}>{t('account.logout')}</button>
    </div>
  </form>
</section>

<style>
  .panel {
    padding: 24px;
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

  .password {
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-width: 380px;
  }

  .ok {
    margin: 0;
    font: 500 14px/1.4 var(--sans);
    color: var(--ok);
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
</style>
