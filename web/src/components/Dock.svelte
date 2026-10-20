<script>
  import Icon from './Icon.svelte';
  import Link from './Link.svelte';
  import { router } from '../lib/router.svelte.js';
  import { t } from '../lib/i18n.svelte.js';
  import { dockEntries } from '../lib/plugins.svelte.js';

  const home = { href: '/', icon: 'home', label: 'nav.home', match: (path) => path === '/' };
  const stella = { href: '/stella', icon: 'star', label: 'nav.stella', match: (path) => path === '/stella' };
  const questionnaire = {
    href: '/questionnaire',
    icon: 'pencil',
    label: 'nav.questionnaire',
    main: true,
    match: (path) => path.startsWith('/questionnaire'),
  };
  const more = {
    href: '/more',
    icon: 'more',
    label: 'nav.more',
    match: (path) => ['/more', '/archive'].includes(path) || path.startsWith('/settings'),
  };

  const items = $derived([
    home,
    stella,
    questionnaire,
    ...dockEntries().map((entry) => ({
      href: entry.href,
      icon: entry.icon,
      text: entry.label,
      match: (path) => path.startsWith(`/p/${entry.pluginId}/`),
    })),
    more,
  ]);
</script>

<div class="dock-wrap">
  <nav class="dock" aria-label={t('nav.label')}>
    {#each items as item (item.href)}
      {@const current = item.match(router.path)}
      {@const label = item.text ?? t(item.label)}
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
