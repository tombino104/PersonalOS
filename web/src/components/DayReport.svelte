<script>
  import Link from './Link.svelte';
  import { api } from '../lib/api.js';
  import { AREAS } from '../lib/charts.js';
  import { addDays, formatDate } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { reportSections } from '../lib/plugins.svelte.js';

  let { day, today, filled } = $props();

  let detail = $state(null);
  let detailStatus = $state('idle');

  $effect(() => {
    const requested = day;
    if (!filled) {
      detail = null;
      detailStatus = 'empty';
      return;
    }
    detailStatus = 'loading';
    api
      .getReport(requested)
      .then((report) => {
        if (requested !== day) return;
        detail = report;
        detailStatus = 'ready';
      })
      .catch(() => {
        detailStatus = 'error';
      });
  });

  const groups = $derived(
    detail
      ? AREAS.map((area) => ({
          area,
          items: detail.completions.filter((completion) => completion.area === area),
        })).filter((group) => group.items.length > 0)
      : [],
  );
  const sections = $derived(reportSections());
  const editable = $derived(day === today || day === addDays(today, -1));
  const longTitle = $derived(formatDate(day, locale(), { weekday: 'long', day: 'numeric', month: 'long' }));
</script>

<section class="card detail rise" aria-label={t('archive.detail')}>
  <div class="detail-head">
    <div>
      <div class="eyebrow">{formatDate(day, locale(), { weekday: 'long' })}</div>
      <h2>{longTitle}</h2>
    </div>
    {#if editable}
      <Link class="btn solid" href={`/questionnaire?day=${day}`}>{filled ? t('archive.edit') : t('archive.fill')}</Link>
    {/if}
  </div>
  {#if editable}
    <p class="muted note">{t(day === today ? 'archive.editToday' : 'archive.editYesterday')}</p>
  {/if}

  {#if detailStatus === 'empty'}
    <div class="blank-box">
      <p>{t('archive.notFilled')}</p>
      <span>{t('archive.notFilledNote')}</span>
    </div>
  {:else if detailStatus === 'error'}
    <p class="error" role="alert">{t('error.generic')}</p>
  {:else if detail && detailStatus === 'ready'}
    <div class="groups">
      {#each groups as group (group.area)}
        <div data-area={group.area}>
          <div class="group-head"><span class="dot small"></span><span>{t(`area.${group.area}`)}</span></div>
          {#each group.items as item (item.activity_id)}
            <div class="activity">
              <span class="mark" class:done={item.done}>{item.done ? '✓' : '○'}</span>
              <span class:muted={!item.done}>{item.name}</span>
            </div>
          {/each}
        </div>
      {/each}
    </div>
    {#if detail.reflection}
      <div class="reflection">
        <div class="eyebrow">{t('questionnaire.reflection')}</div>
        <p>«{detail.reflection}»</p>
      </div>
    {/if}
    {#key day}
      {#each sections as section (section.pluginId + section.sectionId)}
        <div class="plugin-section"><section.component {day} /></div>
      {/each}
    {/key}
  {/if}
</section>

<style>
  .detail {
    min-width: 0;
    margin-top: 16px;
    padding: 24px 28px;
  }

  .detail-head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .detail-head h2 {
    margin: 8px 0 0;
    font: 400 32px/1.1 var(--serif);
  }

  .note {
    margin: 12px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .blank-box {
    margin-top: 20px;
    padding: 40px 20px;
    border: 1px dashed var(--line);
    border-radius: 12px;
    text-align: center;
    color: var(--ink-2);
  }

  .blank-box p {
    margin: 0;
    font: italic 400 18px/1.4 var(--serif);
  }

  .blank-box span {
    font: 400 13px/1.5 var(--sans);
    color: var(--ink-3);
  }

  .groups {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px 28px;
    margin-top: 20px;
  }

  .group-head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    font: 500 12px/1 var(--sans);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-2);
  }

  .dot.small {
    width: 9px;
    height: 9px;
  }

  .activity {
    display: flex;
    align-items: baseline;
    gap: 12px;
    padding: 4px 0;
    font: 400 15px/1.35 var(--sans);
  }

  .mark {
    flex: none;
    width: 14px;
    font-weight: 600;
    color: var(--ink-3);
  }

  .mark.done {
    color: var(--area);
  }

  .plugin-section {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--line);
  }

  .reflection {
    margin-top: 24px;
    padding-top: 20px;
    border-top: 1px solid var(--line);
  }

  .reflection p {
    margin: 8px 0 0;
    font: italic 400 18px/1.45 var(--serif);
    white-space: pre-wrap;
  }
</style>
