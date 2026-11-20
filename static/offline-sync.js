/* Multi Plaza offline-first backup and sync layer.
   Keeps API data in IndexedDB, queues edits while offline, retries when online,
   and creates a dated local backup snapshot. */
(()=>{
'use strict';
const DB='multi-plaza-offline-v1', STORE='records', QUEUE='mp_offline_queue_v1';
let dbPromise;
function openDB(){if(dbPromise)return dbPromise;dbPromise=new Promise((resolve,reject)=>{const r=indexedDB.open(DB,1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains(STORE))r.result.createObjectStore(STORE)};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});return dbPromise}
async function put(k,v){const d=await openDB();return new Promise((res,rej)=>{const t=d.transaction(STORE,'readwrite');t.objectStore(STORE).put(v,k);t.oncomplete=()=>res();t.onerror=()=>rej(t.error)})}
async function get(k){const d=await openDB();return new Promise((res,rej)=>{const r=d.transaction(STORE).objectStore(STORE).get(k);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)})}
function queue(){try{return JSON.parse(localStorage.getItem(QUEUE)||'[]')}catch(_){return []}}
function setQueue(q){localStorage.setItem(QUEUE,JSON.stringify(q));status()}
 async function clearApiCache(){try{const d=await openDB();await new Promise((res,rej)=>{const tx=d.transaction(STORE,'readwrite'),st=tx.objectStore(STORE),req=st.openCursor();req.onsuccess=()=>{const cur=req.result;if(cur){if(String(cur.key).startsWith('cache:/api/'))cur.delete();cur.continue();}};tx.oncomplete=res;tx.onerror=()=>rej(tx.error);});}catch(_){}}
 function clearLegacySectionQueue(){try{const q=queue(),safe=q.filter(m=>!String(m.url||'').startsWith('/api/data/'));if(safe.length!==q.length)setQueue(safe);}catch(_){}}

function status(){let n=queue().length;let el=document.getElementById('mpOfflineStatus');if(!el){el=document.createElement('div');el.id='mpOfflineStatus';el.style.cssText='position:fixed;right:12px;bottom:12px;z-index:99999;padding:8px 12px;border-radius:20px;background:#173b68;color:white;font:12px Arial;box-shadow:0 2px 8px #0003';document.body.appendChild(el)}el.textContent=!navigator.onLine?`Offline • ${n} pending change(s)`:n?`Sync pending • ${n}`:'Online • Synced';el.title='Offline changes are stored on this device and will sync when connection returns.'}
function key(url){return 'cache:'+url}
const nativeFetch=window.fetch.bind(window);
window.fetch=async function(input,init={}){
 const req=input instanceof Request?input:null;const url=new URL(req?req.url:input,location.href);const method=(init.method||(req&&req.method)||'GET').toUpperCase();
 if(url.origin!==location.origin||!url.pathname.startsWith('/api/'))return nativeFetch(input,init);
 const cacheKey=key(url.pathname+url.search);
 if(method==='GET'){
  try{
   const r=await nativeFetch(input,init);
   if(r.ok){const clone=r.clone();clone.json().then(v=>put(cacheKey,v)).catch(()=>{});}
   return r;
  }catch(e){
   // Do not serve stale register snapshots after server-side deletion.
   return new Response(JSON.stringify({ok:false,offline:true,error:'Server unavailable. Live data was not loaded; reconnect and refresh.'}),{status:503,headers:{'Content-Type':'application/json','X-Offline-No-Stale-Data':'1'}});
  }
 }
 if(['PUT','POST','DELETE'].includes(method)){
  let body=init.body!==undefined?init.body:(req?await req.clone().text():undefined);let headers=new Headers(init.headers||(req&&req.headers)||{});headers.set('Content-Type',headers.get('Content-Type')||'application/json');
  let parsed=null;try{if(typeof body==='string')parsed=JSON.parse(body)}catch(_){}
  if(method==='POST'&&url.pathname==='/api/customers'&&parsed){parsed.id=parsed.id||('offline-'+(crypto.randomUUID?crypto.randomUUID():Date.now()+'-'+Math.random().toString(16).slice(2)));body=JSON.stringify(parsed)}
  const mutation={url:url.pathname+url.search,method,body:body||null,headers:[...headers.entries()],createdAt:new Date().toISOString()};
  try{
    const r=await nativeFetch(url.toString(),{...init,method,body,headers});
    if(!r.ok)throw new Error('Server returned '+r.status);
    if(method==='PUT'&&url.pathname.startsWith('/api/data/')){try{await put(key(url.pathname),parsed)}catch(_){}}
    if(method==='DELETE')await clearApiCache();
    return r;
   }
  catch(err){
   // Full-section snapshots are unsafe to replay after another device edits/deletes data.
   // Keep offline section changes local instead of silently overwriting shared records later.
   if(url.pathname.startsWith('/api/data/')){
    return new Response(JSON.stringify({ok:false,offline:true,error:'Not synced: reconnect and review this section before saving.'}),{status:503,headers:{'Content-Type':'application/json','X-Offline-Local-Only':'1'}});
   }
   const q=queue();q.push(mutation);setQueue(q);
   if(method==='POST'&&url.pathname==='/api/customers'&&parsed)return new Response(JSON.stringify(parsed),{status:201,headers:{'Content-Type':'application/json','X-Offline-Queued':'1'}});
   return new Response(JSON.stringify({ok:true,offlineQueued:true}),{status:200,headers:{'Content-Type':'application/json','X-Offline-Queued':'1'}})
  }
 }
 return nativeFetch(input,init)
};
async function sync(){
 if(!navigator.onLine)return;
 // Discard legacy queued full-register snapshots; they may predate other-device edits/deletes.
 let q=queue();
 const safeQueue=q.filter(m=>!String(m.url||'').startsWith('/api/data/'));
 if(safeQueue.length!==q.length){q=safeQueue;setQueue(q);}
 if(!q.length){status();return}
 let remaining=[];
 for(const m of q){try{const r=await nativeFetch(m.url,{method:m.method,headers:new Headers(m.headers),body:m.method==='GET'||m.method==='DELETE'?undefined:m.body});if(!r.ok)throw Error('HTTP '+r.status)}catch(e){remaining.push(m)}}
 setQueue(remaining);if(!remaining.length){window.dispatchEvent(new CustomEvent('mp-sync-complete'));}
}
function dailySnapshot(){try{const day=new Date().toISOString().slice(0,10);const old=localStorage.getItem('mp_last_backup_day');if(old===day)return;const snap={createdAt:new Date().toISOString(),note:'Automatic local snapshot of browser-stored Multi Plaza data',localStorage:{}};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&(/multiPlaza|mp_|quotation/i.test(k)))snap.localStorage[k]=localStorage.getItem(k)}localStorage.setItem('mp_backup_'+day,JSON.stringify(snap));localStorage.setItem('mp_last_backup_day',day)}catch(_){}}
window.addEventListener('online',()=>{sync();status()});window.addEventListener('offline',status);window.addEventListener('load',()=>{dailySnapshot();status();clearLegacySectionQueue();clearApiCache();sync();if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});});setInterval(()=>{if(navigator.onLine)sync()},15000);
window.MultiPlazaBackup={sync,exportLocal(){const data={createdAt:new Date().toISOString(),pending:queue(),localStorage:{}};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&(/multiPlaza|mp_|quotation/i.test(k)))data.localStorage[k]=localStorage.getItem(k)}const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='Multi-Plaza-Local-Backup-'+new Date().toISOString().slice(0,10)+'.json';a.click();URL.revokeObjectURL(a.href)}};
})();
