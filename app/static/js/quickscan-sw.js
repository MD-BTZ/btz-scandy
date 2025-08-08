// Service Worker für Scandy Quickscan PWA
const CACHE_NAME = 'scandy-quickscan-v2';
const urlsToCache = [
  '/mobile/quickscan',
  '/static/css/quickscan.css',
  '/static/js/quickscan.js',
  '/static/images/scandy-logo.png',
  '/static/images/scandy-favicon.png',
  'https://cdn.jsdelivr.net/npm/daisyui@4.10.2/dist/full.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css'
];

// Install Event
self.addEventListener('install', function(event) {
  console.log('Service Worker: Install');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Service Worker: Caching Files');
        return cache.addAll(urlsToCache);
      })
      .then(function() {
        console.log('Service Worker: Files Cached');
        return self.skipWaiting();
      })
  );
});

// Activate Event
self.addEventListener('activate', function(event) {
  console.log('Service Worker: Activate');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Clearing Old Cache');
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim();
});

// Fetch Event
self.addEventListener('fetch', function(event) {
  // Nur GET-Requests cachen
  if (event.request.method !== 'GET') {
    return;
  }

  // API-Calls nicht cachen
  if (event.request.url.includes('/mobile/scan') || 
      event.request.url.includes('/mobile/lend') ||
      event.request.url.includes('/mobile/login')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Cache hit - return response
        if (response) {
          return response;
        }

        // Nicht im Cache - vom Netzwerk holen
        return fetch(event.request)
          .then(function(response) {
            // Prüfe ob gültige Response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Response klonen
            var responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then(function(cache) {
                cache.put(event.request, responseToCache);
              });

            return response;
          })
          .catch(function() {
            // Fallback für Offline-Modus
            if (event.request.destination === 'document') {
              return caches.match('/mobile/quickscan');
            }
          });
      })
  );
});

// Background Sync (falls unterstützt)
self.addEventListener('sync', function(event) {
  if (event.tag === 'background-sync') {
    console.log('Service Worker: Background Sync');
    event.waitUntil(doBackgroundSync());
  }
});

function doBackgroundSync() {
  // Hier können Offline-Aktionen synchronisiert werden
  console.log('Background Sync ausgeführt');
}

// Push Notifications (falls benötigt)
self.addEventListener('push', function(event) {
  console.log('Service Worker: Push Event');
  
  const options = {
    body: event.data ? event.data.text() : 'Neue Nachricht von Scandy',
    icon: '/static/images/scandy-favicon.png',
    badge: '/static/images/scandy-favicon.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Öffnen',
        icon: '/static/images/scandy-favicon.png'
      },
      {
        action: 'close',
        title: 'Schließen',
        icon: '/static/images/scandy-favicon.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Scandy Quickscan', options)
  );
});

// Notification Click
self.addEventListener('notificationclick', function(event) {
  console.log('Service Worker: Notification Click');
  
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/mobile/quickscan')
    );
  }
}); 