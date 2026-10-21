const browser = typeof window !== 'undefined';
const base = (import.meta.env?.BASE_URL ?? '/').replace(/\/$/, '');

export function normalize(pathname) {
  return pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
}

export const withBase = (path) => base + path;

function currentPath() {
  const path = normalize(location.pathname);
  if (base && (path === base || path.startsWith(`${base}/`))) return path.slice(base.length) || '/';
  return path;
}

export const router = $state({
  path: browser ? currentPath() : '/',
  query: new URLSearchParams(browser ? location.search : ''),
});

function sync() {
  router.path = currentPath();
  router.query = new URLSearchParams(location.search);
}

export function navigate(to, { replace = false } = {}) {
  const url = new URL(to, location.origin);
  const target = withBase(url.pathname) + url.search;
  if (replace) history.replaceState(null, '', target);
  else history.pushState(null, '', target);
  sync();
  window.scrollTo(0, 0);
}

if (browser) window.addEventListener('popstate', sync);
