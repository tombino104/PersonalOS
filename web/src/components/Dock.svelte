<script>
  import Icon from './Icon.svelte';
  import Link from './Link.svelte';
  import { router } from '../lib/router.svelte.js';
  import { t } from '../lib/i18n.svelte.js';

  const items = [
    { href: '/', icon: 'home', label: 'nav.home', match: (path) => path === '/' },
    { href: '/stella', icon: 'star', label: 'nav.stella', match: (path) => path === '/stella' },
    {
      href: '/questionnaire',
      icon: 'pencil',
      label: 'nav.questionnaire',
      main: true,
      match: (path) => path.startsWith('/questionnaire'),
    },
    {
      href: '/more',
      icon: 'more',
      label: 'nav.more',
      match: (path) => ['/more', '/archive', '/settings'].includes(path),
    },
  ];
</script>

<div class="dock-wrap">
  <nav class="dock" aria-label={t('nav.label')}>
    {#each items as item}
      {@const current = item.match(router.path)}
      <Link
        href={item.href}
        class={[item.main && 'main', current && 'current']}
        aria-label={t(item.label)}
        aria-current={current ? 'page' : undefined}
      >
        <Icon name={item.icon} />
        <span>{t(item.label)}</span>
      </Link>
    {/each}
  </nav>
</div>
