/**
 * mox Service Worker — Cache-first strategy for offline PWA support.
 *
 * Caches:
 *   - The main HTML page (/)
 *   - Self-hosted font files (/fonts/*.woff2)
 *
 * Strategy:
 *   - On install: pre-cache all assets
 *   - On fetch: serve from cache first, fall back to network
 *   - On activate: clean up old cache versions
 *
 * Note: API routes (/api/*, /sw.js itself) are always network-only.
 */

const CACHE_NAME = 'mox-v2';

const PRECACHE_URLS = [
  '/',
  '/fonts/dm_serif_display_regular.woff2',
  '/fonts/dm_serif_display_italic.woff2',
  '/fonts/space_mono_regular_400.woff2',
  '/fonts/space_mono_italic_400.woff2',
  '/fonts/space_mono_bold_700.woff2',
];

// Routes that must always hit the network (never serve stale data)
const NETWORK_ONLY = [
  '/api/',
  '/sw.js',
  '/manifest.webmanifest',
];

function isNetworkOnly(url) {
  const path = new URL(url).pathname;
  return NETWORK_ONLY.some(prefix => path.startsWith(prefix));
}

// ── Install: pre-cache all known assets ───────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      // Individual fetch so one failure doesn't abort the whole install
      return Promise.allSettled(
        PRECACHE_URLS.map(url =>
          cache.add(url).catch(err => {
            console.warn(`[sw] failed to cache ${url}:`, err);
          })
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// ── Activate: delete old caches ───────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: cache-first for assets, network-only for API ───────────────────────
self.addEventListener('fetch', (event) => {
  // Only intercept same-origin GET requests
  if (event.request.method !== 'GET') return;
  if (!event.request.url.startsWith(self.location.origin)) return;
  if (isNetworkOnly(event.request.url)) return;

  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;

      // Not in cache — fetch from network and cache the response
      return fetch(event.request).then(response => {
        // Only cache valid responses
        if (!response || response.status !== 200 || response.type === 'opaque') {
          return response;
        }
        const toCache = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, toCache));
        return response;
      }).catch(() => {
        // Offline fallback for navigation requests
        if (event.request.mode === 'navigate') {
          return caches.match('/');
        }
        return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
      });
    })
  );
});
