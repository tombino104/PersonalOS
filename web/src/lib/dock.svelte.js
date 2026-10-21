import { api } from './api.js';
import { addKey, moveKey, removeKey, resolveKeys } from './dock.js';
import { allEntries, dockEntries } from './plugins.svelte.js';

export const dockState = $state({ saved: null });

const CORE_ITEMS = [
  { key: 'home', href: '/', icon: 'home', labelKey: 'nav.home', match: (path) => path === '/' },
  { key: 'stella', href: '/stella', icon: 'star', labelKey: 'nav.stella', match: (path) => path === '/stella' },
  {
    key: 'questionnaire',
    href: '/questionnaire',
    icon: 'pencil',
    labelKey: 'nav.questionnaire',
    main: true,
    match: (path) => path.startsWith('/questionnaire'),
  },
  {
    key: 'more',
    href: '/more',
    icon: 'more',
    labelKey: 'nav.more',
    match: (path) => ['/more', '/archive'].includes(path) || path.startsWith('/settings'),
  },
];

export async function loadDock() {
  try {
    const settings = await api.settings();
    dockState.saved = settings.dock ?? null;
  } catch {
  }
}

function availableItems() {
  return [
    ...CORE_ITEMS,
    ...allEntries().map((entry) => ({
      key: entry.key,
      href: entry.href,
      icon: entry.icon,
      text: entry.label,
      match: (path) => path.startsWith(`/p/${entry.pluginId}/`),
    })),
  ];
}

export function dockLayout() {
  const items = availableItems();
  const byKey = new Map(items.map((item) => [item.key, item]));
  const keys = resolveKeys(
    dockState.saved,
    new Set(byKey.keys()),
    dockEntries().map((entry) => entry.key),
  );
  const inDock = keys.map((key) => byKey.get(key));
  const shown = new Set(keys);
  return { keys, inDock, outOfDock: items.filter((item) => !shown.has(item.key)) };
}

async function persist(keys) {
  const before = dockState.saved;
  dockState.saved = keys;
  try {
    await api.updateSettings({ dock: keys });
  } catch (error) {
    dockState.saved = before;
    throw error;
  }
}

export const addToDock = (key) => persist(addKey(dockLayout().keys, key));
export const removeFromDock = (key) => persist(removeKey(dockLayout().keys, key));
export const moveInDock = (key, delta) => persist(moveKey(dockLayout().keys, key, delta));

export async function resetDock() {
  const before = dockState.saved;
  dockState.saved = null;
  try {
    await api.updateSettings({ dock: [] });
  } catch (error) {
    dockState.saved = before;
    throw error;
  }
}
