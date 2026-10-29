import { describe, expect, it } from 'vitest';
import { LEGACY, resolveSettings } from './settingsNav.js';

const tabs = [
  { id: 'activities', sections: [{ id: 'main' }] },
  { id: 'account', sections: [{ id: 'login' }, { id: 'mascot' }, { id: 'backups' }] },
  { id: 'appearance', sections: [{ id: 'look' }, { id: 'dock' }] },
  { id: 'help', sections: [{ id: 'guide' }, { id: 'community' }] },
];

describe('resolveSettings', () => {
  it('opens the first section of a tab by default', () => {
    const place = resolveSettings('/settings/account', tabs);
    expect(place.tab.id).toBe('account');
    expect(place.section.id).toBe('login');
  });

  it('opens a named section', () => {
    expect(resolveSettings('/settings/account/backups', tabs).section.id).toBe('backups');
    expect(resolveSettings('/settings/help/community', tabs).section.id).toBe('community');
  });

  it('falls back to the first section when the section is unknown', () => {
    expect(resolveSettings('/settings/appearance/nope', tabs).section.id).toBe('look');
  });

  it('knows nothing about an unknown tab', () => {
    expect(resolveSettings('/settings', tabs)).toBeNull();
    expect(resolveSettings('/settings/nope', tabs)).toBeNull();
  });

  it('sends the old addresses to their new place', () => {
    expect(resolveSettings('/settings/mascot', tabs).redirect).toBe('/settings/account/mascot');
    expect(resolveSettings('/settings/backups', tabs).redirect).toBe('/settings/account/backups');
    expect(resolveSettings('/settings/dock', tabs).redirect).toBe('/settings/appearance/dock');
    expect(resolveSettings('/settings/guide', tabs).redirect).toBe('/settings/help/guide');
    expect(resolveSettings('/settings/community', tabs).redirect).toBe('/settings/help/community');
  });

  it('only redirects to places that exist', () => {
    for (const [tabId, sectionId] of Object.values(LEGACY)) {
      const place = resolveSettings(`/settings/${tabId}/${sectionId}`, tabs);
      expect(place.section.id).toBe(sectionId);
    }
  });
});
