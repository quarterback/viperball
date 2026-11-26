/* Viperball: installable shell, never cache simulation or session data. */
const CACHE_PREFIX = 'viperball-pwa-';
const CACHE = CACHE_PREFIX + 'v1';
const OFFLINE = '/stats/static/pwa/offline.html';
const SHELL = [OFFLINE, '/stats/pwa/icon-192.png', '/stats/pwa/icon-512.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)));
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k.startsWith(CACHE_PREFIX) && k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin ||
      !url.pathname.startsWith('/stats/')) return;
  // Do not intercept API calls, forms, save downloads, or mutable page data.
  if (req.mode === 'navigate' && req.destination === 'document') {
    event.respondWith(fetch(req, {cache: 'no-store'}).catch(async () => {
      const cache = await caches.open(CACHE);
      return (await cache.match(OFFLINE)) || new Response('Viperball is offline. Reconnect and try again.', {
        status: 503, headers: {'Content-Type': 'text/plain; charset=utf-8'}
      });
    }));
  } else if (SHELL.includes(url.pathname) && !url.search) {
    event.respondWith(caches.open(CACHE).then(async cache => (await cache.match(req)) || fetch(req)));
  }
});
