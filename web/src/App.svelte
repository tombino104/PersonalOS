<script>
  import { onMount } from 'svelte';
  import Grain from './components/Grain.svelte';
  import Dock from './components/Dock.svelte';
  import Login from './routes/Login.svelte';
  import Onboarding from './routes/Onboarding.svelte';
  import Reset from './routes/Reset.svelte';
  import Home from './routes/Home.svelte';
  import Stella from './routes/Stella.svelte';
  import Questionnaire from './routes/Questionnaire.svelte';
  import Completion from './routes/Completion.svelte';
  import Archive from './routes/Archive.svelte';
  import Review from './routes/Review.svelte';
  import Recap from './routes/Recap.svelte';
  import More from './routes/More.svelte';
  import Settings from './routes/Settings.svelte';
  import PluginPage from './routes/PluginPage.svelte';
  import { router, navigate } from './lib/router.svelte.js';
  import { session, bootstrap } from './lib/session.svelte.js';
  import { loadPlugins } from './lib/plugins.svelte.js';
  import { applyTheme } from './lib/theme.svelte.js';
  import { applyLanguage } from './lib/i18n.svelte.js';
  import { syncAppearance } from './lib/appearance.js';
  import { loadProfile } from './lib/profile.svelte.js';
  import { loadDock } from './lib/dock.svelte.js';

  const pages = {
    '/': Home,
    '/stella': Stella,
    '/questionnaire': Questionnaire,
    '/questionnaire/done': Completion,
    '/archive': Archive,
    '/review': Review,
    '/recap': Recap,
    '/more': More,
  };

  function resolve(path) {
    if (path === '/settings' || path.startsWith('/settings/')) return Settings;
    if (path.startsWith('/p/')) return PluginPage;
    return pages[path];
  }

  const Page = $derived(resolve(router.path));

  $effect(() => {
    if (session.status === 'authenticated' && !resolve(router.path)) navigate('/', { replace: true });
  });

  $effect(() => {
    if (session.status === 'authenticated') {
      loadPlugins();
      syncAppearance();
      loadProfile();
      loadDock();
    }
  });

  onMount(() => {
    applyTheme();
    applyLanguage();
    bootstrap();
  });
</script>

<Grain />

{#if session.status === 'authenticated'}
  <div class="page">
    {#if Page}
      {#key router.path + router.query.toString()}
        <Page />
      {/key}
    {/if}
    <Dock />
  </div>
{:else if session.status === 'anonymous'}
  {#if router.path === '/reset'}
    <Reset />
  {:else}
    <Login />
  {/if}
{:else if session.status === 'setup'}
  <Onboarding />
{/if}
