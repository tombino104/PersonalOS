import en from '../locales/en.json';
import it from '../locales/it.json';

const dictionaries = { en, it };
const STORAGE_KEY = 'personal-os-language';

function read() {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? 'auto';
  } catch {
    return 'auto';
  }
}

function resolve(preference) {
  if (preference in dictionaries) return preference;
  const browser = (typeof navigator === 'undefined' ? 'en' : navigator.language ?? 'en').toLowerCase();
  return browser.startsWith('it') ? 'it' : 'en';
}

export const i18n = $state({ preference: read(), lang: resolve(read()) });

export function applyLanguage() {
  document.documentElement.lang = i18n.lang;
}

export function setLanguage(preference) {
  i18n.preference = preference;
  i18n.lang = resolve(preference);
  try {
    if (preference === 'auto') localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, preference);
  } catch {
  }
  applyLanguage();
}

export function t(key, params = {}) {
  const text = dictionaries[i18n.lang][key] ?? dictionaries.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? ''));
}

export function has(key) {
  return key in dictionaries[i18n.lang] || key in dictionaries.en;
}

export function locale() {
  return i18n.lang === 'it' ? 'it-IT' : 'en-GB';
}
