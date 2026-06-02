const SHELL_CACHE = 'mmc-shell-v1';
const DATA_CACHE = 'mmc-data-v1';
const SHELL_FILES = ['/static/mission_control_v2.html'];

self.addEventListener('install', evt => {
  evt.waitUntil(caches.open(SHELL_CACHE).then(c => c.addAll(SHELL_FILES)));
  self.skipWaiting();
});
self.addEventListener('activate', evt => { evt.waitUntil(clients.claim()); });
self.addEventListener('fetch', evt => {
  const url = new URL(evt.request.url);
  if (/socrata|\.gov\/resource|\/api\//.test(url.href)) {
    evt.respondWith(
      caches.open(DATA_CACHE).then(cache =>
        fetch(evt.request).then(res => { cache.put(evt.request, res.clone()); return res; })
          .catch(() => cache.match(evt.request))
      )
    );
  } else {
    evt.respondWith(caches.match(evt.request).then(r => r || fetch(evt.request)));
  }
});
