<script>
  import Link from '../components/Link.svelte';
  import { navigate, router } from '../lib/router.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
  import { LEGACY, resolveSettings } from '../lib/settingsNav.js';
  import AccountTab from './settings/AccountTab.svelte';
  import ActivitiesTab from './settings/ActivitiesTab.svelte';
  import AppearanceTab from './settings/AppearanceTab.svelte';
  import BackupsTab from './settings/BackupsTab.svelte';
  import CommunityTab from './settings/CommunityTab.svelte';
  import DockTab from './settings/DockTab.svelte';
  import GuideTab from './settings/GuideTab.svelte';
  import MascotTab from './settings/MascotTab.svelte';
  import PluginsTab from './settings/PluginsTab.svelte';

  const TABS = [
    { id: 'activities', label: 'settings.activities', sections: [{ id: 'main', component: ActivitiesTab }] },
    {
      id: 'account',
      label: 'settings.account',
      sections: [
        { id: 'login', label: 'settings.login', component: AccountTab },
        { id: 'mascot', label: 'settings.mascot', component: MascotTab },
        { id: 'backups', label: 'settings.backups', component: BackupsTab },
      ],
    },
    {
      id: 'appearance',
      label: 'settings.appearance',
      sections: [
        { id: 'look', label: 'settings.look', component: AppearanceTab },
        { id: 'dock', label: 'settings.dock', component: DockTab },
      ],
    },
    { id: 'plugins', label: 'settings.plugins', sections: [{ id: 'main', component: PluginsTab }] },
    {
      id: 'help',
      label: 'settings.help',
      sections: [
        { id: 'guide', label: 'settings.guide', component: GuideTab },
        { id: 'community', label: 'settings.community', component: CommunityTab },
      ],
    },
  ];

  const place = $derived(resolveSettings(router.path, TABS, LEGACY));
  const tab = $derived(place?.tab);
  const section = $derived(place?.section);
  const Content = $derived(section?.component);

  $effect(() => {
    if (!place) navigate('/settings/activities', { replace: true });
    else if (place.redirect) navigate(place.redirect, { replace: true });
  });
</script>

<div class="content stagger">
  <Link class="back" href="/more"><svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('nav.more')}</Link>
  <header>
    <div class="eyebrow">{t('nav.settings')}</div>
    <h1 class="title">{t('settings.title')} <em>{t('settings.titleEmphasis')}</em></h1>
    <p class="lede">{t('settings.lede')}</p>
  </header>

  <nav class="tabs" aria-label={t('settings.sections')}>
    {#each TABS as item (item.id)}
      <Link href={`/settings/${item.id}`} class={['tab', tab?.id === item.id && 'on']} aria-current={tab?.id === item.id ? 'page' : undefined}>
        {t(item.label)}
      </Link>
    {/each}
  </nav>

  {#if tab && tab.sections.length > 1}
    <nav class="parts" aria-label={t('settings.parts')}>
      {#each tab.sections as item (item.id)}
        <Link href={`/settings/${tab.id}/${item.id}`} class={['part', section?.id === item.id && 'on']} aria-current={section?.id === item.id ? 'page' : undefined}>
          {t(item.label)}
        </Link>
      {/each}
    </nav>
  {/if}

  {#if Content}
    <div class="tab-content">
      <Content />
    </div>
  {/if}
</div>

<style>
  .tab-content {
    max-width: 760px;
  }

  .parts {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: -4px 0 20px;
  }

  .parts :global(.part) {
    display: inline-flex;
    align-items: center;
    min-height: 40px;
    padding: 0 16px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface);
    color: var(--ink-2);
    font: 500 13px/1 var(--sans);
    text-decoration: none;
  }

  .parts :global(.part:hover) {
    color: var(--ink);
  }

  .parts :global(.part.on) {
    border-color: var(--ink);
    background: var(--ink);
    color: var(--paper);
  }
</style>
