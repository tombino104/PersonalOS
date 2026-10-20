const STORAGE_KEY = 'personal-os-theme';
const MODES = ['light', 'dark', 'auto'];

function read() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return MODES.includes(stored) ? stored : 'auto';
  } catch {
    return 'auto';
  }
}

export const theme = $state({ mode: read() });

export function applyTheme() {
  const root = document.documentElement;
  if (theme.mode === 'auto') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', theme.mode);
}

export function setTheme(mode) {
  theme.mode = mode;
  try {
    if (mode === 'auto') localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, mode);
  } catch {
  }
  applyTheme();
}
