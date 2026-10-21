export const MAX_DOCK = 7;
export const FIXED_KEYS = ['questionnaire', 'more'];

export function defaultKeys(pluginKeys) {
  return ['home', 'stella', 'questionnaire', ...pluginKeys, 'more'];
}

export function resolveKeys(saved, available, pluginKeys) {
  if (!Array.isArray(saved) || saved.length === 0) {
    return defaultKeys(pluginKeys.filter((key) => available.has(key)));
  }
  const kept = [...new Set(saved)].filter((key) => key !== 'more' && available.has(key));
  if (!kept.includes('questionnaire')) kept.push('questionnaire');
  let list = kept.slice(0, MAX_DOCK - 1);
  if (!list.includes('questionnaire')) list = [...list.slice(0, MAX_DOCK - 2), 'questionnaire'];
  return [...list, 'more'];
}

export const isFull = (keys) => keys.length >= MAX_DOCK;

export function addKey(keys, key) {
  if (keys.includes(key) || isFull(keys)) return keys;
  return [...keys.slice(0, -1), key, 'more'];
}

export function removeKey(keys, key) {
  if (FIXED_KEYS.includes(key)) return keys;
  return keys.filter((item) => item !== key);
}

export function moveKey(keys, key, delta) {
  const list = keys.slice(0, -1);
  const from = list.indexOf(key);
  const to = from + delta;
  if (from === -1 || to < 0 || to >= list.length) return keys;
  [list[from], list[to]] = [list[to], list[from]];
  return [...list, 'more'];
}
