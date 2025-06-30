// Service Worker für Offline-Funktionalität
const CACHE_NAME = 'scandy-v1';
const CACHE_URLS = [
    '/',
    '/static/css/tailwind.css',
    '/static/js/scanner.js',
    '/static/images/scandy-favicon.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(CACHE_URLS))
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
}); 