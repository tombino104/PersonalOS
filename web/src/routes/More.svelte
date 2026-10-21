<script>
  import { onMount } from 'svelte';
  import Avatar from '../components/Avatar.svelte';
  import Icon from '../components/Icon.svelte';
  import Link from '../components/Link.svelte';
  import { api } from '../lib/api.js';
  import { addDays, formatDate } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { displayName } from '../lib/profile.svelte.js';
  import { dockLayout } from '../lib/dock.svelte.js';

  const hidden = $derived(dockLayout().outOfDock);
  const hiddenCore = $derived(hidden.filter((item) => !item.text));
  const pluginEntries = $derived(hidden.filter((item) => item.text));
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
    <Avatar />
    <div>
      <div class="name">{displayName()}</div>
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
      {#each hiddenCore as item (item.key)}
        <Link class="entry" href={item.href}>
          <span class="ico"><Icon name={item.icon} /></span>
          <span class="text">
            <span class="entry-title">{t(item.labelKey)}</span>
          </span>
          <span class="go"><Icon name="forward" small /></span>
        </Link>
      {/each}
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

  {#if pluginEntries.length > 0}
    <section aria-label={t('more.fromPlugins')}>
      <h2 class="eyebrow heading">{t('more.fromPlugins')}</h2>
      <div class="entries">
        {#each pluginEntries as entry (entry.key)}
          <Link class="entry" href={entry.href}>
            <span class="ico"><Icon name={entry.icon} /></span>
            <span class="text">
              <span class="entry-title">{entry.text}</span>
            </span>
            <span class="go"><Icon name="forward" small /></span>
          </Link>
        {/each}
      </div>
      <p class="muted plugin-note">{t('more.pluginsNote')}</p>
    </section>
  {/if}

  <p class="muted source">
    <a href="https://github.com/tombino104/PersonalOS" target="_blank" rel="noopener noreferrer">{t('more.source')}</a>
  </p>
</div>

<style>
  .plugin-note {
    margin: 16px 2px 0;
    font: 400 13px/1.5 var(--sans);
  }

  .profile {
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 20px 24px;
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

  .source {
    margin: 0;
    font: 400 13px/1.5 var(--sans);
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
