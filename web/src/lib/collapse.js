const PREFIX = 'pos-open:';

export function isOpen(key) {
  try {
    return localStorage.getItem(PREFIX + key) === '1';
  } catch {
    return false;
  }
}

export function setOpen(key, open) {
  try {
    if (open) localStorage.setItem(PREFIX + key, '1');
    else localStorage.removeItem(PREFIX + key);
  } catch {
  }
}
