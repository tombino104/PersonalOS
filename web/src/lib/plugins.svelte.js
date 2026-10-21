import { api } from './api.js';
import { addMessages, has, t } from './i18n.svelte.js';
import { icons } from './icons.js';

const modules = import.meta.glob('../plugin-ui/*/index.js', { eager: true });
const locales = import.meta.glob('../plugin-ui/*/locales/*.json', { eager: true, import: 'default' });

export const MAX_DOCK_ENTRIES = 5;
export const CORE_DOCK_ENTRIES = 4;

const ui = {};
for (const [path, module] of Object.entries(modules)) {
  const [, , id] = path.split('/');
  ui[id] = module.default ?? module;
}

for (const [path, messages] of Object.entries(locales)) {
  const parts = path.split('/');
  const id = parts[2];
  const lang = parts[4].replace('.json', '');
  addMessages(lang, `plugin.${id}`, messages);
}

export const plugins = $state({ list: [], loaded: false });

export async function loadPlugins() {
  try {
    const result = await api.plugins();
    plugins.list = result.plugins;
  } catch {
    plugins.list = [];
  } finally {
    plugins.loaded = true;
  }
}

export function setPlugins(list) {
  plugins.list = list;
}

export const activePlugins = () => plugins.list.filter((plugin) => plugin.active);

export function hasUi(pluginId) {
  return pluginId in ui;
}

export function questionnaireBlocks() {
  return activePlugins().flatMap((plugin) =>
    plugin.questionnaire_blocks
      .map((block) => ({ pluginId: plugin.id, blockId: block, component: ui[plugin.id]?.questionnaireBlocks?.[block] }))
      .filter((block) => block.component),
  );
}

export function reportSections() {
  return activePlugins().flatMap((plugin) =>
    plugin.report_sections
      .map((section) => ({
        pluginId: plugin.id,
        sectionId: section,
        component: ui[plugin.id]?.reportSections?.[section],
      }))
      .filter((section) => section.component),
  );
}

export function widgets() {
  return activePlugins().flatMap((plugin) =>
    plugin.widgets
      .map((widget) => ({ pluginId: plugin.id, widgetId: widget, component: ui[plugin.id]?.widgets?.[widget] }))
      .filter((widget) => widget.component),
  );
}

export function pageComponent(pluginId, page) {
  const plugin = activePlugins().find((item) => item.id === pluginId);
  if (!plugin || !plugin.pages.includes(page)) return null;
  return ui[pluginId]?.pages?.[page] ?? null;
}

export function settingsPanel(pluginId) {
  const plugin = activePlugins().find((item) => item.id === pluginId);
  return plugin?.settings ? ui[pluginId]?.settingsPanel ?? null : null;
}

function entryLabel(plugin, entry) {
  const key = `plugin.${plugin.id}.entry.${entry.id}`;
  return has(key) ? t(key) : entry.label;
}

export function allEntries() {
  return activePlugins().flatMap((plugin) =>
    plugin.entries
      .filter((entry) => ui[plugin.id]?.pages?.[entry.page])
      .map((entry) => ({
        key: `${plugin.id}:${entry.id}`,
        pluginId: plugin.id,
        label: entryLabel(plugin, entry),
        icon: entry.icon in icons ? entry.icon : 'plug',
        placement: entry.placement,
        href: `/p/${plugin.id}/${entry.page}`,
      })),
  );
}

export function dockEntries() {
  const room = MAX_DOCK_ENTRIES - CORE_DOCK_ENTRIES;
  return allEntries()
    .filter((entry) => entry.placement === 'dock')
    .slice(0, Math.max(room, 0));
}

export function moreEntries() {
  const inDock = new Set(dockEntries().map((entry) => entry.key));
  return allEntries().filter((entry) => !inDock.has(entry.key));
}
