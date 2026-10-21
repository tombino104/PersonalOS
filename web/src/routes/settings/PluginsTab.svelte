<script>
  import PermissionsDialog from '../../components/PermissionsDialog.svelte';
  import RemoveDataDialog from '../../components/RemoveDataDialog.svelte';
  import { api } from '../../lib/api.js';
  import { has, t } from '../../lib/i18n.svelte.js';
  import { loadPlugins, plugins, setPlugins, settingsPanel } from '../../lib/plugins.svelte.js';

  const SWITCHABLE = new Set(['active', 'inactive', 'error']);

  let confirming = $state(null);
  let busy = $state(false);
  let failure = $state('');
  let removing = $state(null);
  let removeError = $state('');

  function name(plugin) {
    const key = `plugin.${plugin.id}.name`;
    return has(key) ? t(key) : plugin.name;
  }

  function description(plugin) {
    const key = `plugin.${plugin.id}.description`;
    return has(key) ? t(key) : plugin.description;
  }

  function permissionsText(plugin) {
    if (plugin.permissions.length === 0) return t('plugins.noPermissions');
    return t('plugins.permissions', {
      list: plugin.permissions.map((permission) => t(`permission.${permission}`)).join(', '),
    });
  }

  function stateText(plugin) {
    return t(`plugins.state.${plugin.active || plugin.state !== 'inactive' ? plugin.state : 'off'}`);
  }

  function chipClass(plugin) {
    if (['error', 'broken', 'invalid', 'incompatible', 'missing'].includes(plugin.state)) return 'bad';
    return plugin.active ? 'good' : 'off';
  }

  async function toggle(plugin) {
    failure = '';
    if (plugin.active) {
      busy = true;
      try {
        setPlugins((await api.deactivatePlugin(plugin.id)).plugins);
      } catch {
        failure = t('error.generic');
      } finally {
        busy = false;
      }
    } else {
      confirming = plugin;
    }
  }

  async function removeData(confirmation) {
    busy = true;
    removeError = '';
    try {
      setPlugins((await api.removePluginData(removing.id, confirmation)).plugins);
      removing = null;
    } catch {
      removeError = t('plugins.removeFailed');
    } finally {
      busy = false;
    }
  }

  async function confirm() {
    busy = true;
    failure = '';
    try {
      setPlugins((await api.activatePlugin(confirming.id)).plugins);
      confirming = null;
    } catch {
      failure = t('plugins.activateFailed');
      confirming = null;
      await loadPlugins();
    } finally {
      busy = false;
    }
  }
</script>

<section class="card panel" aria-label={t('settings.plugins')}>
  <h2>{t('settings.plugins')}</h2>
  <p class="desc">{t('plugins.lede')}</p>
  {#if failure}
    <p class="error" role="alert">{failure}</p>
  {/if}
  {#each plugins.list as plugin (plugin.id)}
    {@const Panel = settingsPanel(plugin.id)}
    <div class="item top">
      <span class="grow">
        <span class="name">{name(plugin)}</span>
        {#if description(plugin)}<span class="note">{description(plugin)}</span>{/if}
        <span class="meta">{permissionsText(plugin)}</span>
        {#if plugin.message && plugin.state !== 'active' && plugin.state !== 'inactive'}
          <span class="problem">{t('plugins.lastError', { message: plugin.message })}</span>
        {/if}
        {#if plugin.state === 'error' && !plugin.active}
          <span class="problem">{t('plugins.autoOff')}</span>
        {/if}
        {#if plugin.installed && !plugin.active}
          <button class="remove" onclick={() => ((removeError = ''), (removing = plugin))}>{t('plugins.removeData')}</button>
        {/if}
      </span>
      <span class="chip-state {chipClass(plugin)}"><i></i>{stateText(plugin)}</span>
      <button
        class="toggle"
        role="switch"
        aria-label={name(plugin)}
        aria-checked={plugin.active}
        disabled={!SWITCHABLE.has(plugin.state) || busy}
        onclick={() => toggle(plugin)}
      ></button>
    </div>
    {#if Panel}
      <div class="plugin-panel"><Panel /></div>
    {/if}
  {:else}
    <p class="muted">{t('plugins.none')}</p>
  {/each}
</section>

{#if removing}
  <RemoveDataDialog
    id={removing.id}
    name={name(removing)}
    {busy}
    error={removeError}
    onconfirm={removeData}
    oncancel={() => (removing = null)}
  />
{/if}

{#if confirming}
  <PermissionsDialog
    name={name(confirming)}
    permissions={confirming.permissions}
    {busy}
    onconfirm={confirm}
    oncancel={() => (confirming = null)}
  />
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

  .name {
    display: block;
    font: 500 15px/1.3 var(--sans);
  }

  .note,
  .meta,
  .problem {
    display: block;
    margin-top: 3px;
    font: 400 13px/1.4 var(--sans);
    color: var(--ink-3);
  }

  .meta {
    font-size: 12px;
  }

  .problem {
    color: var(--danger);
  }

  .chip-state {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font: 500 12px/1 var(--sans);
    color: var(--ink-3);
    white-space: nowrap;
  }

  .chip-state i {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--line);
  }

  .chip-state.good i {
    background: var(--ok);
  }

  .chip-state.bad {
    color: var(--danger);
  }

  .chip-state.bad i {
    background: var(--danger);
  }

  .remove {
    margin-top: 8px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--ink-3);
    font: 500 12px/1.4 var(--sans);
    text-decoration: underline;
    cursor: pointer;
  }

  .remove:hover {
    color: var(--danger);
  }

  .toggle:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .plugin-panel {
    padding: 0 0 16px;
  }
</style>
