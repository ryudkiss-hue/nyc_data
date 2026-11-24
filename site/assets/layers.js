// layers.js: browse and query NYC DOT ArcGIS MapServer layers (read-only REST queries).
import { $, el, link, table, download, toCsv, setStatus, cell, getJson } from './ui.js';

const ARCGIS = 'https://a841-dotweb01.nyc.gov/arcgis/rest/services';
let current = null;   // {service, layer, info}
let lastGeo = null;
let map = null;

const svcUrl = (service) => `${ARCGIS}/${service}/MapServer`;

async function listServices(folder) {
  const status = $('#svc-status'), list = $('#svc-list');
  folder = folder.trim().replace(/^\/+|\/+$/g, '');
  setStatus(status, `Listing ${folder || 'the server root'}…`);
  list.replaceChildren();
  try {
    const d = await getJson(`${ARCGIS}/${folder}?f=json`);
    const svcs = (d.services || []).filter((s) => s.type === 'MapServer');
    for (const s of svcs) {
      const b = el('button', { type: 'button', 'aria-expanded': 'false' }, s.name.split('/').pop(), el('span', { class: 'sub' }, s.name));
      const li = el('li', {}, b);
      b.addEventListener('click', () => toggleLayers(s.name, li, b));
      list.append(li);
    }
    for (const f of d.folders || []) {
      const b = el('button', { type: 'button' }, `${f}/`, el('span', { class: 'sub' }, 'folder'));
      b.addEventListener('click', () => { $('#folder').value = f; listServices(f); });
      list.append(el('li', {}, b));
    }
    setStatus(status, `${svcs.length} map services${d.folders?.length ? ` and ${d.folders.length} folders` : ''} in ${folder || 'the root'}.`);
  } catch (e) {
    setStatus(status, `Could not list ${folder || 'the root'}: ${e.message}. DOT's server does not answer root listings from browsers; try PRISM or GAZETTEER.`, true);
  }
}

async function toggleLayers(service, li, btn) {
  const open = btn.getAttribute('aria-expanded') === 'true';
  li.querySelector('ul')?.remove();
  btn.setAttribute('aria-expanded', String(!open));
  if (open) return;
  try {
    const d = await getJson(`${svcUrl(service)}?f=json`);
    const ul = el('ul', { class: 'pick-list', 'aria-label': `Layers of ${service}` });
    for (const l of [...(d.layers || []), ...(d.tables || [])]) {
      const b = el('button', { type: 'button' }, l.name, el('span', { class: 'sub' }, `layer ${l.id}${l.subLayerIds ? ' (group)' : ''}`));
      b.addEventListener('click', () => openLayer(service, l.id, true));
      ul.append(el('li', {}, b));
    }
    li.append(ul);
  } catch (e) {
    li.append(el('ul', {}, el('li', { class: 'status error' }, e.message)));
  }
}

async function openLayer(service, layer, push) {
  const info = $('#layer-info');
  $('#layer-title').textContent = `Loading ${service} layer ${layer}…`;
  info.replaceChildren(); $('#results').hidden = true;
  try {
    const d = await getJson(`${svcUrl(service)}/${layer}?f=json`);
    current = { service, layer, info: d };
    $('#layer-title').textContent = `${d.name} (${service}, layer ${layer})`;
    const dl = el('dl', { class: 'meta' });
    const row = (k, v) => dl.append(el('dt', {}, k), el('dd', {}, v));
    row('Type', `${d.type || ''}${d.geometryType ? ', ' + d.geometryType.replace('esriGeometry', '') : ''}`);
    if (d.description) row('Description', d.description);
    if (d.copyrightText) row('Source', d.copyrightText);
    if (d.maxRecordCount) row('Server limit', `${d.maxRecordCount} features per request`);
    row('Links', el('span', {}, link(`${svcUrl(service)}/${layer}`, 'REST page'), ' · ', link(`${svcUrl(service)}/${layer}?f=pjson`, 'JSON')));
    info.append(dl);
    const fields = d.fields || [];
    info.append(el('details', {}, el('summary', {}, `Fields (${fields.length})`),
      table('Fields', ['Name', 'Alias', 'Type'], fields.map((f) => [f.name, f.alias, (f.type || '').replace('esriFieldType', '')]))));
    $('#query-form').hidden = !!d.subLayerIds?.length && !fields.length;
    if (d.subLayerIds?.length && !fields.length) info.append(el('p', { class: 'hint' }, 'This is a group layer: pick one of its sublayers to query.'));
    if (push) history.replaceState(null, '', `?svc=${encodeURIComponent(service)}&layer=${layer}`);
  } catch (e) {
    $('#layer-title').textContent = `Could not open ${service} layer ${layer}`;
    info.append(el('p', { class: 'status error' }, e.message));
  }
}

function queryParams(format) {
  const p = { where: $('#l-where').value.trim() || '1=1', outFields: $('#l-fields').value.trim() || '*', outSR: '4326',
    returnGeometry: $('#l-geom').checked ? 'true' : 'false', resultRecordCount: String(Math.min(2000, Math.max(1, parseInt($('#l-max').value, 10) || 200))), f: format };
  const lat = $('#l-lat').value.trim(), lon = $('#l-lon').value.trim();
  if (lat && lon) Object.assign(p, { geometry: `${Number(lon)},${Number(lat)}`, geometryType: 'esriGeometryPoint', inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects', distance: String(Number($('#l-dist').value) || 100), units: 'esriSRUnit_Foot' });
  return p;
}

async function run() {
  const status = $('#q-status'), out = $('#results');
  const { service, layer } = current;
  const geo = $('#l-geom').checked;
  const p = queryParams(geo ? 'geojson' : 'json');
  const url = `${svcUrl(service)}/${layer}/query?${new URLSearchParams(p)}`;
  const btn = $('#query-form button[type="submit"]'); btn.disabled = true;
  setStatus(status, 'Querying…');
  try {
    const d = await getJson(url);
    const feats = geo ? d.features || [] : (d.features || []).map((f) => ({ properties: f.attributes }));
    lastGeo = geo ? d : null;
    const props = feats.map((f) => f.properties || {});
    out.hidden = false; out.replaceChildren();
    if (map) { map.remove(); map = null; }
    const box = el('div', { class: 'result' }, el('h2', {}, `${feats.length} features`), el('p', { class: 'code' }, `GET ${url}`));
    out.append(box);
    const dlCsv = el('button', { type: 'button', class: 'btn' }, 'Download CSV');
    dlCsv.addEventListener('click', () => download(`${service.replace('/', '_')}_${layer}.csv`, toCsv(props), 'text/csv'));
    const acts = el('div', { class: 'actions' }, dlCsv);
    if (lastGeo) {
      const dlGeo = el('button', { type: 'button', class: 'btn' }, 'Download GeoJSON');
      dlGeo.addEventListener('click', () => download(`${service.replace('/', '_')}_${layer}.geojson`, JSON.stringify(lastGeo), 'application/geo+json'));
      acts.append(dlGeo);
    }
    box.append(acts);
    if (lastGeo && feats.some((f) => f.geometry) && window.L) {
      const m = el('div', { class: 'map', role: 'region', 'aria-label': `Map of ${feats.length} features` });
      box.append(m);
      map = L.map(m, { scrollWheelZoom: false });
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 20, maxNativeZoom: 19, attribution: '© OpenStreetMap contributors' }).addTo(map);
      const keys = Object.keys(props[0] || {}).slice(0, 4);
      const g = L.geoJSON(lastGeo, {
        pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 6, color: '#000', weight: 1, fillColor: '#1864ab', fillOpacity: 0.85 }),
        style: { color: '#1864ab', weight: 3 },
        onEachFeature: (f, lyr) => lyr.bindTooltip(keys.map((k) => `${k}: ${f.properties?.[k] ?? ''}`).join(' · ')),
      }).addTo(map);
      const b = g.getBounds();
      if (b.isValid()) map.fitBounds(b, { padding: [24, 24], maxZoom: 19 });
    }
    if (d.exceededTransferLimit || d.properties?.exceededTransferLimit) box.append(el('p', { class: 'hint' }, 'More features match than were returned: raise Max features (up to the server limit) or narrow the where clause.'));
    const keys = [...new Set(props.flatMap((r) => Object.keys(r)))];
    box.append(table('Features', keys, props.map((r) => keys.map((k) => cell(r[k])))));
    setStatus(status, `${feats.length} features.`);
    const s = new URLSearchParams({ svc: service, layer, where: p.where, fields: p.outFields, max: p.resultRecordCount });
    if (p.geometry) { s.set('lat', $('#l-lat').value.trim()); s.set('lon', $('#l-lon').value.trim()); s.set('dist', p.distance); }
    history.replaceState(null, '', `?${s}`);
  } catch (e) {
    setStatus(status, `The server refused the query: ${e.message}`, true);
  } finally { btn.disabled = false; }
}

document.addEventListener('DOMContentLoaded', async () => {
  $('#folder-form').addEventListener('submit', (e) => { e.preventDefault(); listServices($('#folder').value); });
  $('#query-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const bad = [...$('#query-form').querySelectorAll('input')].find((i) => !i.checkValidity());
    if (bad) { bad.setAttribute('aria-invalid', 'true'); bad.focus(); setStatus($('#q-status'), 'Latitude and longitude must be decimal numbers.', true); return; }
    run();
  });
  $('#share').addEventListener('click', async (e) => {
    try { await navigator.clipboard.writeText(location.href); e.target.textContent = 'Link copied'; } catch { e.target.textContent = 'Copy failed'; }
    setTimeout(() => { e.target.textContent = 'Copy link to this query'; }, 2000);
  });
  const u = new URLSearchParams(location.search);
  const svc = u.get('svc');
  if (svc) $('#folder').value = svc.split('/')[0];
  listServices($('#folder').value);
  if (svc && /^[A-Za-z0-9_]+\/[A-Za-z0-9_]+$/.test(svc)) {
    await openLayer(svc, parseInt(u.get('layer') || '0', 10), false);
    for (const [k, id] of [['where', 'l-where'], ['fields', 'l-fields'], ['lat', 'l-lat'], ['lon', 'l-lon'], ['dist', 'l-dist'], ['max', 'l-max']]) if (u.get(k)) $(`#${id}`).value = u.get(k);
    if (u.get('where') || u.get('lat') || u.get('run') === '1') run();
  }
});
