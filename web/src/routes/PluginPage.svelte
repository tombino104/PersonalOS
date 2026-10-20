<script>
  import Link from '../components/Link.svelte';
  import { router } from '../lib/router.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
  import { pageComponent, plugins } from '../lib/plugins.svelte.js';

  const parts = $derived(router.path.split('/'));
  const Component = $derived(plugins.loaded ? pageComponent(parts[2], parts[3]) : null);
</script>

<div class="content stagger">
  {#if Component}
    <Component />
  {:else if plugins.loaded}
    <header>
      <div class="eyebrow">{t('nav.more')}</div>
      <h1 class="title">{t('plugins.pageMissing')}</h1>
      <p class="lede">{t('plugins.pageMissingNote')}</p>
    </header>
    <Link class="btn" href="/settings/plugins">{t('plugins.manage')}</Link>
  {:else}
    <p class="lede" aria-live="polite">{t('common.loading')}</p>
  {/if}
</div>
