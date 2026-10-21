<script>
  import { fade, fly } from 'svelte/transition';
  import SetupForm from '../components/SetupForm.svelte';
  import { AREAS } from '../lib/charts.js';
  import { t } from '../lib/i18n.svelte.js';

  const STEPS = ['welcome', 'areas', 'evening', 'score', 'home', 'plugins', 'data'];
  const LAST = STEPS.length;

  const reduced = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const RING = [0, 1, 2, 3, 4, 5].map((index) => {
    const angle = (Math.PI / 3) * index - Math.PI / 2;
    return { x: 80 + 50 * Math.cos(angle), y: 80 + 50 * Math.sin(angle), area: AREAS[index] };
  });

  let index = $state(0);
  let direction = $state(1);

  const key = $derived(index < LAST ? STEPS[index] : 'account');

  function go(target) {
    direction = target >= index ? 1 : -1;
    index = Math.max(0, Math.min(LAST, target));
  }
</script>

<main class="page bare">
  <div class="content narrow onboarding">
    <div class="top">
      <div class="eyebrow">Personal OS</div>
      <ol class="progress" aria-label={t('onboarding.progress', { current: index + 1, total: LAST + 1 })}>
        {#each Array(LAST + 1) as _, position}
          <li class:done={position <= index} aria-current={position === index ? 'step' : undefined}></li>
        {/each}
      </ol>
    </div>

    {#key index}
      <div
        class="step"
        in:fly={{ x: reduced ? 0 : 36 * direction, duration: reduced ? 0 : 320, delay: reduced ? 0 : 80 }}
        out:fade={{ duration: reduced ? 0 : 80 }}
      >
        {#if key === 'welcome'}
          <svg class="art" viewBox="0 0 160 160" aria-hidden="true">
            <polygon class="ring" points={RING.map((point) => `${point.x},${point.y}`).join(' ')} />
            {#each RING as point}
              <circle cx={point.x} cy={point.y} r="12" style:fill={`var(--area-${point.area})`} />
            {/each}
            <circle cx="80" cy="80" r="7" class="core" />
          </svg>
        {:else if key === 'areas'}
          <div class="chips" aria-hidden="true">
            {#each AREAS as area}
              <span class="chip"><span class="dot" data-area={area}></span>{t(`area.${area}`)}</span>
            {/each}
          </div>
        {:else if key === 'evening'}
          <div class="list" aria-hidden="true">
            {#each [true, false, true] as on, row}
              <div class="row">
                <span class="box" class:on><svg viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5" /></svg></span>
                <span class="bar" style:width={`${[70, 55, 80][row]}%`}></span>
              </div>
            {/each}
          </div>
        {:else if key === 'score'}
          <svg class="art wide" viewBox="0 0 240 110" aria-hidden="true">
            <line x1="10" y1="95" x2="230" y2="95" class="axis" />
            <polyline points="14,70 44,52 74,60 104,38" class="line" />
            <rect x="112" y="20" width="28" height="75" class="gap" />
            <polyline points="148,48 178,34 208,44" class="line" />
          </svg>
        {:else if key === 'home'}
          <div class="minis" aria-hidden="true">
            {#each ['physical', 'intellect', 'mindset'] as area, row}
              <svg viewBox="0 0 80 50" data-area={area}>
                <polyline
                  points={['6,36 24,22 44,28 74,10', '6,18 26,30 48,14 74,24', '6,30 28,26 50,32 74,14'][row]}
                  class="trend"
                />
              </svg>
            {/each}
          </div>
        {:else if key === 'plugins'}
          <div class="chips" aria-hidden="true">
            {#each ['calendar', 'mood', 'journal', 'quote'] as name}
              <span class="chip plain">{t(`onboarding.plugin.${name}`)}</span>
            {/each}
          </div>
        {:else if key === 'data'}
          <div class="chips" aria-hidden="true">
            <span class="chip plain">{t('onboarding.data.folder')}</span>
            <span class="chip plain">{t('onboarding.data.backup')}</span>
          </div>
        {/if}

        <h1 class="title">{t(`onboarding.${key}.title`)}</h1>
        <p class="lede">{t(`onboarding.${key}.body`)}</p>

        {#if key === 'account'}
          <div class="card account"><SetupForm /></div>
        {/if}
      </div>
    {/key}

    <div class="nav">
      {#if index > 0}
        <button class="btn" type="button" onclick={() => go(index - 1)}>{t('onboarding.back')}</button>
      {/if}
      {#if index < LAST}
        <button class="btn solid next" type="button" onclick={() => go(index + 1)}>
          {index === 0 ? t('onboarding.start') : t('onboarding.next')}
        </button>
      {/if}
    </div>
    {#if index < LAST}
      <button class="skip" type="button" onclick={() => go(LAST)}>{t('onboarding.skip')}</button>
    {/if}
  </div>
</main>

<style>
  .onboarding {
    justify-content: center;
    gap: 24px;
    max-width: 520px;
  }

  .top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .progress {
    display: flex;
    gap: 6px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .progress li {
    width: 18px;
    height: 4px;
    border-radius: 2px;
    background: var(--line);
    transition: background 0.3s;
  }

  .progress li.done {
    background: var(--ink);
  }

  .step {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-height: 320px;
  }

  .step .title {
    margin: 12px 0 0;
  }

  .step .lede {
    margin: 0;
    font-size: 16px;
  }

  .art {
    width: 140px;
    height: 140px;
  }

  .art.wide {
    width: 240px;
    height: 110px;
  }

  .ring {
    fill: none;
    stroke: var(--line);
    stroke-width: 2;
  }

  .core {
    fill: var(--ink);
  }

  .axis {
    stroke: var(--ink-3);
    stroke-width: 1.5;
  }

  .line {
    fill: none;
    stroke: var(--area-mindset);
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .gap {
    fill: var(--paper-2);
    stroke: var(--line);
    stroke-dasharray: 3 3;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    min-height: 80px;
    align-content: flex-start;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface);
    font: 500 14px/1 var(--sans);
  }

  .chip.plain {
    padding: 10px 18px;
    color: var(--ink-2);
  }

  .list {
    display: flex;
    flex-direction: column;
    gap: 14px;
    width: 220px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .box {
    display: grid;
    place-items: center;
    flex: none;
    width: 26px;
    height: 26px;
    border: 1.5px solid var(--ink-3);
    border-radius: 8px;
  }

  .box svg {
    width: 16px;
    height: 16px;
    fill: none;
    stroke: var(--paper);
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
    opacity: 0;
  }

  .box.on {
    border-color: var(--area-career);
    background: var(--area-career);
  }

  .box.on svg {
    opacity: 1;
  }

  .bar {
    height: 8px;
    border-radius: 4px;
    background: var(--paper-2);
  }

  .minis {
    display: flex;
    gap: 10px;
  }

  .minis svg {
    width: 88px;
    padding: 6px;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--surface);
  }

  .trend {
    fill: none;
    stroke: var(--area);
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .account {
    margin-top: 8px;
    padding: 24px;
  }

  .nav {
    display: flex;
    gap: 12px;
  }

  .next {
    flex: 1;
  }

  .skip {
    align-self: center;
    padding: 8px 12px;
    border: 0;
    background: transparent;
    color: var(--ink-3);
    font: 400 14px/1 var(--sans);
    text-decoration: underline;
    cursor: pointer;
  }
</style>
