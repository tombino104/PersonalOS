<script>
  import { onMount } from 'svelte';
  import Grain from './components/Grain.svelte';
  import Dock from './components/Dock.svelte';
  import Login from './routes/Login.svelte';
  import Setup from './routes/Setup.svelte';
  import Home from './routes/Home.svelte';
  import Stella from './routes/Stella.svelte';
  import Questionnaire from './routes/Questionnaire.svelte';
  import Completion from './routes/Completion.svelte';
  import Archive from './routes/Archive.svelte';
  import More from './routes/More.svelte';
  import Settings from './routes/Settings.svelte';
  import { router, navigate } from './lib/router.svelte.js';
  import { session, bootstrap } from './lib/session.svelte.js';
  import { applyTheme } from './lib/theme.svelte.js';
  import { applyLanguage } from './lib/i18n.svelte.js';

  const pages = {
    '/': Home,
    '/stella': Stella,
    '/questionnaire': Questionnaire,
    '/questionnaire/done': Completion,
    '/archive': Archive,
    '/more': More,
    '/settings': Settings,
  };

  const Page = $derived(pages[router.path]);

  $effect(() => {
    if (session.status === 'authenticated' && !pages[router.path]) navigate('/', { replace: true });
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
  <Login />
{:else if session.status === 'setup'}
  <Setup />
{/if}
