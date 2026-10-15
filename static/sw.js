const CACHE='pocket-shell-__BUILD_ID__';
const SHELL=__SHELL_JSON__;
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>Promise.all(SHELL.map(url=>fetch(url,{cache:'reload'}).then(r=>{if(!r.ok)throw new Error('Shell unavailable');return c.put(url,r);})))));self.skipWaiting();});
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('pocket-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const url=new URL(e.request.url);if(e.request.method!=='GET'||url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;const key=url.pathname+url.search;if(!SHELL.includes(key))return;e.respondWith(fetch(e.request).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(c=>c.put(key,copy));}return response;}).catch(()=>caches.match(key)));});
