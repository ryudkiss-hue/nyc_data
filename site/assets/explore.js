// explore.js: query any NYC Open Data dataset from the browser (Socrata SODA 2.1 resource API).
import { $, el, link, table, download, toCsv, setStatus, pointMap, rowPoint, cell, getJson, fmtDate, daysSince } from './ui.js';

const PORTAL = 'https://data.cityofnewyork.us';
const CATALOG = 'https://api.us.socrata.com/api/catalog/v1';
const ID_RE = /^[a-z0-9]{4}-[a-z0-9]{4}$/;
const GEO = new Set(['point', 'location', 'multipoint', 'line', 'multiline', 'polygon', 'multipolygon']);
const NUMERIC = new Set(['number', 'money', 'double', 'percent']);
const OPS = [
  ['=', 'equals'], ['!=', 'does not equal'], ['>', 'greater than'], ['>=', 'at least'], ['<', 'less than'], ['<=', 'at most'],
  ['contains', 'contains'], ['starts', 'starts with'], ['in', 'is one of (comma list)'], ['null', 'is blank'], ['notnull', 'is not blank'],
  ['within', 'within meters of lat, lon (map columns)'],
];

let registry = { datasets: [], sla_days: {} };
let byId = new Map(), byKey = new Map();
let meta = null;          // current dataset metadata (views API)
let cols = [];            // [{field, name, type}]
let offset = 0;
let lastRows = [];
let map = null;

const sqv = (s) => String(s).replace(/'/g, "''");
const q = (field) => `\`${field}\``;

// ------------------------------------------------------------------ dataset list
async function loadRegistry() {
  try {
    registry = await getJson('data/datasets.json');
    byId = new Map(registry.datasets.map((d) => [d.id, d]));
    byKey = new Map(registry.datasets.map((d) => [d.key, d]));
  } catch (e) {
    setStatus($('#find-status'), `Could not load the Sidewalk Program dataset list (${e.message}). Search still works.`, true);
  }
}

function renderPick(items, note) {
  const list = $('#find-list');
  list.replaceChildren(...items.map((d) => {
    const b = el('button', { type: 'button', 'data-id': d.id, 'aria-current': meta && meta.id === d.id ? 'true' : null },
      d.name, el('span', { class: 'sub' }, [d.id, d.key, d.extra].filter(Boolean).join(' · ')));
    b.addEventListener('click', () => openDataset(d.id, true));
    return el('li', {}, b);
  }));
  setStatus($('#find-status'), note);
}

function filterRegistry() {
  const t = $('#find-q').value.trim().toLowerCase();
  const hits = registry.datasets.filter((d) => !t || d.key.includes(t) || d.id.includes(t) || (d.name || '').toLowerCase().includes(t));
  renderPick(hits.slice(0, 200), `${hits.length} of ${registry.datasets.length} Sidewalk Program datasets${t ? ` match "${t}"` : ''}.`);
}

async function searchCatalog(text) {
  const status = $('#find-status');
  setStatus(status, `Searching NYC Open Data for "${text}"…`);
  try {
    const p = new URLSearchParams({ domains: 'data.cityofnewyork.us', search_context: 'data.cityofnewyork.us', q: text, only: 'dataset', limit: '40' });
    const d = await getJson(`${CATALOG}?${p}`);
    const items = d.results.map((r) => ({ id: r.resource.id, name: r.resource.name,
      key: byId.get(r.resource.id)?.key, extra: r.resource.data_updated_at ? `updated ${fmtDate(r.resource.data_updated_at)}` : null }));
    renderPick(items, `${d.resultSetSize ?? items.length} datasets on NYC Open Data match "${text}"; showing ${items.length}.`);
  } catch (e) {
    setStatus(status, `Catalog search failed: ${e.message}`, true);
  }
}

// ------------------------------------------------------------------ dataset header
async function openDataset(id, push) {
  id = id.trim().toLowerCase();
  if (!ID_RE.test(id)) { setStatus($('#find-status'), `"${id}" is not a dataset ID (four characters, a dash, four characters).`, true); return; }
  const info = $('#ds-info');
  $('#ds-title').textContent = `Loading ${id}…`;
  info.replaceChildren();
  $('#query-form').hidden = true; $('#results').hidden = true; $('#profile-out').hidden = true;
  try {
    meta = await getJson(`${PORTAL}/api/views/${id}.json`);
  } catch (e) {
    $('#ds-title').textContent = `Could not open ${id}`;
    info.append(el('p', { class: 'status error' }, e.message));
    return;
  }
  if (meta.assetType && meta.assetType !== 'dataset') {
    $('#ds-title').textContent = meta.name;
    info.append(el('p', { class: 'status error' }, `${id} is a ${meta.assetType}, not a table: it has no rows to query. Look for the dataset it is built from on the `, link(`${PORTAL}/d/${id}`, 'Open Data page'), '.'));
    return;
  }
  cols = (meta.columns || []).filter((c) => !c.fieldName.startsWith(':')).map((c) => ({ field: c.fieldName, name: c.name, type: c.dataTypeName, description: c.description }));
  const reg = byId.get(id);
  $('#ds-title').textContent = meta.name;
  const dl = el('dl', { class: 'meta' });
  const row = (k, v) => dl.append(el('dt', {}, k), el('dd', {}, v));
  row('Dataset ID', `${id}${reg ? ` (registry key ${reg.key})` : ''}`);
  if (meta.attribution) row('Published by', meta.attribution);
  const upd = meta.rowsUpdatedAt ? new Date(meta.rowsUpdatedAt * 1000).toISOString() : null;
  const days = daysSince(upd);
  const slaDays = reg ? registry.sla_days[reg.sla_tier] : null;
  row('Data updated', upd ? el('span', {}, `${fmtDate(upd)} (${days} days ago)`,
    slaDays ? el('span', { class: days > slaDays ? 'late' : 'ok' }, ` ${reg.sla_tier} tier: ${days > slaDays ? 'older than' : 'within'} ${slaDays} days`) : '') : 'not given');
  const rowsDd = el('span', {}, 'counting…');
  row('Rows', rowsDd);
  row('Columns', String(cols.length));
  if (reg?.primary_key) row('Primary key', reg.primary_key);
  const joins = [];
  for (const fk of reg?.foreign_keys || []) joins.push([fk.column, fk.references]);
  for (const other of registry.datasets) for (const fk of other.foreign_keys || []) if (fk.references.startsWith(`${reg?.key}.`)) joins.push([fk.references.split('.')[1], `${other.key}.${fk.column}`]);
  if (joins.length) row('Joins', el('ul', {}, joins.map(([c, ref]) => {
    const target = byKey.get(ref.split('.')[0]);
    return el('li', {}, `${c} → ${ref} `, target ? (() => { const b = el('button', { type: 'button', class: 'btn' }, `Open ${target.id}`); b.addEventListener('click', () => openDataset(target.id, true)); return b; })() : '');
  })));
  row('Links', el('span', {}, link(`${PORTAL}/d/${id}`, 'Open Data page'), ' · ', link(`${PORTAL}/resource/${id}.json`, 'API endpoint'), ' · ', link(`${PORTAL}/api/views/${id}.json`, 'Metadata')));
  info.append(dl);
  if (reg?.issue) info.append(el('p', { class: 'box errors' }, el('strong', {}, 'Known issue: '), reg.issue));
  if (meta.description) info.append(el('details', {}, el('summary', {}, 'Description'), el('p', { class: 'prose' }, meta.description)));
  info.append(el('details', {}, el('summary', {}, `Column list (${cols.length})`),
    table('Columns', ['Field', 'Label', 'Type', 'Description'], cols.map((c) => [c.field, c.name, c.type, c.description || '']))));
  getJson(`${PORTAL}/resource/${id}.json?$select=count(*) as n`).then((d) => { rowsDd.textContent = Number(d[0].n).toLocaleString('en-US'); })
    .catch((e) => { rowsDd.textContent = `count failed: ${e.message}`; });

  buildForm();
  for (const b of $('#find-list').querySelectorAll('button')) b.setAttribute('aria-current', String(b.dataset.id === id));
  if (push) history.replaceState(null, '', `?ds=${id}`);
}

// ------------------------------------------------------------------ query builder
function colOptions(filter = () => true, first = null) {
  return [...(first ? [el('option', { value: '' }, first)] : []), ...cols.filter(filter).map((c) => el('option', { value: c.field }, `${c.name} (${c.field})`))];
}

function addFilter(init = {}) {
  const i = $('#filters').children.length + 1;
  const col = el('select', { id: `f${i}-col`, 'data-role': 'col' }, colOptions());
  const op = el('select', { id: `f${i}-op`, 'data-role': 'op' }, OPS.map(([v, t]) => el('option', { value: v }, t)));
  const val = el('input', { id: `f${i}-val`, 'data-role': 'val', type: 'text', autocomplete: 'off', spellcheck: 'false' });
  const rm = el('button', { type: 'button', 'aria-label': `Remove filter ${i}` }, 'Remove');
  const rowEl = el('div', { class: 'filter-row' },
    el('div', { class: 'field' }, el('label', { for: col.id }, 'Column'), col),
    el('div', { class: 'field' }, el('label', { for: op.id }, 'Condition'), op),
    el('div', { class: 'field' }, el('label', { for: val.id }, 'Value'), val), rm);
  if (init.col) col.value = init.col;
  if (init.op) op.value = init.op;
  if (init.val) val.value = init.val;
  const hint = () => {
    const t = cols.find((c) => c.field === col.value)?.type;
    val.placeholder = op.value === 'within' ? '40.6757, -73.9744, 50' : op.value === 'in' ? 'A, B, C' : t === 'calendar_date' ? '2026-01-01' : '';
    val.disabled = op.value === 'null' || op.value === 'notnull';
  };
  col.addEventListener('change', hint); op.addEventListener('change', hint); hint();
  rm.addEventListener('click', () => { rowEl.remove(); writeSoql(); });
  $('#filters').append(rowEl);
}

function buildForm() {
  const form = $('#query-form');
  form.hidden = false;
  $('#filters').replaceChildren();
  $('#q-order').replaceChildren(...colOptions(() => true, 'Dataset order'));
  $('#q-countby').replaceChildren(...colOptions((c) => !GEO.has(c.type), 'No grouping'));
  $('#cols').replaceChildren(...cols.map((c, i) => el('label', { for: `col-${i}` },
    el('input', { type: 'checkbox', id: `col-${i}`, value: c.field }), c.name)));
  $('#q-text').value = ''; $('#q-limit').value = '100';
  for (const id of ['s-select', 's-where', 's-order', 's-group']) $(`#${id}`).value = '';
  offset = 0;
  setStatus($('#q-status'), '');
}

function literal(field, v) {
  const t = cols.find((c) => c.field === field)?.type;
  v = v.trim();
  if (NUMERIC.has(t) && v !== '' && !Number.isNaN(Number(v))) return v;
  if (t === 'checkbox') return /^(true|yes|1)$/i.test(v) ? 'true' : 'false';
  return `'${sqv(v)}'`;
}

function whereFromFilters() {
  const parts = [];
  for (const r of $('#filters').children) {
    const f = r.querySelector('[data-role="col"]').value, op = r.querySelector('[data-role="op"]').value, v = r.querySelector('[data-role="val"]').value;
    if (!f) continue;
    if (op === 'null') parts.push(`${q(f)} IS NULL`);
    else if (op === 'notnull') parts.push(`${q(f)} IS NOT NULL`);
    else if (v.trim() === '') continue;
    else if (op === 'contains') parts.push(`upper(${q(f)}) like upper('%${sqv(v.trim())}%')`);
    else if (op === 'starts') parts.push(`upper(${q(f)}) like upper('${sqv(v.trim())}%')`);
    else if (op === 'in') parts.push(`${q(f)} in (${v.split(',').map((x) => x.trim()).filter(Boolean).map((x) => literal(f, x)).join(', ')})`);
    else if (op === 'within') {
      const n = v.split(',').map((x) => Number(x.trim()));
      if (n.length === 3 && n.every((x) => !Number.isNaN(x))) parts.push(`within_circle(${q(f)}, ${n[0]}, ${n[1]}, ${n[2]})`);
    } else parts.push(`${q(f)} ${op} ${literal(f, v)}`);
  }
  return parts.join(' AND ');
}

function writeSoql() {
  const countBy = $('#q-countby').value;
  const picked = [...$('#cols').querySelectorAll('input:checked')].map((i) => q(i.value));
  const ord = $('#q-order').value;
  $('#s-where').value = whereFromFilters();
  if (countBy) {
    $('#s-select').value = `${q(countBy)}, count(*) as count`;
    $('#s-group').value = q(countBy);
    $('#s-order').value = `count ${$('#q-dir').value}`;
  } else {
    $('#s-select').value = picked.join(', ');
    $('#s-group').value = '';
    $('#s-order').value = ord ? `${q(ord)} ${$('#q-dir').value}` : '';
  }
}

function params(extra = {}) {
  const p = {};
  const add = (k, v) => { if (v !== undefined && v !== null && String(v).trim() !== '') p[k] = String(v).trim(); };
  add('$select', $('#s-select').value); add('$where', $('#s-where').value); add('$order', $('#s-order').value);
  add('$group', $('#s-group').value); add('$q', $('#q-text').value);
  add('$limit', Math.max(1, Math.min(50000, parseInt($('#q-limit').value, 10) || 100)));
  if (offset) add('$offset', offset);
  return { ...p, ...extra };
}

// ------------------------------------------------------------------ results
async function run() {
  const status = $('#q-status'), out = $('#results');
  const p = params();
  const url = `${PORTAL}/resource/${meta.id}.json?${new URLSearchParams(p)}`;
  setStatus(status, 'Running…');
  const btn = $('#query-form button[type="submit"]'); btn.disabled = true;
  try {
    const rows = await getJson(url);
    lastRows = rows;
    renderResults(rows, p);
    const lim = Number(p.$limit);
    setStatus(status, rows.length ? `Rows ${offset + 1}–${offset + rows.length}${rows.length === lim ? ' (more may follow)' : ''}.` : 'No rows match.');
    const share = new URLSearchParams({ ds: meta.id });
    for (const [k, v] of Object.entries(p)) share.set(k.replace('$', ''), v);
    history.replaceState(null, '', `?${share}`);
  } catch (e) {
    out.hidden = true;
    setStatus(status, `The API refused the query: ${e.message}`, true);
  } finally { btn.disabled = false; }
}

function renderResults(rows, p) {
  const out = $('#results');
  out.hidden = false;
  out.replaceChildren();
  if (map) { map.remove(); map = null; }
  const lim = Number(p.$limit);
  const head = el('div', { class: 'result' }, el('h2', {}, `Results: ${meta.name}`));
  out.append(head);
  const apiParams = new URLSearchParams({ ...p, $limit: 50000 }); apiParams.delete('$offset');
  head.append(el('p', { class: 'code' }, `GET ${PORTAL}/resource/${meta.id}.json?${new URLSearchParams(p)}`));
  const pager = el('div', { class: 'pager' });
  const prev = el('button', { type: 'button', class: 'btn', disabled: offset === 0 }, 'Previous page');
  const next = el('button', { type: 'button', class: 'btn', disabled: rows.length < lim }, 'Next page');
  prev.addEventListener('click', () => { offset = Math.max(0, offset - lim); run(); });
  next.addEventListener('click', () => { offset += lim; run(); });
  pager.append(prev, next);
  const dlCsv = el('button', { type: 'button', class: 'btn' }, 'Download these rows (CSV)');
  dlCsv.addEventListener('click', () => download(`${meta.id}_rows.csv`, toCsv(rows), 'text/csv'));
  const dlJson = el('button', { type: 'button', class: 'btn' }, 'Download these rows (JSON)');
  dlJson.addEventListener('click', () => download(`${meta.id}_rows.json`, JSON.stringify(rows, null, 1)));
  head.append(el('div', { class: 'actions' }, pager, dlCsv, dlJson,
    el('a', { class: 'btn', href: `${PORTAL}/resource/${meta.id}.csv?${apiParams}`, target: '_blank', rel: 'noopener noreferrer' }, 'CSV of up to 50,000 matching rows (API)')));
  if (!rows.length) { head.append(el('p', { class: 'empty' }, 'No rows match this query.')); return; }
  const pts = [];
  for (const r of rows.slice(0, 5000)) { const pt = rowPoint(r); if (pt && Math.abs(pt.lat) <= 90) pts.push({ ...pt, label: Object.values(r).filter((v) => typeof v === 'string').slice(0, 3).join(' · ') }); }
  if (pts.length) {
    head.append(el('h3', {}, `Map (${pts.length} of ${rows.length} rows have a location)`));
    map = pointMap(head, pts, { label: `Map of ${pts.length} result rows` });
  }
  const keys = [...new Set(rows.flatMap((r) => Object.keys(r)))].filter((k) => !k.startsWith(':@computed'));
  const labelOf = (k) => cols.find((c) => c.field === k)?.name || k;
  head.append(table(`Rows ${offset + 1}–${offset + rows.length}`, keys.map(labelOf), rows.map((r) => keys.map((k) => cell(r[k]))),
    keys.map((k, i) => (NUMERIC.has(cols.find((c) => c.field === k)?.type) || k === 'count' ? i : -1)).filter((i) => i >= 0)));
}

// ------------------------------------------------------------------ profile
async function profile() {
  const out = $('#profile-out'), status = $('#q-status');
  out.hidden = false; out.replaceChildren(el('h2', {}, 'Column profile'));
  const where = $('#s-where').value.trim(), text = $('#q-text').value.trim();
  out.append(el('p', { class: 'hint' }, `Counts over ${where || text ? 'the rows matching the current filters' : 'every row'}. Distinct counts are skipped for map columns.`));
  const res = [];
  const todo = cols.slice(0, 80);
  try {
    for (let i = 0; i < todo.length; i += 8) {
      setStatus(status, `Profiling columns ${i + 1}–${Math.min(i + 8, todo.length)} of ${todo.length}…`);
      const batch = todo.slice(i, i + 8);
      const sel = ['count(*) as __n', ...batch.flatMap((c, j) => [`count(${q(c.field)}) as c${j}`, ...(GEO.has(c.type) ? [] : [`count(distinct ${q(c.field)}) as d${j}`])])];
      const p = { $select: sel.join(', ') };
      if (where) p.$where = where;
      if (text) p.$q = text;
      const [d] = await getJson(`${PORTAL}/resource/${meta.id}.json?${new URLSearchParams(p)}`);
      const n = Number(d.__n);
      batch.forEach((c, j) => res.push([c.name, c.field, c.type, Number(d[`c${j}`]).toLocaleString('en-US'),
        n ? `${((100 * Number(d[`c${j}`])) / n).toFixed(1)}%` : '', d[`d${j}`] !== undefined ? Number(d[`d${j}`]).toLocaleString('en-US') : '']));
      if (i === 0) out.append(el('p', {}, `${n.toLocaleString('en-US')} rows.`));
    }
    out.append(table('Columns', ['Column', 'Field', 'Type', 'Filled', 'Filled %', 'Distinct values'], res, [3, 4, 5]));
    if (cols.length > todo.length) out.append(el('p', { class: 'hint' }, `Profiled the first ${todo.length} of ${cols.length} columns.`));
    setStatus(status, 'Profile done.');
  } catch (e) {
    out.append(table('Columns profiled before the error', ['Column', 'Field', 'Type', 'Filled', 'Filled %', 'Distinct values'], res, [3, 4, 5]));
    setStatus(status, `Profile stopped: ${e.message}`, true);
  }
}

// ------------------------------------------------------------------ start
document.addEventListener('DOMContentLoaded', async () => {
  await loadRegistry();
  filterRegistry();
  $('#find-q').addEventListener('input', filterRegistry);
  $('#find-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const t = $('#find-q').value.trim();
    if (!t) { setStatus($('#find-status'), 'Type a name, keyword or dataset ID first.', true); $('#find-q').focus(); return; }
    if (ID_RE.test(t.toLowerCase())) openDataset(t, true); else searchCatalog(t);
  });
  $('#add-filter').addEventListener('click', () => { addFilter(); $('#filters').lastElementChild.querySelector('select').focus(); });
  $('#query-form').addEventListener('change', (e) => { if (!e.target.closest('.soql')) { offset = 0; writeSoql(); } });
  $('#query-form').addEventListener('input', (e) => { if (e.target.matches('[data-role="val"]')) writeSoql(); });
  $('#cols-all').addEventListener('click', () => { for (const c of $('#cols').querySelectorAll('input')) c.checked = true; writeSoql(); });
  $('#cols-none').addEventListener('click', () => { for (const c of $('#cols').querySelectorAll('input')) c.checked = false; writeSoql(); });
  $('#query-form').addEventListener('submit', (e) => { e.preventDefault(); offset = 0; run(); });
  $('#profile').addEventListener('click', profile);
  $('#share').addEventListener('click', async (e) => {
    try { await navigator.clipboard.writeText(location.href); e.target.textContent = 'Link copied'; } catch { e.target.textContent = 'Copy failed'; }
    setTimeout(() => { e.target.textContent = 'Copy link to this query'; }, 2000);
  });

  const u = new URLSearchParams(location.search);
  if (u.get('search')) { $('#find-q').value = u.get('search'); filterRegistry(); searchCatalog(u.get('search')); }
  if (u.get('ds')) {
    await openDataset(u.get('ds'), false);
    if (!meta) return;
    const map2 = { select: 's-select', where: 's-where', order: 's-order', group: 's-group' };
    let any = false;
    for (const [k, id] of Object.entries(map2)) if (u.get(k)) { $(`#${id}`).value = u.get(k); any = true; }
    if (u.get('q')) { $('#q-text').value = u.get('q'); any = true; }
    if (u.get('limit')) $('#q-limit').value = u.get('limit');
    if (u.get('offset')) offset = parseInt(u.get('offset'), 10) || 0;
    if (any || u.get('run') === '1') run();
  }
});

