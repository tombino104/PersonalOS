<script>
  import ActivityDialog from '../components/ActivityDialog.svelte';
  import Link from '../components/Link.svelte';
  import { api, ApiError } from '../lib/api.js';
  import { AREAS } from '../lib/charts.js';
  import { i18n, setLanguage, t } from '../lib/i18n.svelte.js';
  import { logout } from '../lib/session.svelte.js';
  import { setTheme, theme } from '../lib/theme.svelte.js';

  let activities = $state([]);
  let warnings = $state([]);
  let showArchived = $state(false);
  let status = $state('loading');
  let editing = $state(null);
  let dialogOpen = $state(false);
  let defaultArea = $state('physical');

  let currentPassword = $state('');
  let newPassword = $state('');
  let repeatPassword = $state('');
  let passwordMessage = $state('');
  let passwordFailed = $state(false);
  let passwordBusy = $state(false);

  async function load() {
    try {
      const result = await api.activities(showArchived);
      activities = result.activities;
      warnings = result.warnings;
      status = 'ready';
    } catch {
      status = 'error';
    }
  }

  $effect(() => {
    showArchived;
    load();
  });

  const byArea = $derived(
    AREAS.map((area) => ({
      area,
      items: activities.filter((activity) => activity.area === area),
      tooMany: warnings.some((warning) => warning.area === area),
    })),
  );

  function open(activity, area) {
    editing = activity;
    defaultArea = area;
    dialogOpen = true;
  }

  function saved() {
    dialogOpen = false;
    load();
  }

  async function changePassword(event) {
    event.preventDefault();
    passwordMessage = '';
    passwordFailed = true;
    if (newPassword !== repeatPassword) {
      passwordMessage = t('account.mismatch');
      return;
    }
    passwordBusy = true;
    try {
      await api.changePassword(currentPassword, newPassword);
      passwordFailed = false;
      passwordMessage = t('account.changed');
      currentPassword = newPassword = repeatPassword = '';
    } catch (failure) {
      if (failure instanceof ApiError && failure.code === 'invalid_credentials') passwordMessage = t('account.wrongCurrent');
      else if (failure instanceof ApiError && failure.code === 'weak_password') passwordMessage = t('account.weak');
      else if (failure instanceof ApiError && failure.code === 'locked_out') passwordMessage = t('login.locked', { minutes: Math.ceil((failure.retryAfter ?? 900) / 60) });
      else passwordMessage = t('error.generic');
    } finally {
      passwordBusy = false;
    }
  }

  const themes = [
    ['light', 'settings.themeLight'],
    ['dark', 'settings.themeDark'],
    ['auto', 'settings.themeAuto'],
  ];
  const languages = [
    ['auto', 'settings.languageAuto'],
    ['en', 'settings.languageEn'],
    ['it', 'settings.languageIt'],
  ];
</script>

<div class="content stagger">
  <Link class="back" href="/more"><svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('nav.more')}</Link>
  <header>
    <div class="eyebrow">{t('nav.settings')}</div>
    <h1 class="title">{t('settings.title')} <em>{t('settings.titleEmphasis')}</em></h1>
    <p class="lede">{t('settings.lede')}</p>
  </header>

  <div class="layout">
    <nav class="card index" aria-label={t('settings.sections')}>
      <a href="#activities">{t('settings.activities')}</a>
      <a href="#account">{t('settings.account')}</a>
      <a href="#appearance">{t('settings.appearance')}</a>
    </nav>

    <div class="sections">
      <section id="activities" class="card" aria-label={t('settings.activities')}>
        <h2>{t('settings.activities')}</h2>
        <p class="desc">{t('settings.activitiesLede')}</p>
        <div class="item archived-row">
          <span class="grow">{t('settings.showArchived')}</span>
          <button class="toggle" role="switch" aria-label={t('settings.showArchived')} aria-checked={showArchived} onclick={() => (showArchived = !showArchived)}></button>
        </div>
        {#if status === 'error'}
          <p class="error" role="alert">{t('error.generic')}</p>
        {/if}
        {#each byArea as group (group.area)}
          <div class="item top" data-area={group.area}>
            <span class="area"><span class="dot small"></span><span>{t(`area.${group.area}`)}</span></span>
            <div class="grow">
              <div class="chips">
                {#each group.items as activity (activity.id)}
                  <button class="chip" class:faded={activity.archived_at} onclick={() => open(activity, group.area)}>
                    {activity.name}<b>{activity.archived_at ? t('settings.archivedTag') : t('settings.weightTag', { weight: activity.weight })}</b>
                  </button>
                {/each}
                <button class="chip dashed" onclick={() => open(null, group.area)}>{t('settings.add')}</button>
              </div>
              {#if group.tooMany}
                <p class="warn">{t('settings.tooMany')}</p>
              {/if}
            </div>
          </div>
        {/each}
      </section>

      <section id="account" class="card" aria-label={t('settings.account')}>
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
          {#if passwordMessage}
            <p class={passwordFailed ? 'error' : 'ok'} role="status">{passwordMessage}</p>
          {/if}
          <div class="actions">
            <button class="btn solid" type="submit" disabled={passwordBusy}>{t('account.change')}</button>
            <button class="btn" type="button" onclick={logout}>{t('account.logout')}</button>
          </div>
        </form>
      </section>

      <section id="appearance" class="card" aria-label={t('settings.appearance')}>
        <h2>{t('settings.appearance')}</h2>
        <p class="desc">{t('settings.appearanceLede')}</p>
        <span class="label" id="theme-label">{t('settings.theme')}</span>
        <div class="segmented fit" role="group" aria-labelledby="theme-label">
          {#each themes as [mode, label]}
            <button class="seg" class:on={theme.mode === mode} aria-pressed={theme.mode === mode} onclick={() => setTheme(mode)}>{t(label)}</button>
          {/each}
        </div>
        <span class="label spaced" id="language-label">{t('settings.language')}</span>
        <div class="segmented fit" role="group" aria-labelledby="language-label">
          {#each languages as [value, label]}
            <button class="seg" class:on={i18n.preference === value} aria-pressed={i18n.preference === value} onclick={() => setLanguage(value)}>{t(label)}</button>
          {/each}
        </div>
      </section>
    </div>
  </div>
</div>

{#if dialogOpen}
  {#key editing?.id ?? `new-${defaultArea}`}
    <ActivityDialog activity={editing} area={defaultArea} onsaved={saved} onclose={() => (dialogOpen = false)} />
  {/key}
{/if}

<style>
  .layout {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 20px;
  }

  .index {
    position: sticky;
    top: 16px;
    flex: 0 0 200px;
    padding: 8px;
  }

  .index a {
    display: flex;
    align-items: center;
    min-height: 44px;
    padding: 0 16px;
    border-radius: 10px;
    color: var(--ink-2);
    text-decoration: none;
    font: 500 14px/1 var(--sans);
  }

  .index a:hover {
    background: var(--paper-2);
    color: var(--ink);
  }

  .sections {
    display: flex;
    flex: 1 1 520px;
    flex-direction: column;
    gap: 16px;
    min-width: 0;
  }

  section {
    padding: 24px;
    scroll-margin-top: 20px;
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

  .grow {
    flex-grow: 1;
    min-width: 0;
  }

  .top {
    align-items: flex-start;
  }

  .area {
    display: flex;
    flex: none;
    align-items: center;
    gap: 8px;
    width: 120px;
    padding-top: 14px;
    font: 500 15px/1 var(--sans);
  }

  .dot.small {
    width: 9px;
    height: 9px;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .warn {
    margin: 12px 0 0;
    font: 400 13px/1.5 var(--sans);
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

  .fit {
    width: fit-content;
  }

  .spaced {
    margin-top: 20px;
  }

  @media (max-width: 560px) {
    .index {
      position: static;
      flex: 1 1 100%;
    }

    .area {
      width: 96px;
    }
  }
</style>
