/* Quran PWA service worker — offline app shell + cache-first assets/data */
'use strict';

const VER = 'qr-pwa-v7';
const SHELL = [
  './index.html',
  './manifest.json',
  './assets/icon-192.png',
  './assets/icon-512.png',
  './assets/maskable-192.png',
  './assets/maskable-512.png',
  './assets/favicon-32.png',
  './assets/apple-touch-icon.png',
  './assets/icon.svg',
  './assets/meta.json',           // bundled surah metadata (offline-ready at install)
  './assets/editions.json'        // bundled translations list
];

const SAME = VER + '-same';   // app shell + same-origin assets
const FONT = VER + '-font';   // Google Fonts
const DATA = VER + '-data';   // api.alquran.cloud
const AUDIO = VER + '-audio'; // cdn.islamic.network + everyayah.com
const AUDIO_MAX = 300;        // cap cached audio files (evict oldest)

/* ---------- install: precache the app shell ---------- */
addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(SAME);
    // Precache individually so one missing file can't break the whole install.
    await Promise.allSettled(SHELL.map(u => c.add(u)));
    await self.skipWaiting();
  })());
});

/* ---------- activate: drop stale caches, take over now ---------- */
addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys
      .filter(k => !k.startsWith(VER))
      .map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

/* ---------- helpers ---------- */
const isNav = r => r.mode === 'navigate';
const lru = async (cache, limit) => {
  const reqs = await cache.keys();
  if (reqs.length <= limit) return;
  // keys() is oldest-first — delete the surplus from the front
  await Promise.all(reqs.slice(0, reqs.length - limit).map(r => cache.delete(r)));
};

/* network-first for navigations (fresh HTML when online, shell when offline) */
async function nav(req) {
  try {
    const res = await fetch(req);
    const c = await caches.open(SAME);
    c.put(req, res.clone());
    return res;
  } catch {
    const c = await caches.open(SAME);
    const hit = await c.match(req) || await c.match('./index.html');
    return hit || Response.error();
  }
}

/* stale-while-revalidate: serve cache instantly, refresh in background */
async function swr(req, cacheName, cap) {
  const c = await caches.open(cacheName);
  const hit = await c.match(req);
  const refresh = fetch(req).then(res => {
    if (res && res.ok && res.type !== 'opaque') {
      c.put(req, res.clone());
      if (cap) lru(c, cap).catch(() => {});
    }
    return res;
  }).catch(() => hit);
  return hit || refresh;
}

/* cache-first with network fallback (for opaque cross-origin fonts CSS) */
async function cf(req, cacheName) {
  const c = await caches.open(cacheName);
  const hit = await c.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res && (res.ok || res.type === 'opaque')) c.put(req, res.clone());
  return res;
}

addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET') return;

  const url = new URL(r.url);

  if (isNav(r)) { e.respondWith(nav(r)); return; }

  // Google Fonts: css (cache-first) + font files (SWR, long-lived)
  if (url.hostname === 'fonts.googleapis.com') { e.respondWith(cf(r, FONT)); return; }
  if (url.hostname === 'fonts.gstatic.com') { e.respondWith(swr(r, FONT)); return; }

  // Quran text API
  if (url.hostname === 'api.alquran.cloud') { e.respondWith(swr(r, DATA)); return; }

  // Recitation MP3s (remote CDNs) — cache-first so playback works offline,
  // capped in size. Bundled recitations under assets/audio/ are NOT cached
  // here: they are served from disk by the server and are already shared
  // with everyone on the network.
  if (url.hostname === 'cdn.islamic.network') { e.respondWith(swr(r, AUDIO, AUDIO_MAX)); return; }
  if (url.hostname === 'everyayah.com') { e.respondWith(swr(r, AUDIO, AUDIO_MAX)); return; }

  // Bundled recitations and Quran text: stream straight from the server, no
  // browser cache. The server's disk is the single shared copy; a device that
  // wants its own offline copy uses the in-app Downloads manager (IndexedDB).
  if (url.pathname.startsWith('/assets/audio/') ||
      url.pathname.startsWith('/assets/pages/')) return;

  // Same-origin static assets (icons etc.)
  if (url.origin === location.origin) { e.respondWith(swr(r, SAME)); return; }
});

/* allow the page to trigger an immediate update */
addEventListener('message', e => {
  if (e.data === 'skipWaiting') self.skipWaiting();
});
