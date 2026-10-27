import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import en from './en.json';
import it_ from './it.json';

const placeholders = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();

function sources(directory) {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) return name === 'plugin-ui' ? [] : sources(path);
    return /\.(svelte|js)$/.test(name) && !name.endsWith('.test.js') ? [path] : [];
  });
}

describe('locales', () => {
  it('have the same keys in both languages', () => {
    expect(Object.keys(it_).sort()).toEqual(Object.keys(en).sort());
  });

  it('use the same placeholders in both languages', () => {
    for (const key of Object.keys(en)) {
      expect(placeholders(it_[key]), key).toEqual(placeholders(en[key]));
    }
  });

  it('have no empty strings', () => {
    for (const [key, value] of [...Object.entries(en), ...Object.entries(it_)]) {
      expect(value.trim(), key).not.toBe('');
    }
  });

  it('contain every key used in the code', () => {
    const used = new Set();
    for (const file of sources(join(import.meta.dirname, '..'))) {
      const text = readFileSync(file, 'utf8');
      for (const match of text.matchAll(/\bt\(\s*['"]([\w.]+)['"]/g)) used.add(match[1]);
      for (const match of text.matchAll(/'((?:nav|settings)\.[\w]+)'/g)) used.add(match[1]);
    }
    const missing = [...used].filter((key) => !(key in en));
    expect(missing).toEqual([]);
  });

  it('have a name for every area', () => {
    for (const area of ['physical', 'discipline', 'social', 'intellect', 'career', 'mindset']) {
      expect(en[`area.${area}`]).toBeTruthy();
      expect(it_[`area.${area}`]).toBeTruthy();
    }
  });
});

describe('dynamic keys', () => {
  it('cover every plugin state and permission', () => {
    const states = ['active', 'off', 'inactive', 'error', 'broken', 'invalid', 'incompatible', 'missing'];
    const permissions = [
      'read_activities',
      'read_reports',
      'read_scores',
      'questionnaire_block',
      'ui_panel',
      'api_routes',
      'listen_events',
      'ingest',
      'request_reminder',
    ];
    for (const state of states) expect(en[`plugins.state.${state}`], state).toBeTruthy();
    for (const permission of permissions) {
      expect(en[`permission.${permission}`], permission).toBeTruthy();
      expect(it_[`permission.${permission}`], permission).toBeTruthy();
    }
  });
});

describe('plugin locales', () => {
  const root = join(import.meta.dirname, '..', '..', '..', 'plugins');
  const ids = readdirSync(root).filter((name) => statSync(join(root, name)).isDirectory());

  function load(id, lang) {
    const path = join(root, id, 'ui', 'locales', `${lang}.json`);
    return JSON.parse(readFileSync(path, 'utf8'));
  }

  it.each(ids)('%s has the same keys in English and Italian', (id) => {
    const english = load(id, 'en');
    const italian = load(id, 'it');
    const optional = new Set(['name', 'description']);
    const required = (data) => Object.keys(data).filter((key) => !optional.has(key)).sort();
    expect(required(italian)).toEqual(required(english));
  });

  it.each(ids)('%s defines every key it uses', (id) => {
    const english = load(id, 'en');
    const uiDirectory = join(root, id, 'ui');
    const used = new Set();
    for (const file of sources(uiDirectory)) {
      const text = readFileSync(file, 'utf8');
      for (const match of text.matchAll(/\bt\(\s*['"]([\w.]+)['"]/g)) {
        const prefix = `plugin.${id}.`;
        if (match[1].startsWith(prefix)) used.add(match[1].slice(prefix.length));
      }
    }
    const missing = [...used].filter((key) => !(key in english));
    expect(missing).toEqual([]);
  });
});
