// datasets.js: freshness board for the Sidewalk Program datasets in data/datasets.json.
import { $, el, link, download, toCsv, setStatus, getJson, fmtDate, daysSince } from './ui.js';

const PORTAL = 'https://data.cityofnewyork.us';
let reg = { datasets: [], sla_days: {} };
const live = new Map();   // id -> {updated, name, rows, error}

async function pool(items, n, fn) {
  let i = 0;
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, async () => { while (i < items.length) await fn(items[i++]); }));
}

function statusOf(d) {
  const l = live.get(d.id);
  if (!l || l.updated === undefined) return 'pending';
  if (l.error) return 'error';
  const days = daysSince(l.updated);
  return days > reg.sla_days[d.sla_tier] ? 'late' : 'ok';
}

function visible() {
  const t = $('#d-q').value.trim().toLowerCase(), dom = $('#d-domain').value, tier = $('#d-tier').value, st = $('#d-status').value;
  return reg.datasets.filter((d) => (!t || d.key.includes(t) || d.id.includes(t) || (d.name || '').toLowerCase().includes(t))
    && (!dom || d.domain === dom) && (!tier || d.sla_tier === tier)
    && (!st || (st === 'issue' ? !!d.issue : statusOf(d) === st)));
}

function render() {
  const rows = visible();
  const tb = el('tbody');
  for (const d of rows) {
    const l = live.get(d.id) || {};
    const days = l.updated ? daysSince(l.updated) : null;
    const st = statusOf(d);
    const joins = (d.foreign_keys || []).map((f) => `${f.column} → ${f.references}`).join('; ');
    tb.append(el('tr', {},
      el('td', {}, el('a', { href: `explore.html?ds=${d.id}` }, l.name || d.name), el('div', { class: 'sub hint' }, d.key)),
      el('td', {}, link(`${PORTAL}/d/${d.id}`, d.id)),
      el('td', {}, d.domain || ''),
      el('td', {}, d.sla_tier),
      el('td', {}, l.error ? el('span', { class: 'late' }, 'could not read') : l.updated ? fmtDate(l.updated) : '…'),
      el('td', { class: 'num' }, days === null ? '' : String(days)),
      el('td', {}, st === 'late' ? el('span', { class: 'late' }, `older than ${reg.sla_days[d.sla_tier]} days`)
        : st === 'ok' ? el('span', { class: 'ok' }, 'within tier') : st === 'error' ? l.error : '…'),
      el('td', { class: 'num' }, l.rows === undefined ? '' : l.rows),
      el('td', {}, joins),
      el('td', {}, d.issue || '')));
  }
  const counts = { late: 0, ok: 0, pending: 0, error: 0 };
  for (const d of reg.datasets) counts[statusOf(d)]++;
  $('#board').replaceChildren(el('div', { class: 'table-wrap' }, el('table', {},
    el('caption', {}, `${rows.length} of ${reg.datasets.length} datasets · ${counts.ok} within tier, ${counts.late} older${counts.pending ? `, ${counts.pending} still loading` : ''}${counts.error ? `, ${counts.error} unreadable` : ''}`),
    el('thead', {}, el('tr', {}, ['Dataset', 'ID', 'Domain', 'Tier', 'Data updated', 'Days', 'Status', 'Rows', 'Joins', 'Known issue'].map((h) => el('th', { scope: 'col' }, h)))),
    tb)));
}

async function loadFreshness() {
  const status = $('#status');
  let done = 0;
  setStatus(status, `Reading update dates for ${reg.datasets.length} datasets…`);
  let timer = null;
  const soon = () => { if (!timer) timer = setTimeout(() => { timer = null; render(); }, 250); };
  await pool(reg.datasets, 6, async (d) => {
    try {
      const m = await getJson(`${PORTAL}/api/views/metadata/v1/${d.id}`);
      live.set(d.id, { ...(live.get(d.id) || {}), updated: m.dataUpdatedAt || m.updatedAt || null, name: m.name });
    } catch (e) {
      live.set(d.id, { ...(live.get(d.id) || {}), updated: null, error: e.message.slice(0, 80) });
    }
    done++;
    setStatus(status, `Read ${done} of ${reg.datasets.length} update dates.`);
    soon();
  });
  render();
  const late = reg.datasets.filter((d) => statusOf(d) === 'late').length;
  setStatus(status, `Done. ${late} of ${reg.datasets.length} datasets are older than their tier allows.`);
}

async function countRows() {
  const rows = visible(), status = $('#status'), btn = $('#count');
  btn.disabled = true;
  let done = 0;
  await pool(rows, 4, async (d) => {
    try {
      const [r] = await getJson(`${PORTAL}/resource/${d.id}.json?$select=count(*) as n`);
      live.set(d.id, { ...(live.get(d.id) || {}), rows: Number(r.n).toLocaleString('en-US') });
    } catch (e) {
      live.set(d.id, { ...(live.get(d.id) || {}), rows: 'n/a' });
    }
    done++;
    setStatus(status, `Counted ${done} of ${rows.length}.`);
  });
  render();
  setStatus(status, `Counted rows for ${rows.length} datasets. "n/a" means the dataset has no row API (a map or file).`);
  btn.disabled = false;
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    reg = await getJson('data/datasets.json');
  } catch (e) {
    setStatus($('#status'), `Could not load data/datasets.json: ${e.message}`, true);
    return;
  }
  for (const d of [...new Set(reg.datasets.map((d) => d.domain))].sort()) $('#d-domain').append(el('option', {}, d));
  $('#tiers').textContent = `Tiers: HIGH ${reg.sla_days.HIGH} days, MEDIUM ${reg.sla_days.MEDIUM} days, LOW ${reg.sla_days.LOW} days. ${reg.sla_rule}`;
  const p = new URLSearchParams(location.search);
  for (const k of ['q', 'domain', 'tier', 'status']) if (p.get(k)) $(`#d-${k}`).value = p.get(k);
  $('#filter-form').addEventListener('input', render);
  $('#filter-form').addEventListener('submit', (e) => e.preventDefault());
  $('#count').addEventListener('click', countRows);
  $('#dl').addEventListener('click', () => download('datasets.csv', toCsv(visible().map((d) => {
    const l = live.get(d.id) || {};
    return { key: d.key, id: d.id, name: l.name || d.name, domain: d.domain, tier: d.sla_tier, data_updated: l.updated || '',
      days: l.updated ? daysSince(l.updated) : '', status: statusOf(d), rows: l.rows ?? '', joins: (d.foreign_keys || []).map((f) => `${f.column} -> ${f.references}`).join('; '), issue: d.issue || '' };
  })), 'text/csv'));
  render();
  loadFreshness();
});
