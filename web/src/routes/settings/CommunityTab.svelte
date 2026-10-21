<script>
  import { onMount } from 'svelte';
  import { t } from '../../lib/i18n.svelte.js';

  const REPO = 'https://github.com/tombino104/PersonalOS';
  const LINKS = [
    { id: 'idea', href: `${REPO}/discussions` },
    { id: 'bug', href: `${REPO}/issues/new/choose` },
    { id: 'contribute', href: `${REPO}/blob/main/CONTRIBUTING.md` },
    { id: 'source', href: REPO },
    { id: 'releases', href: `${REPO}/releases` },
    { id: 'security', href: `${REPO}/security/policy` },
    { id: 'license', href: `${REPO}/blob/main/LICENSE` },
  ];

  let version = $state('');

  onMount(() => {
    fetch('/health')
      .then((response) => response.json())
      .then((data) => {
        version = data.version ?? '';
      })
      .catch(() => {});
  });
</script>

<section class="card panel" aria-label={t('settings.community')}>
  <h2>{t('settings.community')}</h2>
  <p class="desc">{t('community.lede')}</p>
  {#each LINKS as link (link.id)}
    <a class="item" href={link.href} target="_blank" rel="noopener noreferrer">
      <span class="text">
        <span class="title">{t(`community.${link.id}.title`)}</span>
        <span class="note">{t(`community.${link.id}.note`)}</span>
      </span>
      <svg class="icon small go" viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 6.5 15 12l-5.5 5.5" /></svg>
    </a>
  {/each}
  <p class="muted privacy">{t('community.privacy')}</p>
  {#if version}
    <p class="muted version">{t('community.version', { version })}</p>
  {/if}
</section>

<style>
  .panel {
    padding: 24px;
  }

  h2 {
    margin: 0;
    font: 400 26px/1.2 var(--serif);
  }

  .desc {
    margin: 8px 0 16px;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .item {
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 64px;
    padding: 12px 0;
    border-top: 1px solid var(--line);
    color: inherit;
    text-decoration: none;
  }

  .text {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    gap: 4px;
  }

  .title {
    font: 500 20px/1.3 var(--serif);
  }

  .note {
    font: 400 14px/1.4 var(--sans);
    color: var(--ink-2);
  }

  .go {
    flex: none;
    color: var(--ink-3);
  }

  .privacy {
    margin: 16px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .version {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
