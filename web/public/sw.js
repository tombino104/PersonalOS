const CACHE = 'personal-os-shell-v1';
const SHELL = new URL('./', self.location).href;

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys()) {
        if (key !== CACHE) await caches.delete(key);
      }
      await self.clients.claim();
    })(),
  );
});

const TEXT_KEY = new URL('reminder-text.json', self.location).href;

self.addEventListener('push', (event) => {
  event.waitUntil(
    (async () => {
      let text = { title: 'Evening check-in', body: 'A quiet moment to tick what you did today.' };
      try {
        const hit = await (await caches.open(CACHE)).match(TEXT_KEY);
        if (hit) text = await hit.json();
      } catch {
      }
      await self.registration.showNotification(text.title, {
        body: text.body,
        icon: new URL('icon-192.png', self.location).href,
        badge: new URL('icon-192.png', self.location).href,
        tag: 'evening-reminder',
      });
    })(),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL('questionnaire', self.registration.scope).href;
  event.waitUntil(
    (async () => {
      const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const page of windows) {
        await page.focus();
        try {
          await page.navigate(target);
        } catch {
        }
        return;
      }
      await self.clients.openWindow(target);
    })(),
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.includes('/assets/')) {
    event.respondWith(
      (async () => {
        const cache = await caches.open(CACHE);
        const hit = await cache.match(request);
        if (hit) return hit;
        const response = await fetch(request);
        if (response.ok) cache.put(request, response.clone());
        return response;
      })(),
    );
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        const cache = await caches.open(CACHE);
        try {
          const response = await fetch(request);
          if (response.ok) cache.put(SHELL, response.clone());
          return response;
        } catch {
          return (await cache.match(SHELL)) ?? Response.error();
        }
      })(),
    );
  }
});
