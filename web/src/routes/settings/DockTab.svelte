<script>
  import Icon from '../../components/Icon.svelte';
  import { FIXED_KEYS, MAX_DOCK, isFull } from '../../lib/dock.js';
  import { addToDock, dockLayout, moveInDock, removeFromDock, resetDock } from '../../lib/dock.svelte.js';
  import { t } from '../../lib/i18n.svelte.js';

  let failure = $state('');

  const layout = $derived(dockLayout());
  const full = $derived(isFull(layout.keys));
  const movable = $derived(layout.inDock.filter((item) => item.key !== 'more'));

  const label = (item) => item.text ?? t(item.labelKey);

  async function run(action) {
    failure = '';
    try {
      await action();
    } catch {
      failure = t('error.generic');
    }
  }
</script>

<section class="card panel" aria-label={t('settings.dock')}>
  <h2>{t('settings.dock')}</h2>
  <p class="desc">{t('dock.lede', { max: MAX_DOCK })}</p>
  <p class="count" aria-live="polite">{t('dock.count', { count: layout.keys.length, max: MAX_DOCK })}</p>

  <div class="list" role="list" aria-label={t('dock.inDock')}>
    {#each layout.inDock as item (item.key)}
      {@const fixed = FIXED_KEYS.includes(item.key)}
      {@const index = movable.findIndex((candidate) => candidate.key === item.key)}
      <div class="item" role="listitem">
        <span class="ico"><Icon name={item.icon} /></span>
        <span class="grow">
          {label(item)}
          {#if fixed}<span class="tag">{t('dock.always')}</span>{/if}
        </span>
        {#if item.key !== 'more'}
          <span class="moves">
            <button class="move" type="button" aria-label={t('dock.moveUp', { name: label(item) })} disabled={index === 0} onclick={() => run(() => moveInDock(item.key, -1))}>
              <Icon name="up" small />
            </button>
            <button class="move" type="button" aria-label={t('dock.moveDown', { name: label(item) })} disabled={index === movable.length - 1} onclick={() => run(() => moveInDock(item.key, 1))}>
              <Icon name="down" small />
            </button>
          </span>
        {/if}
        <button
          class="toggle"
          role="switch"
          aria-label={t('dock.show', { name: label(item) })}
          aria-checked="true"
          disabled={fixed}
          onclick={() => run(() => removeFromDock(item.key))}
        ></button>
      </div>
    {/each}
  </div>

  {#if layout.outOfDock.length > 0}
    <h3 class="eyebrow heading">{t('dock.notInDock')}</h3>
    <div class="list" role="list" aria-label={t('dock.notInDock')}>
      {#each layout.outOfDock as item (item.key)}
        <div class="item" role="listitem">
          <span class="ico"><Icon name={item.icon} /></span>
          <span class="grow">{label(item)}</span>
          <button
            class="toggle"
            role="switch"
            aria-label={t('dock.show', { name: label(item) })}
            aria-checked="false"
            disabled={full}
            onclick={() => run(() => addToDock(item.key))}
          ></button>
        </div>
      {/each}
    </div>
    {#if full}
      <p class="muted note">{t('dock.full', { max: MAX_DOCK })}</p>
    {/if}
  {/if}

  {#if failure}
    <p class="error" role="alert">{failure}</p>
  {/if}

  <button class="btn reset" type="button" onclick={() => run(resetDock)}>{t('dock.reset')}</button>
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
    margin: 8px 0 12px;
    font: 400 14px/1.5 var(--sans);
    color: var(--ink-2);
  }

  .count {
    margin: 0 0 8px;
    font: 500 14px/1.4 var(--sans);
  }

  .heading {
    margin: 24px 0 8px;
  }

  .grow {
    flex: 1 1 auto;
    min-width: 0;
    font: 500 16px/1.3 var(--sans);
  }

  .tag {
    margin-left: 8px;
    color: var(--ink-3);
    font: 400 13px/1 var(--sans);
  }

  .ico {
    display: flex;
    flex: none;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: var(--paper-2);
  }

  .moves {
    display: flex;
    gap: 4px;
  }

  .move {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 50%;
    background: var(--surface);
    color: var(--ink-2);
    cursor: pointer;
  }

  .move:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .toggle:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .note {
    margin: 8px 0 0;
    font: 400 13px/1.5 var(--sans);
  }

  .reset {
    margin-top: 20px;
  }
</style>
