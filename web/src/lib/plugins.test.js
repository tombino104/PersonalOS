import { beforeEach, describe, expect, it } from 'vitest';
import {
  allEntries,
  dockEntries,
  hasUi,
  moreEntries,
  pageComponent,
  questionnaireBlocks,
  reportSections,
  setPlugins,
  widgets,
} from './plugins.svelte.js';

const base = {
  version: '0.1.0',
  description: '',
  permissions: [],
  questionnaire_blocks: [],
  widgets: [],
  pages: [],
  entries: [],
  report_sections: [],
  settings: false,
  state: 'active',
};

describe('plugin helpers', () => {
  beforeEach(() => setPlugins([]));

  it('bundles the interface of the example plugin', () => {
    expect(hasUi('example')).toBe(true);
    expect(hasUi('nothing')).toBe(false);
  });

  it('offers questionnaire blocks only for active plugins that ship them', () => {
    setPlugins([{ ...base, id: 'example', name: 'Example', active: true, questionnaire_blocks: ['gratitude'] }]);
    expect(questionnaireBlocks().map((block) => block.blockId)).toEqual(['gratitude']);
    setPlugins([{ ...base, id: 'example', name: 'Example', active: false, questionnaire_blocks: ['gratitude'] }]);
    expect(questionnaireBlocks()).toEqual([]);
  });

  it('bundles the mood plugin interface with its block, report section and page', () => {
    const mood = {
      ...base,
      id: 'mood',
      name: 'Mood tracker',
      active: true,
      questionnaire_blocks: ['mood'],
      report_sections: ['mood'],
      pages: ['trend'],
      entries: [{ id: 'mood', label: 'Mood', icon: 'smile', placement: 'more', page: 'trend' }],
    };
    setPlugins([mood]);
    expect(questionnaireBlocks().map((block) => block.blockId)).toEqual(['mood']);
    expect(reportSections().map((section) => section.sectionId)).toEqual(['mood']);
    expect(pageComponent('mood', 'trend')).not.toBeNull();
    expect(allEntries().map((entry) => entry.href)).toEqual(['/p/mood/trend']);
    expect(dockEntries()).toEqual([]);
    expect(moreEntries().map((entry) => entry.label)).toEqual(['Mood']);
    setPlugins([{ ...mood, active: false }]);
    expect(reportSections()).toEqual([]);
    expect(allEntries()).toEqual([]);
  });

  it('puts an entry in the dock only when it asks for it and there is room', () => {
    setPlugins([
      {
        ...base,
        id: 'mood',
        name: 'Mood tracker',
        active: true,
        pages: ['trend'],
        entries: [{ id: 'mood', label: 'Mood', icon: 'smile', placement: 'dock', page: 'trend' }],
      },
    ]);
    expect(dockEntries()).toHaveLength(1);
    expect(moreEntries()).toEqual([]);
  });

  it('ignores blocks the interface does not provide', () => {
    setPlugins([{ ...base, id: 'example', name: 'Example', active: true, questionnaire_blocks: ['unknown'] }]);
    expect(questionnaireBlocks()).toEqual([]);
  });

  it('has no widgets, pages or entries without a matching interface', () => {
    setPlugins([
      {
        ...base,
        id: 'example',
        name: 'Example',
        active: true,
        widgets: ['w'],
        pages: ['p'],
        entries: [{ id: 'e', label: 'E', icon: 'plug', placement: 'dock', page: 'p' }],
      },
    ]);
    expect(widgets()).toEqual([]);
    expect(reportSections()).toEqual([]);
    expect(pageComponent('example', 'p')).toBeNull();
    expect(allEntries()).toEqual([]);
    expect(dockEntries()).toEqual([]);
    expect(moreEntries()).toEqual([]);
  });
});
