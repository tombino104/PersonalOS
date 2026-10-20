export function normalize(pathname) {
  return pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
}

export const router = $state({
  path: normalize(location.pathname),
  query: new URLSearchParams(location.search),
});

function sync() {
  router.path = normalize(location.pathname);
  router.query = new URLSearchParams(location.search);
}

export function navigate(to, { replace = false } = {}) {
  const url = new URL(to, location.origin);
  const target = url.pathname + url.search;
  if (replace) history.replaceState(null, '', target);
  else history.pushState(null, '', target);
  sync();
  window.scrollTo(0, 0);
}

window.addEventListener('popstate', sync);
