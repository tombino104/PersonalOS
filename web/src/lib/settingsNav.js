export const LEGACY = {
  mascot: ['account', 'mascot'],
  backups: ['account', 'backups'],
  dock: ['appearance', 'dock'],
  guide: ['help', 'guide'],
  community: ['help', 'community'],
};

export function resolveSettings(path, tabs, legacy = LEGACY) {
  const [, , tabId, sectionId] = path.split('/');
  const old = legacy[tabId];
  if (old) return { tab: null, section: null, redirect: `/settings/${old[0]}/${old[1]}` };
  const tab = tabs.find((item) => item.id === tabId);
  if (!tab) return null;
  const section = tab.sections.find((item) => item.id === sectionId) ?? tab.sections[0];
  return { tab, section, redirect: null };
}
