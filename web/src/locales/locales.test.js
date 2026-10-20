import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import en from './en.json';
import it_ from './it.json';

const placeholders = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();

function sources(directory) {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) return sources(path);
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
