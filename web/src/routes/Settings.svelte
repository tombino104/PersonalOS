<script>
  import Link from '../components/Link.svelte';
  import { navigate, router } from '../lib/router.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
  import AccountTab from './settings/AccountTab.svelte';
  import ActivitiesTab from './settings/ActivitiesTab.svelte';
  import AppearanceTab from './settings/AppearanceTab.svelte';
  import PluginsTab from './settings/PluginsTab.svelte';

  const TABS = [
    { id: 'activities', label: 'settings.activities', component: ActivitiesTab },
    { id: 'account', label: 'settings.account', component: AccountTab },
    { id: 'appearance', label: 'settings.appearance', component: AppearanceTab },
    { id: 'plugins', label: 'settings.plugins', component: PluginsTab },
  ];

  const tab = $derived(TABS.find((item) => item.id === router.path.split('/')[2]));
  const Content = $derived(tab?.component);

  $effect(() => {
    if (!tab) navigate('/settings/activities', { replace: true });
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
</style>
