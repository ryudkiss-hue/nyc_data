// ui.js: helpers shared by every page. Values from APIs or files go into the page with textContent only.

export const $ = (sel, root = document) => root.querySelector(sel);

export function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') n.className = v;
    else if (k === 'text') n.textContent = v;
    else n.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined && k !== false) n.append(k instanceof Node ? k : String(k));
  return n;
}

export const link = (href, text, external = true) =>
  el('a', external ? { href, target: '_blank', rel: 'noopener noreferrer' } : { href }, text);

export function table(caption, headers, rows, numeric = []) {
  if (!rows.length) return el('p', { class: 'empty' }, `${caption}: none.`);
  return el('div', { class: 'table-wrap' },
    el('table', {},
      el('caption', {}, `${caption} (${rows.length})`),
      el('thead', {}, el('tr', {}, headers.map((h) => el('th', { scope: 'col' }, h)))),
      el('tbody', {}, rows.map((r) => el('tr', {}, r.map((c, i) => el('td', numeric.includes(i) ? { class: 'num' } : {}, c ?? '')))))));
}

export const tags = (list) => list.map((t) => el('span', { class: /DELINQUENT|EXPIRED|older than|issue/i.test(t) ? 'tag warn' : 'tag' }, t));

export function download(name, text, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = el('a', { href: url, download: name });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function toCsv(rows, columns) {
  const cols = columns || [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const q = (v) => {
    if (v === null || v === undefined) return '';
    const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [cols.join(','), ...rows.map((r) => cols.map((c) => q(r[c])).join(','))].join('\r\n') + '\r\n';
}

export function setStatus(node, text, isError = false) {
  node.textContent = text;
  node.classList.toggle('error', isError);
}

export const store = {
  get(k) { try { return localStorage.getItem(`nycod.${k}`) || ''; } catch { return ''; } },
  set(k, v) { try { if (v) localStorage.setItem(`nycod.${k}`, v); else localStorage.removeItem(`nycod.${k}`); return true; } catch { return false; } },
};

// Tabs: native focusgroup="tablist", polyfilled only where missing; selection follows focus.
export function setupTabs(root = document, onSelect = () => {}) {
  const tabs = [...root.querySelectorAll('.tablist button')];
  const panelFor = (tab) => root.querySelector(`[role="tabpanel"][aria-labelledby="${tab.id}"]`);
  function select(tab) {
    for (const t of tabs) {
      const on = t === tab;
      t.setAttribute('aria-selected', String(on));
      t.toggleAttribute('focusgroupstart', on);
      const p = panelFor(t);
      if (on) p.removeAttribute('hidden'); else p.hidden = 'until-found';
    }
    onSelect(tab);
  }
  for (const t of tabs) {
    t.addEventListener('click', () => select(t));
    t.addEventListener('focus', () => select(t));
    panelFor(t).addEventListener('beforematch', () => select(t));
  }
  return select;
}

export async function polyfillFocusgroup() {
  if (Object.hasOwn(HTMLElement.prototype, 'focusGroup') || 'focusgroup' in HTMLElement.prototype) return;
  if (!document.querySelector('[focusgroup]')) return;
  try {
    const { polyfill } = await import('https://cdn.jsdelivr.net/npm/@microsoft/focusgroup-polyfill@1.6.0/build/index.min.mjs');
    polyfill();
  } catch { /* tabs still work by Tab key and click */ }
}

// Leaflet map of points; returns the map or null when Leaflet is missing or there are no points.
// points: [{lat, lon, label, color}]
export function pointMap(container, points, { maxZoom = 19, label = 'Map of the results' } = {}) {
  if (!window.L || !points.length) return null;
  const box = el('div', { class: 'map', role: 'region', 'aria-label': label });
  container.append(box);
  const m = L.map(box, { scrollWheelZoom: false });
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 20, maxNativeZoom: 19,
    attribution: '© OpenStreetMap contributors' }).addTo(m);
  const ll = [];
  for (const p of points) {
    L.circleMarker([p.lat, p.lon], { radius: 6, color: '#000', weight: 1, fillColor: p.color || '#1864ab', fillOpacity: 0.85 })
      .bindTooltip(p.label || `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`).addTo(m);
    ll.push([p.lat, p.lon]);
  }
  if (ll.length === 1) m.setView(ll[0], 18); else m.fitBounds(ll, { padding: [24, 24], maxZoom });
  return m;
}

// Points from a row: Socrata point/location columns, lat/lon pairs, or ArcGIS point geometry.
export function rowPoint(r) {
  for (const v of Object.values(r)) {
    if (v && typeof v === 'object' && v.type === 'Point' && Array.isArray(v.coordinates)) return { lon: +v.coordinates[0], lat: +v.coordinates[1] };
    if (v && typeof v === 'object' && v.latitude !== undefined && v.longitude !== undefined && v.latitude !== null) return { lat: +v.latitude, lon: +v.longitude };
  }
  const keys = Object.keys(r);
  const lk = keys.find((k) => /^(lat|latitude)$/i.test(k)), gk = keys.find((k) => /^(lon|lng|long|longitude|longitud)$/i.test(k));
  if (lk && gk && r[lk] !== null && r[gk] !== null && r[lk] !== '' && !Number.isNaN(+r[lk]) && !Number.isNaN(+r[gk])) return { lat: +r[lk], lon: +r[gk] };
  return null;
}

export function cell(v) {
  if (v === null || v === undefined) return '';
  if (typeof v === 'object') {
    if (v.type === 'Point' && v.coordinates) return `POINT (${v.coordinates[0]}, ${v.coordinates[1]})`;
    if (v.type && v.coordinates) return `${v.type} geometry`;
    if (v.url) return link(v.url, v.description || v.url);
    return JSON.stringify(v);
  }
  return String(v);
}

export async function getJson(url, init) {
  const r = await fetch(url, { headers: { Accept: 'application/json' }, ...init });
  const text = await r.text();
  let d;
  try { d = JSON.parse(text); } catch { throw new Error(`HTTP ${r.status}: ${text.slice(0, 300)}`); }
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${d.message || d.error?.message || text.slice(0, 300)}`);
  if (d && !Array.isArray(d) && d.error) throw new Error(`${d.error.message || JSON.stringify(d.error)}${d.error.details ? ' ' + d.error.details.join(' ') : ''}`);
  return d;
}

export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'numeric', day: 'numeric' }) : '');
export const daysSince = (iso) => (iso ? Math.floor((Date.now() - new Date(iso).getTime()) / 86400000) : null);
