import { api } from './api.js';
import { i18n, setLanguage } from './i18n.svelte.js';
import { syncText } from './reminder.js';
import { setTheme, theme } from './theme.svelte.js';

export async function syncAppearance() {
  try {
    const saved = await api.settings();
    const missing = {};
    if (saved.theme) setTheme(saved.theme);
    else missing.theme = theme.mode;
    if (saved.language) setLanguage(saved.language);
    else missing.language = i18n.preference;
    if (Object.keys(missing).length) await api.updateSettings(missing);
  } catch {
  }
}

export function forgetLocalAppearance() {
  try {
    localStorage.removeItem('personal-os-theme');
    localStorage.removeItem('personal-os-language');
  } catch {
  }
}

export function saveTheme(mode) {
  setTheme(mode);
  api.updateSettings({ theme: mode }).catch(() => {});
}

export function saveLanguage(language) {
  setLanguage(language);
  api.updateSettings({ language }).catch(() => {});
  syncText();
}
