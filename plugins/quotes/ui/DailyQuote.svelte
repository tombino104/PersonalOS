<script>
  import { i18n, t } from '$core/lib/i18n.svelte.js';
  import { QUOTES, localDay, quoteFor } from './quotes.js';

  const quote = $derived(QUOTES[quoteFor(localDay())]);
  const text = $derived(i18n.lang === 'it' ? quote[2] : quote[1]);
</script>

<figure>
  <figcaption class="eyebrow">{t('plugin.quotes.title')}</figcaption>
  <blockquote>«{text}»</blockquote>
  <p class="author">{quote[0]}</p>
</figure>

<style>
  figure {
    margin: 0;
    padding: 0;
  }

  blockquote {
    margin: 12px 0 8px;
    font: italic 400 22px/1.35 var(--serif);
  }

  .author {
    margin: 0;
    font: 400 13px/1.4 var(--sans);
    color: var(--ink-3);
  }
</style>
