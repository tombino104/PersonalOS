<script>
  import { onMount } from 'svelte';
  import { api, pluginRequest } from '$core/lib/api.js';
  import Link from '$core/components/Link.svelte';
  import { formatDate } from '$core/lib/dates.js';
  import { locale, t } from '$core/lib/i18n.svelte.js';

  const DAYS_SHOWN = 30;

  let days = $state([]);
  let tokens = $state([]);
  let status = $state('loading');
  let name = $state('iPhone');
  let created = $state(null);
  let busy = $state(false);
  let failure = $state('');
  let revoking = $state(null);
  let copied = $state(false);

  const address = `${location.origin}/api/v1/ingest/health`;
  const largest = $derived(Math.max(1, ...days.map((item) => item.steps)));
  const number = (value) => new Intl.NumberFormat(locale()).format(value);
  const dayLabel = (day) => formatDate(day, locale(), { weekday: 'short', day: 'numeric', month: 'short' });

  async function load() {
    try {
      const result = await pluginRequest('health', 'GET', `/days?limit=${DAYS_SHOWN}`);
      days = result.days;
      status = 'ready';
    } catch {
      status = 'error';
    }
    if (!__DEMO__) {
      try {
        tokens = (await api.tokens('health')).tokens;
      } catch {
        tokens = [];
      }
    }
  }

  onMount(load);

  async function create(event) {
    event.preventDefault();
    busy = true;
    failure = '';
    copied = false;
    try {
      created = await api.createToken(name.trim(), 'health');
      name = '';
      tokens = (await api.tokens('health')).tokens;
    } catch (error) {
      failure = error.code === 'too_many_tokens' ? t('plugin.health.tooMany') : t('error.generic');
    } finally {
      busy = false;
    }
  }

  async function revoke(id) {
    if (revoking !== id) {
      revoking = id;
      return;
    }
    try {
      await api.revokeToken(id);
      tokens = tokens.filter((item) => item.id !== id);
      if (created?.id === id) created = null;
    } catch {
      failure = t('error.generic');
    } finally {
      revoking = null;
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(created.token);
      copied = true;
    } catch {
      copied = false;
    }
  }
</script>

<Link class="back" href="/more">
  <svg class="icon small" viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6" /></svg>{t('nav.more')}
</Link>
<header class="head">
  <div class="eyebrow">{t('plugin.health.eyebrow')}</div>
  <h1 class="title">{t('plugin.health.heading')} <em>{t('plugin.health.headingEmphasis')}</em></h1>
  <p class="lede">{t('plugin.health.lede')}</p>
</header>

{#if status === 'error'}
  <p class="error" role="alert">{t('error.generic')}</p>
{:else if status === 'loading'}
  <p class="lede" aria-live="polite">{t('common.loading')}</p>
{:else if days.length === 0}
  <section class="card block">
    <p class="lede">{t('plugin.health.empty')}</p>
  </section>
{:else}
  <section class="card block" aria-label={t('plugin.health.days')}>
    <div class="eyebrow">{t('plugin.health.days')}</div>
    <ul class="days">
      {#each days as item (item.day)}
        <li class="day">
          <span class="when">{dayLabel(item.day)}</span>
          <span class="track" aria-hidden="true"><span class="bar" style:width="{(item.steps / largest) * 100}%"></span></span>
          <span class="count">{number(item.steps)}</span>
        </li>
      {/each}
    </ul>
  </section>
{/if}

{#if !__DEMO__}
  <section class="card block" aria-label={t('plugin.health.connect')}>
    <div class="eyebrow">{t('plugin.health.connect')}</div>
    <p class="muted note">{t('plugin.health.connectHint')}</p>

    <label class="label" for="health-address">{t('plugin.health.address')}</label>
    <input id="health-address" class="field" type="text" readonly value={address} onfocus={(event) => event.currentTarget.select()} />

    {#if tokens.length}
      <ul class="tokens">
        {#each tokens as item (item.id)}
          <li class="token">
            <span>
              {item.name}
              <span class="muted small">
                {item.last_used_at ? t('plugin.health.lastUsed', { day: dayLabel(item.last_used_at.slice(0, 10)) }) : t('plugin.health.neverUsed')}
              </span>
            </span>
            <button class="btn" type="button" onclick={() => revoke(item.id)}>
              {revoking === item.id ? t('plugin.health.revokeSure') : t('plugin.health.revoke')}
            </button>
          </li>
        {/each}
      </ul>
    {/if}

    {#if created}
      <div class="secret" role="status">
        <p class="muted note">{t('plugin.health.shownOnce')}</p>
        <code class="code">{created.token}</code>
        <button class="btn" type="button" onclick={copy}>{copied ? t('plugin.health.copied') : t('plugin.health.copy')}</button>
      </div>
    {/if}

    <form class="create" onsubmit={create}>
      <div class="grow">
        <label class="label" for="health-token-name">{t('plugin.health.deviceName')}</label>
        <input id="health-token-name" class="field" type="text" maxlength="60" bind:value={name} />
      </div>
      <button class="btn solid" type="submit" disabled={busy || !name.trim()}>{t('plugin.health.create')}</button>
    </form>
    {#if failure}
      <p class="error" role="alert">{failure}</p>
    {/if}
    <p class="muted note">{t('plugin.health.howTo')}</p>
  </section>
{/if}

<p class="muted foot">{t('plugin.health.foot')}</p>

<style>
  .block {
    margin-top: 24px;
    padding: 20px 24px;
  }

  .days {
    display: grid;
    gap: 8px;
    margin: 14px 0 0;
    padding: 0;
    list-style: none;
  }

  .day {
    display: grid;
    grid-template-columns: 110px 1fr 64px;
    align-items: center;
    gap: 12px;
    font: 400 14px/1.4 var(--sans);
  }

  .when {
    color: var(--ink-2);
  }

  .track {
    height: 8px;
    border-radius: 4px;
    background: var(--line);
    overflow: hidden;
  }

  .bar {
    display: block;
    height: 100%;
    border-radius: 4px;
    background: var(--ink-2);
  }

  .count {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .note {
    margin: 10px 0 14px;
    font: 400 14px/1.5 var(--sans);
  }

  .small {
    display: block;
    font-size: 12px;
  }

  .tokens {
    margin: 16px 0 0;
    padding: 0;
    list-style: none;
  }

  .token {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 0;
    border-top: 1px solid var(--line);
    font: 400 15px/1.4 var(--sans);
  }

  .secret {
    margin-top: 16px;
    padding: 14px 16px;
    border: 1px dashed var(--line);
    border-radius: 8px;
  }

  .code {
    display: block;
    margin: 8px 0 12px;
    font: 400 13px/1.5 ui-monospace, monospace;
    overflow-wrap: anywhere;
    user-select: all;
  }

  .create {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 12px;
    margin-top: 18px;
  }

  .grow {
    flex: 1 1 200px;
  }

  .foot {
    margin: 24px 0 0;
    font: 400 13px/1.5 var(--sans);
  }
</style>
