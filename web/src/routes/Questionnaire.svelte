<script>
  import { untrack } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import Link from '../components/Link.svelte';
  import { api, ApiError } from '../lib/api.js';
  import { AREAS } from '../lib/charts.js';
  import { formatDate } from '../lib/dates.js';
  import { locale, t } from '../lib/i18n.svelte.js';
  import { navigate, router } from '../lib/router.svelte.js';
  import { displayName } from '../lib/profile.svelte.js';
  import { questionnaireBlocks } from '../lib/plugins.svelte.js';

  let status = $state('loading');
  let report = $state(null);
  let day = $state('');
  let today = $state('');
  let opensAt = $state('');
  let reflection = $state('');
  let saved = $state(false);
  let failure = $state('');
  let completing = $state(false);
  let saveTimer = null;

  const groups = $derived(
    report
      ? AREAS.map((area) => ({
          area,
          tasks: report.completions.filter((completion) => completion.area === area),
        })).filter((group) => group.tasks.length > 0)
      : [],
  );

  async function load(requested) {
    try {
      const info = await api.today();
      today = info.day;
      day = requested ?? today;
      if (day === today && info.report_opens_at) {
        opensAt = info.report_opens_at;
        status = 'locked';
        return;
      }
      let opened = await api.openReport(day);
      if (!opened.completed && opened.editable) opened = await api.syncReport(day);
      report = opened;
      reflection = opened.reflection ?? '';
      saved = Boolean(opened.reflection) || opened.completions.some((c) => c.done);
      status = opened.editable ? 'ready' : 'closed';
    } catch (error) {
      status = error instanceof ApiError && error.code === 'report_closed' ? 'closed' : 'error';
      if (error instanceof ApiError && error.code === 'report_not_open') {
        opensAt = error.message.match(/\d{2}:\d{2}/)?.[0] ?? '';
        status = 'locked';
      }
    }
  }

  $effect(() => {
    const requested = router.query.get('day');
    untrack(() => load(requested));
  });

  async function toggle(completion) {
    const next = !completion.done;
    completion.done = next;
    failure = '';
    try {
      await api.setCompletion(day, completion.activity_id, next);
      saved = true;
    } catch {
      completion.done = !next;
      failure = t('error.generic');
    }
  }

  async function flushReflection() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = null;
    await api.setReflection(day, reflection.trim() === '' ? null : reflection);
    saved = true;
  }

  function onReflectionInput() {
    saved = false;
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => flushReflection().catch(() => (failure = t('error.generic'))), 700);
  }

  async function complete() {
    completing = true;
    failure = '';
    try {
      await flushReflection();
      await api.completeReport(day);
      navigate(`/questionnaire/done?day=${day}`);
    } catch {
      failure = t('error.generic');
      completing = false;
    }
  }

  const blocks = $derived(questionnaireBlocks());
  const weekday = $derived(day ? formatDate(day, locale(), { weekday: 'long' }) : '');
  const fullDate = $derived(day ? formatDate(day, locale(), { day: 'numeric', month: 'long' }) : '');
</script>

<div class="content narrow">
  {#if status === 'loading'}
    <p class="lede" aria-live="polite">{t('common.loading')}</p>
  {:else if status === 'error'}
    <p class="error" role="alert">{t('error.generic')}</p>
  {:else if status === 'locked'}
    <header>
      <div class="eyebrow">{t('questionnaire.eyebrow')}</div>
      <h1 class="title">{t('questionnaire.lockedTitle')}</h1>
      <p class="lede">{t('questionnaire.locked', { time: opensAt })}</p>
    </header>
    <div class="locked-actions">
      <Link class="btn" href="/settings/activities">{t('questionnaire.lockedChange')}</Link>
    </div>
  {:else if status === 'closed'}
    <header>
      <div class="eyebrow">{t('questionnaire.eyebrow')}</div>
      <h1 class="title">{fullDate}</h1>
      <p class="lede">{t('questionnaire.closed')}</p>
    </header>
    <Link class="btn" href="/archive">{t('nav.archive')}</Link>
  {:else}
    <header class="stagger">
      <div class="eyebrow">{t('questionnaire.eyebrow')}</div>
      <h1 class="title">
        {weekday.charAt(0).toUpperCase() + weekday.slice(1)}
        <em>{day === today ? t('questionnaire.evening') : fullDate}</em>
      </h1>
      <p class="lede">
        {t('questionnaire.greeting', { name: displayName() })}
        {#if saved}· {t('questionnaire.draftSaved')}{/if}
      </p>
      {#if report.completed}
        <p class="lede">{t('questionnaire.alreadyDone')}</p>
      {/if}
    </header>

    {#if groups.length === 0}
      <section class="card empty">
        <p class="lede">{t('questionnaire.noActivities')}</p>
        <Link class="btn" href="/settings">{t('nav.settings')}</Link>
      </section>
    {/if}

    <div class="groups">
      {#each groups as group (group.area)}
        <section class="rise" data-area={group.area} aria-label={t(`area.${group.area}`)}>
          <div class="group-head">
            <span class="dot"></span>
            <h2>{t(`area.${group.area}`)}</h2>
          </div>
          {#each group.tasks as task (task.activity_id)}
            <button
              class="task"
              class:on={task.done}
              type="button"
              aria-pressed={task.done}
              onclick={() => toggle(task)}
            >
              <span class="box"><Icon name="check" small /></span>
              <span class="name">{task.name}</span>
            </button>
          {/each}
        </section>
      {/each}

      {#each blocks as block (block.pluginId + block.blockId)}
        <section class="rise" aria-label={t(`plugin.${block.pluginId}.title`)}>
          <block.component {day} editable={report.editable} />
        </section>
      {/each}

      <section class="rise" aria-label={t('questionnaire.reflection')}>
        <h2 class="reflection-title">{t('questionnaire.reflection')}</h2>
        <label class="label" for="reflection">{t('questionnaire.optional')}</label>
        <textarea
          id="reflection"
          class="field"
          rows="4"
          maxlength="5000"
          placeholder={t('questionnaire.reflectionPlaceholder')}
          bind:value={reflection}
          oninput={onReflectionInput}
        ></textarea>
      </section>

      {#if failure}
        <p class="error" role="alert">{failure}</p>
      {/if}

      <button class="finish" type="button" disabled={completing} onclick={complete}>
        {report.completed ? t('questionnaire.save') : t('questionnaire.complete')}
      </button>
    </div>
  {/if}
</div>

<style>
  .locked-actions {
    display: flex;
    gap: 12px;
  }

  .groups {
    display: flex;
    flex-direction: column;
    gap: 28px;
  }

  .group-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }

  .group-head h2,
  .reflection-title {
    margin: 0;
    font: 500 20px/1 var(--serif);
  }

  .reflection-title {
    margin-bottom: 12px;
  }

  .task {
    display: flex;
    align-items: center;
    gap: 16px;
    width: 100%;
    min-height: 52px;
    padding: 8px 4px;
    border: 0;
    border-top: 1px solid var(--line);
    background: transparent;
    color: var(--ink);
    font: 400 16px/1.3 var(--sans);
    text-align: left;
    cursor: pointer;
  }

  .box {
    display: flex;
    flex: none;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border: 1.5px solid var(--ink-3);
    border-radius: 8px;
    color: var(--paper);
  }

  .box :global(.icon) {
    stroke-width: 2.2;
    opacity: 0;
    transform: scale(0.6);
    transition: opacity 0.15s, transform 0.15s;
  }

  .task.on .box {
    background: var(--area);
    border-color: var(--area);
    animation: stamp 0.28s cubic-bezier(0.2, 1.4, 0.4, 1) 1;
  }

  .task.on .box :global(.icon) {
    opacity: 1;
    transform: scale(1);
  }

  .task.on .name {
    color: var(--ink-2);
  }

  @keyframes stamp {
    0% { transform: scale(0.8); }
    60% { transform: scale(1.14); }
    100% { transform: scale(1); }
  }

  @media (prefers-reduced-motion: reduce) {
    .task.on .box { animation: none; }
    .box :global(.icon) { transition: none; }
  }

  .finish {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 56px;
    border: 0;
    border-radius: 999px;
    background: var(--ink);
    color: var(--paper);
    font: 500 16px/1 var(--sans);
    cursor: pointer;
  }

  .finish:disabled {
    opacity: 0.6;
  }

  .empty {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 20px 24px;
  }
</style>
