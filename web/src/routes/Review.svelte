<script>
  import { onMount } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import PeriodView from '../components/PeriodView.svelte';
  import WeekView from '../components/WeekView.svelte';
  import { api } from '../lib/api.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { router } from '../lib/router.svelte.js';
  import { weekRange } from '../lib/review.js';
  import { VIEWS, canGoBack, latestPeriod, periodFor, periodLabel, shiftView, switchView, viewOf } from '../lib/recap.js';

  let today = $state('');
  let firstDay = $state(null);
  let kind = $state('week');
  let period = $state('');
  let wantedDay = $state('');
  let failed = $state(false);

  onMount(async () => {
    try {
      const info = await api.today();
      today = info.day;
      firstDay = info.first_day;
      const day = router.query.get('day');
      const asked = router.query.get('period');
      const view = router.query.get('view');
      const validDay = day && /^\d{4}-\d{2}-\d{2}$/.test(day) && day <= today ? day : '';
      if (asked && /^\d{4}(-\d{2})?$/.test(asked)) {
        kind = viewOf(asked);
        period = asked;
      } else if (router.path === '/recap') {
        kind = VIEWS.includes(view) && view !== 'week' ? view : 'month';
        period = periodFor(kind, validDay || today);
      } else {
        kind = VIEWS.includes(view) ? view : 'week';
        period = periodFor(kind, validDay || today);
      }
      wantedDay = validDay;
    } catch {
      failed = true;
    }
  });

  const isLatest = $derived(Boolean(period) && period === latestPeriod(kind, today));
  const backAllowed = $derived(Boolean(period) && canGoBack(kind, period, firstDay));
  const title = $derived(
    !period ? '' : kind === 'week' ? weekRange(period, locale()) : periodLabel(period, locale()),
  );

  function choose(next) {
    wantedDay = '';
    period = switchView(kind, next, period, today);
    kind = next;
  }

  function move(delta) {
    wantedDay = '';
    period = shiftView(kind, period, delta);
  }

  function latest() {
    wantedDay = '';
    period = latestPeriod(kind, today);
  }

  function zoom(month) {
    wantedDay = '';
    kind = 'month';
    period = month;
  }
</script>

<div class="content stagger">
  <header>
    <div>
      <div class="eyebrow">{t('nav.review')}</div>
      <h1 class="title">
        {t(kind === 'week' ? 'review.titleLead' : 'recap.titleLead')} <em>{title}</em>
      </h1>
    </div>
    <div class="controls">
      <div class="segmented" role="group" aria-label={t('review.views')}>
        {#each VIEWS as item (item)}
          <button class="seg" class:on={kind === item} aria-pressed={kind === item} disabled={!today} onclick={() => choose(item)}>{t(`review.view.${item}`)}</button>
        {/each}
      </div>
      <div class="nav" role="group" aria-label={t('review.choose')}>
        <button class="btn" type="button" aria-label={t('review.previousPeriod')} disabled={!backAllowed} onclick={() => move(-1)}>
          <Icon name="back" small />
        </button>
        <button class="btn" type="button" disabled={isLatest || !period} onclick={latest}>{t(`review.now.${kind}`)}</button>
        <button class="btn" type="button" aria-label={t('review.nextPeriod')} disabled={isLatest || !period} onclick={() => move(1)}>
          <Icon name="forward" small />
        </button>
      </div>
    </div>
  </header>

  {#if failed}
    <p class="error" role="alert">{t('error.generic')}</p>
  {:else if !period}
    <p class="lede" aria-live="polite">{t('common.loading')}</p>
  {:else}
    {#key kind + period}
      {#if kind === 'week'}
        <WeekView week={period} {today} {wantedDay} />
      {:else}
        <PeriodView {period} {today} {wantedDay} onzoom={zoom} />
      {/if}
    {/key}
  {/if}
</div>

<style>
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    margin: 20px 0 24px;
  }

  .nav {
    display: flex;
    gap: 8px;
  }

  .nav .btn:not(:nth-child(2)) {
    width: 44px;
    padding: 0;
  }

  .nav .btn:nth-child(2) {
    min-width: 10.5rem;
  }
</style>
