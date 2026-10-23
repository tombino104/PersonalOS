<script>
  import ActivityDialog from '../../components/ActivityDialog.svelte';
  import ReminderCard from '../../components/ReminderCard.svelte';
  import ReportTimeCard from '../../components/ReportTimeCard.svelte';
  import { api } from '../../lib/api.js';
  import { AREAS } from '../../lib/charts.js';
  import { daysLabel } from '../../lib/dates.js';
  import { locale, t } from '../../lib/i18n.svelte.js';

  let activities = $state([]);
  let warnings = $state([]);
  let showArchived = $state(false);
  let status = $state('loading');
  let editing = $state(null);
  let dialogOpen = $state(false);
  let defaultArea = $state('physical');

  async function load() {
    try {
      const result = await api.activities(showArchived);
      activities = result.activities;
      warnings = result.warnings;
      status = 'ready';
    } catch {
      status = 'error';
    }
  }

  $effect(() => {
    showArchived;
    load();
  });

  const byArea = $derived(
    AREAS.map((area) => ({
      area,
      items: activities.filter((activity) => activity.area === area),
      tooMany: warnings.some((warning) => warning.area === area),
    })),
  );

  function open(activity, area) {
    editing = activity;
    defaultArea = area;
    dialogOpen = true;
  }

  function saved() {
    dialogOpen = false;
    load();
  }
</script>

<section class="card panel" aria-label={t('settings.activities')}>
  <h2>{t('settings.activities')}</h2>
  <p class="desc">{t('settings.activitiesLede')}</p>
  <div class="item">
    <span class="grow">{t('settings.showArchived')}</span>
    <button class="toggle" role="switch" aria-label={t('settings.showArchived')} aria-checked={showArchived} onclick={() => (showArchived = !showArchived)}></button>
  </div>
  {#if status === 'error'}
    <p class="error" role="alert">{t('error.generic')}</p>
  {/if}
  {#each byArea as group (group.area)}
    <div class="item top" data-area={group.area}>
      <span class="area"><span class="dot small"></span><span>{t(`area.${group.area}`)}</span></span>
      <div class="grow">
        <div class="chips">
          {#each group.items as activity (activity.id)}
            <button class="chip" class:faded={activity.archived_at} title={activity.description ?? undefined} onclick={() => open(activity, group.area)}>
              {activity.name}<b>{activity.archived_at ? t('settings.archivedTag') : t('settings.weightTag', { weight: activity.weight })}</b>{#if daysLabel(activity.days, locale())}<b>{daysLabel(activity.days, locale())}</b>{/if}{#if activity.times_per_week}<b>{t('settings.timesTag', { count: activity.times_per_week })}</b>{/if}
            </button>
          {/each}
          <button class="chip dashed" onclick={() => open(null, group.area)}>{t('settings.add')}</button>
        </div>
        {#if group.tooMany}
          <p class="warn">{t('settings.tooMany')}</p>
        {/if}
      </div>
    </div>
  {/each}
</section>

<ReportTimeCard />

{#if !__DEMO__}
  <ReminderCard />
{/if}

{#if dialogOpen}
  {#key editing?.id ?? `new-${defaultArea}`}
    <ActivityDialog activity={editing} area={defaultArea} onsaved={saved} onclose={() => (dialogOpen = false)} />
  {/key}
{/if}

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

  .grow {
    flex-grow: 1;
    min-width: 0;
  }

  .top {
    align-items: flex-start;
  }

  .area {
    display: flex;
    flex: none;
    align-items: center;
    gap: 8px;
    width: 120px;
    padding-top: 14px;
    font: 500 15px/1 var(--sans);
  }

  .dot.small {
    width: 9px;
    height: 9px;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .warn {
    margin: 12px 0 0;
    font: 400 13px/1.5 var(--sans);
    color: var(--ink-2);
  }

  @media (max-width: 560px) {
    .area {
      width: 96px;
    }
  }
</style>
