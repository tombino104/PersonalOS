import { beforeEach, describe, expect, it } from 'vitest';
import { allEntries, dockEntries, hasUi, moreEntries, pageComponent, questionnaireBlocks, setPlugins, widgets } from './plugins.svelte.js';

const base = {
  version: '0.1.0',
  description: '',
  permissions: [],
  questionnaire_blocks: [],
  widgets: [],
  pages: [],
  entries: [],
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
    expect(pageComponent('example', 'p')).toBeNull();
    expect(allEntries()).toEqual([]);
    expect(dockEntries()).toEqual([]);
    expect(moreEntries()).toEqual([]);
  });
});
