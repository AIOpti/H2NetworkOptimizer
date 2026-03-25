// OptiFLO AI — Service Worker for PWA offline support
const CACHE_NAME = 'optiflo-v2';
const ASSETS = ['/', '/index.html'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/') || e.request.url.includes('groq.com')) {
    // Network-only for API calls, fallback to cache on failure
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
  } else {
    // Stale-while-revalidate for static assets
    e.respondWith(
      caches.match(e.request).then(cached => {
        const fetched = fetch(e.request).then(res => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
          return res;
        });
        return cached || fetched;
      })
    );
  }
});
