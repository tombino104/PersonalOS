<script>
  import { onMount } from 'svelte';
  import { pluginRequest } from '$core/lib/api.js';
  import Link from '$core/components/Link.svelte';
  import { formatDate } from '$core/lib/dates.js';
  import { locale, t } from '$core/lib/i18n.svelte.js';
  import PersonDialog from './PersonDialog.svelte';
  import { parseBirthday, whenKey } from './people.js';

  let people = $state([]);
  let status = $state('loading');
  let dialogOpen = $state(false);
  let editing = $state(null);
  let reload = $state(0);

  $effect(() => {
    reload;
    pluginRequest('people', 'GET', '/people')
      .then((result) => {
        people = result.people;
        status = 'ready';
      })
      .catch(() => {
        status = 'error';
      });
  });

  function open(person) {
    editing = person;
    dialogOpen = true;
  }

  function saved() {
    dialogOpen = false;
    reload += 1;
  }

  function birthdayText(person) {
    const parsed = parseBirthday(person.birthday);
    if (!parsed) return '';
    const pad = (number) => String(number).padStart(2, '0');
    const text = formatDate(`2000-${pad(parsed.month)}-${pad(parsed.day)}`, locale(), { day: 'numeric', month: 'long' });
    return parsed.year ? `${text} ${parsed.year}` : text;
  }

  function whenText(person) {
    const key = whenKey(person.days_until);
    if (!key) return '';
    const base = t(`plugin.people.${key}`, { count: person.days_until });
    return person.turning ? `${base} · ${t('plugin.people.turning', { age: person.turning })}` : base;
  }
</script>

<Link class="back" href="/more">
  <svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('nav.more')}
</Link>
<header class="head">
  <div>
    <div class="eyebrow">{t('plugin.people.eyebrow')}</div>
    <h1 class="title">{t('plugin.people.heading')} <em>{t('plugin.people.headingEmphasis')}</em></h1>
    <p class="lede">{t('plugin.people.lede')}</p>
  </div>
  <button class="btn solid" type="button" onclick={() => open(null)}>{t('plugin.people.add')}</button>
</header>

{#if status === 'error'}
  <p class="error" role="alert">{t('error.generic')}</p>
{:else if status === 'loading'}
  <p class="lede" aria-live="polite">{t('common.loading')}</p>
{:else if people.length === 0}
  <section class="card empty">
    <p class="lede">{t('plugin.people.empty')}</p>
  </section>
{:else}
  <section class="card list" aria-label={t('plugin.people.heading')}>
    {#each people as person (person.id)}
      <div class="row">
        <div class="who">
          <span class="name">{person.name}</span>
          {#if person.birthday}
            <span class="muted when">{birthdayText(person)}</span>
          {/if}
        </div>
        <span class="soon" class:near={person.days_until !== null && person.days_until <= 7}>{whenText(person)}</span>
        <button class="btn" type="button" onclick={() => open(person)}>{t('plugin.people.editShort')}</button>
      </div>
    {/each}
  </section>
{/if}

<p class="muted foot">{t('plugin.people.foot')}</p>

{#if dialogOpen}
  {#key editing?.id ?? 'new'}
    <PersonDialog person={editing} onsaved={saved} onclose={() => (dialogOpen = false)} />
  {/key}
{/if}

<style>
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 24px;
  }

  .list {
    padding: 8px 24px;
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 16px;
    padding: 14px 0;
    border-top: 1px solid var(--line);
  }

  .row:first-child {
    border-top: 0;
  }

  .who {
    display: flex;
    flex: 1 1 200px;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .name {
    font: 500 18px/1.3 var(--serif);
  }

  .when {
    font: 400 13px/1.3 var(--sans);
  }

  .soon {
    font: 400 14px/1.3 var(--sans);
    color: var(--ink-2);
  }

  .soon.near {
    font-weight: 500;
    color: var(--ink);
  }

  .empty {
    padding: 28px;
  }

  .empty .lede {
    margin: 0;
  }

  .foot {
    margin: 16px 2px 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
