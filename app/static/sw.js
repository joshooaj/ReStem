const CACHE_NAME = 'mux-minus-v1';
const STATIC_CACHE_NAME = 'mux-minus-static-v1';

// Assets to cache immediately on install
const PRECACHE_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/images/logo-horizontal.svg',
  '/static/images/logo-horizontal.png'
];

// Install event - cache essential assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then((cache) => {
        console.log('Caching essential assets');
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => self.skipWaiting())
      .catch((error) => {
        console.error('Failed to cache assets:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== STATIC_CACHE_NAME)
          .map((name) => {
            console.log('Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip API calls and form submissions - always go to network
  if (url.pathname.startsWith('/api/') || 
      url.pathname.includes('/login') || 
      url.pathname.includes('/register') ||
      url.pathname.includes('/logout')) {
    return;
  }

  // For static assets, use cache-first strategy
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(request).then((response) => {
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(STATIC_CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        });
      })
    );
    return;
  }

  // For pages, use network-first strategy
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache successful responses for pages
        if (response.ok && request.headers.get('accept')?.includes('text/html')) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Fallback to cache if network fails
        return caches.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Return offline page if available
          return caches.match('/');
        });
      })
  );
});
