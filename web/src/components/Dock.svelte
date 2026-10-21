<script>
  import Icon from './Icon.svelte';
  import Link from './Link.svelte';
  import { router } from '../lib/router.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
  import { dockLayout } from '../lib/dock.svelte.js';

  const items = $derived(dockLayout().inDock);
</script>

<div class="dock-wrap">
  <nav class="dock" aria-label={t('nav.label')}>
    {#each items as item (item.key)}
      {@const current = item.match(router.path)}
      {@const label = item.text ?? t(item.labelKey)}
      <Link
        href={item.href}
        class={[item.main && 'main', current && 'current']}
        aria-label={label}
        aria-current={current ? 'page' : undefined}
      >
        <Icon name={item.icon} />
        <span>{label}</span>
      </Link>
    {/each}
  </nav>
</div>
