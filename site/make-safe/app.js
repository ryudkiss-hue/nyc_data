// app.js: page wiring for the Make Safe SR brief. All event binding goes through addEventListener; every value from
// the APIs or the workbook goes into the page with textContent (never innerHTML).
import { createBrief, readSrRows, recordToInput, odDate } from './brief.js';
import { $, el, link, table, tags, download, setStatus, store, setupTabs, polyfillFocusgroup } from '../assets/ui.js';

let B = null;
function makeBrief() {
  B = createBrief({ proj4: window.proj4, appToken: store.get('token'), dynamicsBase: store.get('dynamics') });
}

// ------------------------------------------------------------------ rendering one brief
let currentMap = null;
function renderMap(container, b) {
  if (!window.L || !b.point) return null;
  const box = el('div', { class: 'map', role: 'region', 'aria-label': 'Map of the SR point, candidate corners and ramps' });
  container.append(box,
    el('p', { class: 'hint' },
      el('span', { class: 'legend-dot', style: 'background:#000' }), 'SR point  ',
      el('span', { class: 'legend-dot', style: 'background:#1864ab' }), 'candidate corner  ',
      el('span', { class: 'legend-dot', style: 'background:#fff' }), 'other corner at the intersection  ',
      el('span', { class: 'legend-dot', style: 'background:#e8a400' }), 'ramp'));
  const m = L.map(box, { scrollWheelZoom: false }).setView([b.point.lat, b.point.lon], 19);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 20, maxNativeZoom: 19,
    attribution: '© OpenStreetMap contributors' }).addTo(m);
  const pts = [[b.point.lat, b.point.lon]];
  L.circleMarker([b.point.lat, b.point.lon], { radius: 7, color: '#000', fillColor: '#000', fillOpacity: 1 })
    .bindTooltip(`SR point (${b.point.source})`).addTo(m);
  for (const c of b.corners) {
    const cand = c.within_radius || c.at_named_intersection;
    L.circleMarker([c.lat, c.lon], { radius: 8, color: '#000', weight: 2, fillColor: cand ? '#1864ab' : '#ffffff', fillOpacity: 1 })
      .bindTooltip(`${c.dir_label || 'direction blank'} · ${c.cid}`, { permanent: cand, direction: 'top' }).addTo(m);
    pts.push([c.lat, c.lon]);
    for (const r of c.ramps) L.circleMarker([r.lat, r.lon], { radius: 4, color: '#7a5600', fillColor: '#e8a400', fillOpacity: 1 })
      .bindTooltip(`Ramp ${r.ramp} (${r.type}) · ${r.street}`).addTo(m);
  }
  if (pts.length > 1) m.fitBounds(pts, { padding: [30, 30], maxZoom: 20 });
  return m;
}

function renderBrief(container, b, { headingLevel = 2 } = {}) {
  container.replaceChildren();
  const H = `h${headingLevel}`, H2 = `h${headingLevel + 1}`;
  const wrap = el('article', { class: 'result' });
  container.append(wrap);
  wrap.append(el(H, {}, `${b.sr || 'SR without number'} · ${b.borough}`));
  const meta = el('dl', { class: 'meta' });
  const row = (k, v) => meta.append(el('dt', {}, k), el('dd', {}, v));
  row('Created On', b.complaint_date ? odDate(b.complaint_date) : 'not given (today used)');
  if (b.point) row('SR point', `${b.point.lat.toFixed(6)}, ${b.point.lon.toFixed(6)} (${b.point.source})`);
  row('SR tax lot', b.sr_lot.bbl ? `${b.sr_lot.bbl}${b.sr_lot.address ? ' · ' + b.sr_lot.address : ''}` : 'none under the point');
  if (b.intersection_source) row('Intersection from', b.intersection_source);
  if (b.dynamics_link) row('Dynamics', link(b.dynamics_link, 'Open the record'));
  row('In jagj-gttd', b.sr ? (b.facts.this_sr_logged_in_jagj ? `yes, corners ${b.facts.this_sr_logged_corners.join(', ')}` : 'not yet (logging lags about a week)') : 'no SR number given');
  wrap.append(meta);
  if (b.description) wrap.append(el('p', { class: 'caller' }, el('strong', {}, 'Caller: '), `"${b.description}"`));
  if (b.additional_location_details) wrap.append(el('p', {}, el('strong', {}, 'Additional Location Details: '), b.additional_location_details));

  wrap.append(el('div', { class: 'actions' },
    el('button', { type: 'button', class: 'btn', 'data-act': 'json' }, 'Download JSON'),
    el('button', { type: 'button', class: 'btn', 'data-act': 'txt' }, 'Download summary.txt'),
    el('button', { type: 'button', class: 'btn', 'data-act': 'copy' }, 'Copy summary')));
  const stem = b.sr || 'brief';
  wrap.querySelector('[data-act="json"]').addEventListener('click', () => download(`${stem}.json`, JSON.stringify(b, null, 1)));
  wrap.querySelector('[data-act="txt"]').addEventListener('click', () => download(`${stem}.summary.txt`, b.summary + '\n', 'text/plain'));
  wrap.querySelector('[data-act="copy"]').addEventListener('click', async (e) => {
    try { await navigator.clipboard.writeText(b.summary); e.target.textContent = 'Copied'; } catch { e.target.textContent = 'Copy failed'; }
    setTimeout(() => { e.target.textContent = 'Copy summary'; }, 2000);
  });

  wrap.append(el(H2, {}, 'Rules these facts feed'));
  wrap.append(b.rules_these_facts_feed.length ? el('ul', { class: 'feeds' }, b.rules_these_facts_feed.map((x) => el('li', {}, x)))
    : el('p', { class: 'empty' }, 'No made-safe, permit, capital or logging facts that point to a specific rule.'));
  wrap.append(el('p', {}, el('strong', {}, 'Corners rule: '), b.corners_rule));
  if (b.errors.length) wrap.append(el('div', { class: 'box errors', role: 'alert' }, el('strong', {}, 'Sources not read (nothing filled in): '), el('ul', {}, b.errors.map((x) => el('li', {}, x)))));
  if (b.notes.length) wrap.append(el('div', { class: 'box notes' }, el('strong', {}, 'Notes'), el('ul', {}, b.notes.map((x) => el('li', {}, x)))));

  wrap.append(el(H2, {}, 'Corners'));
  if (currentMap && container.id === 'one-result') { currentMap.remove(); currentMap = null; }
  const m = renderMap(wrap, b);
  if (container.id === 'one-result') currentMap = m;
  wrap.append(table('Candidate and intersection corners',
    ['CMTCornerID', 'Direction', 'On / From', 'Feet', 'Ramps', 'Program', 'Flags', 'Street Smart'],
    b.corners.map((c) => {
      const pr = b.ramp_program[String(c.cid)];
      const flags = [['within radius', c.within_radius], ['named intersection', c.at_named_intersection], ['on SR lot', c.on_sr_lot], ['named by caller', c.named_by_caller]]
        .filter(([, on]) => on).map(([t]) => t);
      return [String(c.cid), c.dir_label || 'blank', `${c.on} / ${c.frm}`, c.dist_ft ?? '', String(c.ramps.length),
        pr ? `${pr.status}${pr.construction_type ? ', ' + pr.construction_type : ''}${pr.completed ? ', completed ' + pr.completed : ''}` : 'no row',
        tags(flags), link(c.link, 'View')];
    }), [3, 4]));
  if (b.reference_corner) wrap.append(el('p', {}, el('strong', {}, 'Reference corner (mid-block): '),
    `${b.reference_corner.cid} ${b.reference_corner.dir_label || ''} ${b.reference_corner.on} / ${b.reference_corner.frm}`));

  wrap.append(el(H2, {}, 'Ramp complaints and temporary repairs (jagj-gttd)'));
  wrap.append(table('Rows for these corners', ['Complaint', 'Date', 'Corner', 'Temp repair feasible', 'Temp repair', 'Type', 'Second repair'],
    b.ramp_complaints_history.map((r) => [r.complaint_id, odDate(r.complaint_date), r.cmt_corner_id, r.temp_repair_feasible,
      odDate(r.temp_repair_date), r.temp_repair_type, odDate(r.date_second_temp_repair)])));

  wrap.append(el(H2, {}, 'Street permits (tqtj-sjs8)'));
  wrap.append(el('p', { class: 'hint' }, `Issued since ${odDate(b.permit_window_since)}${b.permit_window_extended_to ? `, and from ${odDate(b.permit_window_extended_to)} (earliest ramp program completion)` : ''}. ` +
    b.permit_queries.map((q) => q.kind === 'address' ? `${q.house_number} ${q.street}: ${q.rows}` : `${q.a} / ${q.b} since ${odDate(q.since)}: ${q.rows}`).join(' · ')));
  wrap.append(table('Permits', ['Permit', 'Type', 'Permittee', 'Status', 'Work dates', 'Location', 'Tags'],
    b.permits.map((p) => [link(p.nycstreets, p.permitnumber), p.permittypedesc, p.permitteename, p.permitstatusshortdesc,
      `${odDate(p.issuedworkstartdate)}-${odDate(p.issuedworkenddate)}${p.in_force_on_complaint_date ? ' (in force on Created On)' : ''}`,
      [p.onstreetname, p.fromstreetname, p.tostreetname].filter(Boolean).join(' / ') + (p.permitlocationcomments ? ` · ${p.permitlocationcomments}` : ''),
      tags(p.tags)])));
  if (b.permit_links.length) {
    wrap.append(el(H2, {}, 'Quality of Work permit links (screenshot order)'));
    wrap.append(el('ol', {}, b.permit_links.map((p) => el('li', {}, link(p.url, p.label)))));
    wrap.append(el('p', { class: 'hint' }, 'NYCStreets pages open only on the DOT network with your sign-in.'));
  }

  wrap.append(el(H2, {}, 'Completed capital projects within 60 m (97nd-ff3i)'));
  wrap.append(table('Projects', ['FMS ID', 'Title', 'Lead agency', 'Type', 'Completed', 'Near corner'],
    b.capital_projects.map((c) => [c.fmsid, c.projtitle, c.leadagency, c.projectt_1, c.construc_2 ? odDate(c.construc_2) : 'blank', String(c.near_cid)])));

  wrap.append(el(H2, {}, 'Public 311 sidewalk and curb requests within 50 m, last year (erm2-nwe9)'));
  wrap.append(table('Requests', ['Created', 'Descriptor', 'Address', 'Status', 'Resolution'],
    b.public_311_nearby.map((r) => [odDate(r.created_date), r.descriptor, r.incident_address || [r.intersection_street_1, r.intersection_street_2].filter(Boolean).join(' & '),
      r.status, r.resolution_description])));

  wrap.append(el(H2, {}, 'Not covered here'));
  wrap.append(el('ul', {}, b.not_covered.map((x) => el('li', {}, x))));
  wrap.append(el('details', {}, el('summary', {}, 'Plain-text summary'), el('pre', { class: 'summary' }, b.summary)));
}

// ------------------------------------------------------------------ one SR
function setupOne() {
  const form = $('#one-form'), status = $('#one-status'), out = $('#one-result');
  const sr = $('#f-sr');
  sr.addEventListener('input', () => { sr.setCustomValidity(''); sr.removeAttribute('aria-invalid'); });
  form.addEventListener('reset', () => { setStatus(status, ''); out.hidden = true; out.replaceChildren(); });
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(form).entries());
    for (const k of Object.keys(f)) f[k] = String(f[k]).trim();
    const hasLoc = (f.lat && f.lon) || f.address || (f.street1 && f.street2);
    if (!form.checkValidity()) {
      const bad = form.querySelector(':invalid');
      bad.setAttribute('aria-invalid', 'true'); bad.focus();
      setStatus(status, `Check ${form.querySelector(`label[for="${bad.id}"]`).textContent}.`, true);
      return;
    }
    if (!hasLoc) { setStatus(status, 'Add a location: Latitude and Longitude, the SR Address, or Street 1 and Street 2.', true); $('#f-addr').focus(); return; }
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    setStatus(status, 'Reading PRISM, GAZETTEER and NYC Open Data…');
    try {
      const b = await B.srBrief({ ...f, lat: f.lat || null, lon: f.lon || null, approx_directions: true });
      out.hidden = false;
      renderBrief(out, b);
      setStatus(status, `Done: ${b.corners.length} corners, ${b.permits.length} permits, ${b.facts.made_safe_before.length} earlier temporary repairs${b.errors.length ? `, ${b.errors.length} sources failed` : ''}.`, b.errors.length > 0);
      out.querySelector('h2').setAttribute('tabindex', '-1');
      out.querySelector('h2').focus();
    } catch (err) {
      setStatus(status, err.message, true);
    } finally {
      btn.disabled = false;
    }
  });
}

// ------------------------------------------------------------------ workbook
function setupBook() {
  const form = $('#book-form'), file = $('#b-file'), sheetSel = $('#b-sheet'), status = $('#book-status'), out = $('#book-result');
  const prog = $('#b-progress'), stopBtn = $('#b-stop');
  let records = {}, stop = false;
  file.addEventListener('change', async () => {
    sheetSel.replaceChildren(); sheetSel.disabled = true; records = {};
    const f = file.files[0];
    if (!f) return;
    if (!window.XLSX) { setStatus(status, 'The spreadsheet reader (SheetJS) did not load; check the network and reload.', true); return; }
    setStatus(status, `Reading ${f.name}…`);
    try {
      const wb = XLSX.read(await f.arrayBuffer(), { cellDates: true, dense: true });
      for (const name of wb.SheetNames) {
        const rows = XLSX.utils.sheet_to_json(wb.Sheets[name], { header: 1, raw: true, defval: null, blankrows: true });
        records[name] = readSrRows(rows, name);
      }
      const withSrs = wb.SheetNames.filter((n) => records[n].length);
      for (const n of wb.SheetNames) sheetSel.append(el('option', { value: n, disabled: records[n].length ? null : true }, `${n} (${records[n].length} SRs)`));
      sheetSel.disabled = !withSrs.length;
      if (withSrs.length) sheetSel.value = withSrs.includes('Richard') ? 'Richard' : withSrs[0];
      setStatus(status, withSrs.length ? `${withSrs.length} of ${wb.SheetNames.length} tabs hold SRs. Pick one and run.` : 'No tab has an SR Number or ARTs Tracking # header row.', !withSrs.length);
    } catch (err) {
      setStatus(status, `Could not read ${f.name}: ${err.message}`, true);
    }
  });
  stopBtn.addEventListener('click', () => { stop = true; setStatus(status, 'Stopping after the current SR…'); });
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const recs = records[sheetSel.value] || [];
    if (!recs.length) { setStatus(status, 'Open a workbook and pick a tab with SRs.', true); (file.files[0] ? sheetSel : file).focus(); return; }
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true; stop = false; stopBtn.hidden = false;
    prog.hidden = false; prog.max = recs.length; prog.value = 0;
    out.hidden = false; out.replaceChildren();
    const ok = [], failed = [];
    const tbody = el('tbody');
    const detail = el('div', { id: 'book-detail' });
    out.append(el('h2', {}, `${sheetSel.value}: ${recs.length} SRs`),
      el('div', { class: 'actions' },
        el('button', { type: 'button', class: 'btn', id: 'b-json' }, 'Download all JSON'),
        el('button', { type: 'button', class: 'btn', id: 'b-txt' }, 'Download summary.txt'),
        el('button', { type: 'button', class: 'btn', id: 'b-csv' }, 'Download CSV')),
      el('div', { class: 'table-wrap' }, el('table', {},
        el('caption', {}, 'One row per SR; open a row for its full brief'),
        el('thead', {}, el('tr', {}, ['Row', 'SR', 'Description', 'Candidate corners', 'Permits', 'Made safe before', 'In jagj-gttd', 'Rules these facts feed', 'Brief']
          .map((h) => el('th', { scope: 'col' }, h)))), tbody)),
      detail);
    $('#b-json').addEventListener('click', () => download(`${sheetSel.value}_briefs.json`, JSON.stringify({ ok, failed }, null, 1)));
    $('#b-txt').addEventListener('click', () => download('summary.txt', ok.map((b) => b.summary).join('\n\n') + '\n', 'text/plain'));
    $('#b-csv').addEventListener('click', () => {
      const q = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
      const lines = [['sr', 'row', 'description', 'corners', 'permits', 'made_safe_before', 'logged_in_jagj', 'feeds', 'errors'].join(',')];
      for (const b of ok) lines.push([b.sr, b._row, b.description, b.corners.filter((c) => c.within_radius || c.at_named_intersection).map((c) => `${c.cid} ${c.dir_label || '?'}`).join('; '),
        b.permits.length, b.facts.made_safe_before.length, b.facts.this_sr_logged_in_jagj, b.rules_these_facts_feed.join(' | '), b.errors.join(' | ')].map(q).join(','));
      for (const f of failed) lines.push([f.sr, f.row, f.description, '', '', '', '', '', f.error].map(q).join(','));
      download(`${sheetSel.value}_briefs.csv`, lines.join('\r\n') + '\r\n', 'text/csv');
    });
    for (const [i, rec] of recs.entries()) {
      if (stop) break;
      setStatus(status, `Briefing ${i + 1} of ${recs.length}: ${rec.sr}…`);
      try {
        const b = await B.srBrief({ ...recordToInput(rec), approx_directions: true });
        b._row = rec.row; ok.push(b);
        const open = el('button', { type: 'button', class: 'btn' }, 'Open');
        open.addEventListener('click', () => { renderBrief(detail, b, { headingLevel: 3 }); detail.querySelector('h3').setAttribute('tabindex', '-1'); detail.querySelector('h3').focus(); });
        tbody.append(el('tr', {},
          el('td', { class: 'num' }, String(rec.row)), el('td', {}, rec.sr), el('td', {}, rec.description ?? ''),
          el('td', {}, b.corners.filter((c) => c.within_radius || c.at_named_intersection).map((c) => `${c.cid} ${c.dir_label || '?'}`).join(', ') || 'none'),
          el('td', { class: 'num' }, String(b.permits.length)), el('td', { class: 'num' }, String(b.facts.made_safe_before.length)),
          el('td', {}, b.facts.this_sr_logged_in_jagj === null ? 'no SR number' : b.facts.this_sr_logged_in_jagj ? 'yes' : 'not yet'),
          el('td', {}, b.rules_these_facts_feed.length ? el('ul', {}, b.rules_these_facts_feed.map((x) => el('li', {}, x))) : '',
            b.errors.length ? el('p', { class: 'status error' }, `${b.errors.length} sources failed`) : ''),
          el('td', {}, open)));
      } catch (err) {
        failed.push({ sr: rec.sr, row: rec.row, description: rec.description, error: err.message });
        tbody.append(el('tr', {}, el('td', { class: 'num' }, String(rec.row)), el('td', {}, rec.sr), el('td', {}, rec.description ?? ''),
          el('td', { colspan: '6', class: 'status error' }, `Not briefed: ${err.message}`)));
      }
      prog.value = i + 1;
    }
    setStatus(status, `${stop ? 'Stopped. ' : ''}${ok.length} briefed, ${failed.length} not briefed.`, failed.length > 0);
    btn.disabled = false; stopBtn.hidden = true;
  });
}

// ------------------------------------------------------------------ settings
function setupSettings() {
  const form = $('#settings-form'), status = $('#settings-status');
  $('#s-token').value = store.get('token');
  $('#s-dyn').value = store.get('dynamics');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const okT = store.set('token', $('#s-token').value.trim());
    const okD = store.set('dynamics', $('#s-dyn').value.trim());
    makeBrief();
    setStatus(status, okT && okD ? 'Saved in this browser.' : 'This browser blocks local storage; the settings apply until the page is reloaded.', !(okT && okD));
  });
  $('#s-clear').addEventListener('click', () => { makeBrief(); setStatus(status, 'Cached answers cleared.'); });
}

// ------------------------------------------------------------------ start
document.addEventListener('DOMContentLoaded', () => {
  polyfillFocusgroup();
  setupTabs(document, (tab) => { if (tab.id === 'tab-one' && currentMap) setTimeout(() => currentMap.invalidateSize(), 0); });
  if (!window.proj4) {
    setStatus($('#one-status'), 'The coordinate library (proj4) did not load, so briefs cannot run. Check the network and reload.', true);
    return;
  }
  makeBrief();
  setupOne(); setupBook(); setupSettings();
  const p = new URLSearchParams(location.search);   // ?sr=...&borough=...&street1=...: prefill from a link
  for (const [k, v] of p) { const f = document.querySelector(`#one-form [name="${k}"]`); if (f) f.value = v; }
  if (p.get('run') === '1') $('#one-form').requestSubmit();
});
