<script>
  import { t } from '../../lib/i18n.svelte.js';

  const SECTIONS = ['basics', 'evening', 'score', 'activities', 'home', 'calendar', 'plugins', 'mascot', 'backups', 'account', 'data'];
  let open = $state('basics');

  const paragraphs = (id) => t(`guide.${id}.body`).split('\n');
</script>

<section class="card panel" aria-label={t('settings.guide')}>
  <h2>{t('settings.guide')}</h2>
  <p class="desc">{t('guide.lede')}</p>
  {#each SECTIONS as id (id)}
    <details open={open === id} ontoggle={(event) => event.currentTarget.open && (open = id)}>
      <summary>{t(`guide.${id}.title`)}</summary>
      <div class="body">
        {#each paragraphs(id) as text}
          <p>{text}</p>
        {/each}
      </div>
    </details>
  {/each}
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

  details {
    border-top: 1px solid var(--line);
  }

  summary {
    display: flex;
    align-items: center;
    min-height: 56px;
    font: 500 20px/1.3 var(--serif);
    cursor: pointer;
  }

  .body {
    padding: 0 0 16px;
  }

  .body p {
    margin: 0 0 10px;
    font: 400 15px/1.6 var(--sans);
    color: var(--ink-2);
  }
</style>
