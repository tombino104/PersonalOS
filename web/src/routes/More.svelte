<script>
  import { onMount } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import Link from '../components/Link.svelte';
  import { api } from '../lib/api.js';
  import { addDays, formatDate } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { session } from '../lib/session.svelte.js';

  let recorded = $state(0);
  let since = $state('');

  onMount(async () => {
    try {
      const today = (await api.today()).day;
      const result = await api.listReports(addDays(today, -365), today);
      const completed = result.reports.filter((report) => report.completed).map((report) => report.day);
      recorded = completed.length;
      since = completed.length ? completed.sort()[0] : '';
    } catch {
      recorded = 0;
    }
  });
</script>

<div class="content stagger">
  <header>
    <div class="eyebrow">{t('nav.more')}</div>
    <h1 class="title">{t('more.title')} <em>{t('more.titleEmphasis')}</em></h1>
    <p class="lede">{t('more.lede')}</p>
  </header>

  <section class="card profile" aria-label={t('more.profile')}>
    <span class="avatar" aria-hidden="true">{session.name.charAt(0).toUpperCase()}</span>
    <div>
      <div class="name">{session.name}</div>
      <div class="since">
        {#if recorded > 0}
          {t('more.since', { date: formatDate(since, locale(), { day: 'numeric', month: 'long' }), count: recorded })}
        {:else}
          {t('more.noDays')}
        {/if}
      </div>
    </div>
  </section>

  <section aria-label={t('more.diary')}>
    <h2 class="eyebrow heading">{t('more.diary')}</h2>
    <div class="entries">
      <Link class="entry" href="/archive">
        <span class="ico"><Icon name="archive" /></span>
        <span class="text">
          <span class="entry-title">{t('nav.archive')}</span>
          <span class="entry-note">{t('more.archiveNote')}</span>
        </span>
        <span class="go"><Icon name="forward" small /></span>
      </Link>
      <Link class="entry" href="/settings">
        <span class="ico"><Icon name="sliders" /></span>
        <span class="text">
          <span class="entry-title">{t('nav.settings')}</span>
          <span class="entry-note">{t('more.settingsNote')}</span>
        </span>
        <span class="go"><Icon name="forward" small /></span>
      </Link>
    </div>
  </section>
</div>

<style>
  .profile {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 20px 24px;
  }

  .avatar {
    display: inline-flex;
    flex: none;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--ink);
    color: var(--paper);
    font: 500 28px/1 var(--serif);
  }

  .name {
    font: 500 22px/1.2 var(--serif);
  }

  .since {
    margin-top: 4px;
    font: 400 14px/1.4 var(--sans);
    color: var(--ink-2);
  }

  .heading {
    margin: 0 0 12px;
  }

  .entries {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
    gap: 16px;
  }

  .entries :global(.entry) {
    display: flex;
    align-items: center;
    gap: 20px;
    min-height: 88px;
    padding: 20px 24px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    color: var(--ink);
    text-decoration: none;
    transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .entries :global(.entry:hover) {
    transform: translateY(-2px);
  }

  .ico {
    display: flex;
    flex: none;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: var(--paper-2);
  }

  .text {
    flex: 1 1 auto;
  }

  .entry-title {
    display: block;
    font: 500 22px/1.2 var(--serif);
  }

  .entry-note {
    display: block;
    margin-top: 4px;
    font: 400 14px/1.4 var(--sans);
    color: var(--ink-2);
  }

  .go {
    color: var(--ink-3);
  }

  @media (prefers-reduced-motion: reduce) {
    .entries :global(.entry) {
      transition: none;
    }

    .entries :global(.entry:hover) {
      transform: none;
    }
  }
</style>
