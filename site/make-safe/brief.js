// brief.js: the nyc-opendata-mcp SR brief, ported to the browser (and Node 18+) from src/nycod/{geo,opendata,qow,sr}.py.
// Same queries, filters and sort orders as the Python package, which in turn matches the make-safe-batch skill's msb.py.
// test/parity.mjs runs both on the same live inputs and compares the results.
//
// createBrief({ proj4, fetch, appToken, dynamicsBase }) -> { srBrief, summaryText, parseSrAddress, cornersInWords, ... }

const ARCGIS = 'https://a841-dotweb01.nyc.gov/arcgis/rest/services';
const OPENDATA = 'https://data.cityofnewyork.us/resource';
const PERMITS = `${OPENDATA}/tqtj-sjs8.json`;
export const NYCSTREETS = 'https://nycstreets.nycdot.nyc/NYCStreets/Permit/Details/';
const EPSG2263 = '+proj=lcc +lat_0=40.1666666666667 +lon_0=-74 +lat_1=41.0333333333333 +lat_2=40.6666666666667 ' +
  '+x_0=300000 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=us-ft +no_defs +type=crs';

export const BORO_NUM = { MANHATTAN: 1, BRONX: 2, BROOKLYN: 3, QUEENS: 4, 'STATEN IS': 5, 'STATEN ISLAND': 5 };
const BORO_ALIASES = { M: 1, MN: 1, 'NEW YORK': 1, X: 2, BX: 2, K: 3, BK: 3, KINGS: 3, Q: 4, QN: 4, R: 5, SI: 5, RICHMOND: 5 };
export const OD_BORO = { 1: 'MANHATTAN', 2: 'BRONX', 3: 'BROOKLYN', 4: 'QUEENS', 5: 'STATEN ISLAND' };
const CODE = { 1: 'M', 2: 'X', 3: 'K', 4: 'Q', 5: 'R' };
const ORD = { FIRST: '1', SECOND: '2', THIRD: '3', FOURTH: '4', FIFTH: '5', SIXTH: '6', SEVENTH: '7', EIGHTH: '8',
  NINTH: '9', TENTH: '10', ELEVENTH: '11', TWELFTH: '12' };
export const RAMP_TYPES = ['RAMP', 'SIDEWALK', 'CURB', 'CORNER', 'PED', 'SIM/CWC', 'RESTORATION', 'TEST PIT', 'FOUNDATION', 'SIGNAL'];
const PERMIT_FIELDS = 'permitnumber,permitstatusshortdesc,permittypedesc,permitseriesshortdesc,permitissuedate,' +
  'issuedworkstartdate,issuedworkenddate,permithousenumber,onstreetname,fromstreetname,tostreetname,permitteename,' +
  'permitpurposecomments,permitlocationcomments';
const NYC311_FIELDS = 'unique_key,created_date,closed_date,agency,complaint_type,descriptor,incident_address,street_name,' +
  'cross_street_1,cross_street_2,intersection_street_1,intersection_street_2,address_type,status,' +
  'resolution_description,borough,bbl,latitude,longitude';
const NOM = { N: 0, NE: 45, E: 90, SE: 135, S: 180, SW: 225, W: 270, NW: 315 };
const OCT = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
const QUADS = ['NE', 'NW', 'SE', 'SW'];
const WORDS = { NORTHEAST: 'NE', 'NORTH EAST': 'NE', NORTHWEST: 'NW', 'NORTH WEST': 'NW', SOUTHEAST: 'SE',
  'SOUTH EAST': 'SE', SOUTHWEST: 'SW', 'SOUTH WEST': 'SW' };

const mod = (a, n) => ((a % n) + n) % n;   // Python's % on floats
const pyRound1 = (x) => Math.round(x * 10) / 10;

// ------------------------------------------------------------------ text helpers (no network)
export function norm(s) {
  s = String(s).toUpperCase().replace(/ /g, ' ').replace(/\s+/g, ' ').trim();
  return s.split(' ').map((w) => ORD[w] ?? w).join(' ');
}
export const sq = (s) => String(s).replace(/'/g, "''");
const nm = (x) => (x || '').toUpperCase().split(/\s+/).filter(Boolean).join(' ');
const title = (s) => s.replace(/[A-Za-z]+/g, (w) => w[0].toUpperCase() + w.slice(1).toLowerCase());

export function boroNum(b) {
  if (b === null || b === undefined || b === '') throw new Error('borough is required: a name (Queens), a code (Q) or a number (4)');
  if (typeof b === 'number' || /^\s*\d+\s*$/.test(String(b))) {
    const n = parseInt(b, 10);
    if (n >= 1 && n <= 5) return n;
    throw new Error(`borough number must be 1-5, got ${b}`);
  }
  const s = String(b).toUpperCase().split(/\s+/).filter(Boolean).join(' ');
  if (s in BORO_NUM) return BORO_NUM[s];
  if (s in BORO_ALIASES) return BORO_ALIASES[s];
  throw new Error(`unknown borough '${b}'; use Manhattan, Bronx, Brooklyn, Queens, Staten Island, a code M/X/K/Q/R or 1-5`);
}

export function odDate(s) {
  if (!s) return '';
  const [y, m, d] = String(s).slice(0, 10).replace(/\//g, '-').split('-');
  return `${parseInt(m, 10)}/${parseInt(d, 10)}/${y}`;
}

// 'YYYY-MM-DD' from the date formats Dynamics and Open Data use; null when not understood
export function parseDate(s) {
  if (s === null || s === undefined || s === '') return null;
  if (s instanceof Date) return isNaN(s) ? null : s.toISOString().slice(0, 10);
  s = String(s).trim();
  let m = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[T ].*)?$/);
  if (m) return valid(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+.*)?$/);
  if (m) return valid(+m[3], +m[1], +m[2]);
  return null;
  function valid(y, mo, d) {
    const t = new Date(Date.UTC(y, mo - 1, d));
    return t.getUTCMonth() === mo - 1 && t.getUTCDate() === d ? t.toISOString().slice(0, 10) : null;
  }
}
const addDays = (iso, n) => { const t = new Date(iso + 'T00:00:00Z'); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); };
const daysBetween = (a, b) => Math.round((Date.parse(a + 'T00:00:00Z') - Date.parse(b + 'T00:00:00Z')) / 86400000);
const today = () => { const t = new Date(); return new Date(Date.UTC(t.getFullYear(), t.getMonth(), t.getDate())).toISOString().slice(0, 10); };

export function parseSrAddress(addr) {
  const out = { raw: addr ?? null, house_number: null, street: null, cross_street: null, borough: null, neighborhood: null, zip: null };
  if (!addr || !String(addr).trim()) return out;
  const s = String(addr).replace(/ /g, ' ').split(/\s+/).filter(Boolean).join(' ');
  const parts = s.split(',').map((p) => p.trim());
  const head = parts[0];
  for (const p of parts.slice(1)) {
    const m = p.match(/^([A-Za-z ]+?)\s*(?:\(([^)]+)\))?$/);
    if (m && m[1].trim().toUpperCase() in BORO_NUM) {
      out.borough = m[1].trim().toUpperCase();
      out.neighborhood = m[2] ? title(m[2]) : null;
    } else if (/^\d{5}$/.test(p)) out.zip = p;
  }
  const sp = head.match(/^(.*?)(?:\s+(?:AND|&|AT)\s+|\s*\/\s*|\s*&\s*)(.*)$/i);
  if (sp && sp[1].trim() && sp[2].trim()) {
    out.street = norm(sp[1]); out.cross_street = norm(sp[2]);
    return out;
  }
  const m = head.match(/^(\d+[A-Z]?(?:-\d+[A-Z]?)?)\s+(.+)$/i);
  if (m) { out.house_number = m[1].toUpperCase(); out.street = norm(m[2]); } else out.street = norm(head);
  return out;
}

export function cornersInWords(text) {
  if (!text) return { quadrants: [], all_corners: false, sides: [] };
  const t = (' ' + String(text).toUpperCase().replace(/[^A-Z0-9 ]+/g, ' ') + ' ').split(/\s+/).filter(Boolean).join(' ');
  const found = new Set();
  for (const [w, q] of Object.entries(WORDS)) if (new RegExp(`\\b${w}\\b`).test(t)) found.add(q);
  for (const q of QUADS) if (new RegExp(`\\b${q}\\b`).test(t)) found.add(q);
  const all = /\bALL (?:4|FOUR) CORNERS\b|\bALL (?:THE )?CORNERS\b|\bEVERY CORNER\b|\bEACH CORNER\b/.test(t);
  const sides = [...new Set([...t.matchAll(/\b(NORTH|SOUTH|EAST|WEST)\s+SIDE\b/g)].map((m) => m[1]))].sort();
  return { quadrants: [...found].sort(), all_corners: all, sides };
}

export function cwcPermit(r) {
  return r.permitteename === 'NYC DEPT OF TRANSPORTATION' && (r.permittypedesc || '').startsWith('SIM/CWC');
}

export function permitLinks(permits, corners, complaintDate) {
  const mine = new Set(corners.map((c) => c.split(' ')[0].toUpperCase()));
  const quads = (r) => new Set([...(r.permitlocationcomments || '').toUpperCase().matchAll(/\b(NE|NW|SE|SW)\b/g)].map((m) => m[1]));
  const g = (r, k) => r[k] || '';
  let keep = permits.filter((r) => { const q = quads(r); return q.size === 0 || [...q].some((x) => mine.has(x)); });
  const pref = 'RAMP';
  const cmp = (f) => (a, b) => (f(a) < f(b) ? -1 : f(a) > f(b) ? 1 : 0);
  keep = keep.slice().sort(cmp((r) => (g(r, 'permittypedesc').includes(pref) ? 0 : 1)));
  keep.sort((a, b) => cmp((r) => g(r, 'issuedworkenddate'))(b, a));
  keep.sort(cmp((r) => (g(r, 'issuedworkenddate').slice(0, 10) < (complaintDate || '').slice(0, 10) ? 1 : 0)));
  const first = keep.find((r) => g(r, 'permittypedesc').includes(pref));
  if (first) { keep.splice(keep.indexOf(first), 1); keep.unshift(first); }
  return keep.map((r) => ({
    permit: r.permitnumber,
    label: `${r.permitnumber} (${g(r, 'permittypedesc').replace('SIM/CWC-', '').toLowerCase()}, ${g(r, 'permitteename')}, ` +
      `${g(r, 'permitstatusshortdesc').toLowerCase()}, ${odDate(g(r, 'issuedworkstartdate'))}-${odDate(g(r, 'issuedworkenddate'))})`,
    url: NYCSTREETS + r.permitnumber,
  }));
}

// ------------------------------------------------------------------ factory (network)
export function createBrief({ proj4, fetch: fetchFn = globalThis.fetch.bind(globalThis), appToken = '', dynamicsBase = '' } = {}) {
  if (!proj4) throw new Error('createBrief needs proj4');
  proj4.defs('EPSG:2263', EPSG2263);
  const toSP = (lon, lat) => proj4('EPSG:4326', 'EPSG:2263', [lon, lat]);
  const toLL = (X, Y) => proj4('EPSG:2263', 'EPSG:4326', [X, Y]);
  const toMerc = (X, Y) => proj4('EPSG:2263', 'EPSG:3857', [X, Y]);
  const cache = new Map();
  let calls = 0;

  async function getJson(url) {
    if (cache.has(url)) return cache.get(url);
    let err;
    for (let i = 0; i < 3; i++) {
      try {
        calls++;
        const r = await fetchFn(url, { headers: { Accept: 'application/json' } });
        if (!r.ok) {
          const body = (await r.text()).slice(0, 600);
          err = new Error(`HTTP ${r.status} for ${url}: ${body}`);
          if (r.status >= 400 && r.status < 500 && r.status !== 429) break;
        } else {
          const d = await r.json();
          if (d && !Array.isArray(d) && typeof d === 'object' && 'error' in d) {
            err = new Error(`server error for ${url}: ${JSON.stringify(d.error)}`);
            break;
          }
          cache.set(url, d);
          return d;
        }
      } catch (e) {
        err = new Error(`${e.name} for ${url}: ${e.message}`);
      }
      await new Promise((res) => setTimeout(res, 1500 * (i + 1)));
    }
    throw err;
  }
  const qs = (p) => new URLSearchParams(p).toString();
  function q(service, layer, params) {
    const p = { f: 'json', outFields: '*', returnGeometry: 'true', ...params };
    return getJson(`${ARCGIS}/${service}/MapServer/${layer}/query?${qs(p)}`);
  }
  function soda(ds, params) {
    const p = { $limit: 1000, ...params };
    if (appToken) p.$$app_token = appToken;
    return getJson(`${OPENDATA}/${ds}.json?${qs(p)}`);
  }
  const ft = (lat1, lon1, lat2, lon2) => {
    const [x1, y1] = toSP(lon1, lat1), [x2, y2] = toSP(lon2, lat2);
    return Math.hypot(x2 - x1, y2 - y1);
  };
  function streetsmart(X, Y, half = 50) {
    const [x, y] = toMerc(X, Y); const h = half * 0.3048;
    return `https://streetsmart.cyclomedia.com/streetsmart/?mq=${(x - h).toFixed(2)};${(y - h).toFixed(2)};${(x + h).toFixed(2)};${(y + h).toFixed(2)}&msrs=EPSG:3857`;
  }
  const dynamicsLink = (guid) => (dynamicsBase && guid ? dynamicsBase + String(guid).trim().replace(/^\{|\}$/g, '') : null);

  // ---- PRISM / GAZETTEER
  function cornerRec(f, ref) {
    const a = f.attributes, g = f.geometry;
    const bbl = a.Block !== null && a.Block !== undefined
      ? `${Math.trunc(a.BoroughCode)}${String(Math.trunc(a.Block)).padStart(5, '0')}${String(Math.trunc(a.Lot)).padStart(4, '0')}` : null;
    const [X, Y] = toSP(g.x, g.y);
    const r = { cid: a.CMTCornerID, dir: a.CornerDirection, ctype: a.CornerType, on: a.OnStreetName, frm: a.FromStreetName,
      bbl, block: a.Block ?? null, lot: a.Lot ?? null, lat: g.y, lon: g.x, X, Y, link: streetsmart(X, Y) };
    if (ref) r.dist = ft(ref[0], ref[1], g.y, g.x);
    return r;
  }
  async function cornersNear(lat, lon, distFt = 100) {
    const d = await q('PRISM/PRISM_CORNERS', 0, { geometry: `${lon},${lat}`, geometryType: 'esriGeometryPoint', inSR: 4326,
      spatialRel: 'esriSpatialRelIntersects', distance: distFt, units: 'esriSRUnit_Foot', outSR: 4326 });
    return d.features.map((f) => cornerRec(f, [lat, lon])).sort((a, b) => a.dist - b.dist);
  }
  async function cornersById(ids) {
    ids = [...new Set(ids.map((i) => parseInt(i, 10)))].sort((a, b) => a - b);
    const out = [];
    for (let i = 0; i < ids.length; i += 200)
      out.push(...(await q('PRISM/PRISM_CORNERS', 0, { where: `CMTCornerID IN (${ids.slice(i, i + 200).join(',')})`, outSR: 4326 })).features);
    return out.map((f) => cornerRec(f));
  }
  async function intersection(a, b, boro) {
    a = norm(a); b = norm(b);
    const w = `BoroughCode=${boroNum(boro)} AND ((OnStreetName='${sq(a)}' AND FromStreetName='${sq(b)}') OR ` +
      `(OnStreetName='${sq(b)}' AND FromStreetName='${sq(a)}'))`;
    return (await q('PRISM/PRISM_CORNERS', 0, { where: w, outSR: 4326 })).features.map((f) => cornerRec(f));
  }
  async function rampsByCorner(cids) {
    const out = {}; const ids = [...new Set(cids.map((i) => parseInt(i, 10)))].sort((a, b) => a - b);
    for (let i = 0; i < ids.length; i += 200) {
      const d = await q('PRISM/PRISM_RAMPS', 0, { where: `CMTCornerID IN (${ids.slice(i, i + 200).join(',')})`, outSR: 4326 });
      for (const f of d.features) {
        const a = f.attributes, g = f.geometry;
        const byRamp = (out[a.CMTCornerID] ??= new Map());
        const prev = byRamp.get(a.CMTRampID);
        if (prev) {
          if (!String(prev.street).split(' / ').includes(a.OnStreetName)) prev.street += ' / ' + a.OnStreetName;
          continue;
        }
        byRamp.set(a.CMTRampID, { ramp: a.CMTRampID, type: a.RampType, street: a.OnStreetName, lat: g.y, lon: g.x });
      }
    }
    return Object.fromEntries(Object.entries(out).map(([k, v]) => [k, [...v.values()]]));
  }
  const bearing = (x0, y0, x, y) => mod((Math.atan2(x - x0, y - y0) * 180) / Math.PI + 360, 360);
  async function approxDir(lat, lon, on, frm) {
    const recs = await cornersNear(lat, lon, 900);
    const key = (r) => [r.on, r.frm].sort().join('\u0001');
    const groups = new Map();
    for (const r of recs) { const k = key(r); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(r); }
    const mine = (groups.get([on, frm].sort().join('\u0001')) || []).filter((r) => r.dist < 400);
    if (mine.length < 2) return null;
    const centroid = (rs) => [rs.reduce((s, r) => s + r.X, 0) / rs.length, rs.reduce((s, r) => s + r.Y, 0) / rs.length];
    const local = mine.filter((r) => r.dir in NOM);
    const pool = local.length ? [[mine, local]]
      : [...groups.values()].filter((rs) => rs.length >= 3 && rs.some((r) => r.dir in NOM)).map((rs) => [rs, rs.filter((r) => r.dir in NOM)]);
    const offs = [];
    for (const [rs, lab] of pool) {
      const [cx, cy] = centroid(rs);
      for (const r of lab) offs.push(((NOM[r.dir] - bearing(cx, cy, r.X, r.Y)) * Math.PI) / 180);
    }
    if (!offs.length) return null;
    const rot = (Math.atan2(offs.reduce((s, o) => s + Math.sin(o), 0), offs.reduce((s, o) => s + Math.cos(o), 0)) * 180) / Math.PI;
    const [cx, cy] = centroid(mine); const [x, y] = toSP(lon, lat);
    return OCT[Math.floor(mod(mod(bearing(cx, cy, x, y) + rot, 360) + 22.5, 360) / 45)];
  }
  const hnPad = (hn) => {
    if (!hn.includes('-')) return hn;
    const i = hn.indexOf('-'); const a = hn.slice(0, i), c = hn.slice(i + 1);
    return /^\d+$/.test(c) ? `${a}-${String(parseInt(c, 10)).padStart(3, '0')}` : hn;
  };
  async function locateAddress(hn, street, boro) {
    const bn = boroNum(boro); street = norm(street);
    const lion = await q('GAZETTEER/LION', 0, { where: `Street='${sq(street)}' AND (LBoro=${bn} OR RBoro=${bn})`, outFields: 'StreetCode', returnGeometry: 'false' });
    const codes = [...new Set(lion.features.map((f) => f.attributes.StreetCode).filter(Boolean))].sort();
    for (const c of codes) {
      const fs = (await q('GAZETTEER/AddressPoint', 0, { where: `HOUSE_NUMBER='${hnPad(hn)}' AND B7SC_ACTUAL LIKE '${c}%'`,
        outFields: 'HOUSE_NUMBER,B7SC_ACTUAL', outSR: 4326 })).features;
      if (fs.length) return [fs[0].geometry.y, fs[0].geometry.x, 'GAZETTEER AddressPoint'];
    }
    const pl = (await q('GAZETTEER/MapPLUTO', 0, { where: `Address='${sq(hn + ' ' + street)}' AND BoroCode=${bn}`,
      outFields: 'BBL,Latitude,Longitude', returnGeometry: 'false' })).features;
    if (pl.length) return [pl[0].attributes.Latitude, pl[0].attributes.Longitude, 'MapPLUTO lot'];
    const n = parseInt(hn.replace(/-/g, ''), 10);
    if (Number.isNaN(n) || !/^\d+$/.test(hn.replace(/-/g, ''))) return null;
    const segs = (await q('GAZETTEER/LION', 0, { where: `Street='${sq(street)}' AND (LBoro=${bn} OR RBoro=${bn})`,
      outFields: 'FromLeft,ToLeft,FromRight,ToRight,SegmentID', outSR: 4326 })).features;
    for (const f of segs) {
      const a = f.attributes;
      for (const [lo, hi] of [[a.FromLeft, a.ToLeft], [a.FromRight, a.ToRight]]) {
        if (lo && hi && Math.min(lo, hi) <= n && n <= Math.max(lo, hi) && mod(lo, 2) === mod(n, 2)) {
          const pts = f.geometry.paths.flat();
          const t = hi === lo ? 0.5 : (n - lo) / (hi - lo);
          const i = Math.min(Math.trunc(t * (pts.length - 1)), pts.length - 2); const fr = t * (pts.length - 1) - i;
          return [pts[i][1] + (pts[i + 1][1] - pts[i][1]) * fr, pts[i][0] + (pts[i + 1][0] - pts[i][0]) * fr, 'LION address-range interpolation'];
        }
      }
    }
    return null;
  }
  async function lionNodes(aLike, bLike, boro) {
    const bn = boroNum(boro);
    async function segs(p) {
      const out = new Map();
      const d = await q('GAZETTEER/LION', 0, { where: `Street LIKE '${sq(p)}' AND (LBoro=${bn} OR RBoro=${bn})`,
        outFields: 'Street,NodeIDFrom,NodeIDTo,XFrom,YFrom,XTo,YTo', returnGeometry: 'false' });
      for (const f of d.features) {
        const a = f.attributes;
        out.set(a.NodeIDFrom, [a.XFrom, a.YFrom, a.Street]); out.set(a.NodeIDTo, [a.XTo, a.YTo, a.Street]);
      }
      return out;
    }
    const A = await segs(aLike), B = await segs(bLike);
    const res = [];
    for (const [n, v] of A) if (B.has(n)) { const [lon, lat] = toLL(v[0], v[1]); res.push({ node: n, lat, lon, a: v[2], b: B.get(n)[2] }); }
    return res;
  }
  async function lotAt(lat, lon) {
    const fs = (await q('GAZETTEER/MapPLUTO', 0, { geometry: `${lon},${lat}`, geometryType: 'esriGeometryPoint', inSR: 4326,
      spatialRel: 'esriSpatialRelIntersects', outFields: 'BBL,Address', returnGeometry: 'false' })).features;
    if (!fs.length) return [null, null];
    const a = fs[0].attributes;
    return [a.BBL ? String(Math.trunc(a.BBL)).padStart(10, '0') : null, a.Address ?? null];
  }

  // ---- Open Data
  function permits(where, limit = 1000) {
    const p = { $select: PERMIT_FIELDS, $where: where, $order: 'permitissuedate DESC', $limit: limit };
    if (appToken) p.$$app_token = appToken;
    return getJson(`${PERMITS}?${qs(p)}`);
  }
  async function permitsAt(boroName, a, b, since, keep = RAMP_TYPES) {
    const [A, B] = [a, b].map((x) => norm(x).split(' ').join('%'));
    const w = `boroughname='${boroName}' AND permitissuedate >= '${since}' AND (` +
      `(upper(onstreetname) like '%${A}%' AND (upper(fromstreetname) like '%${B}%' OR upper(tostreetname) like '%${B}%')) OR ` +
      `(upper(onstreetname) like '%${B}%' AND (upper(fromstreetname) like '%${A}%' OR upper(tostreetname) like '%${A}%')))`;
    const na = norm(a), nb = norm(b);
    const exact = (r) => { const on = nm(r.onstreetname), fr = nm(r.fromstreetname), to = nm(r.tostreetname);
      return (on === na && (nb === fr || nb === to)) || (on === nb && (na === fr || na === to)); };
    const rows = (await permits(w)).filter(exact);
    return keep === null ? rows : rows.filter((r) => keep.some((k) => (r.permittypedesc || '').toUpperCase().includes(k)));
  }
  async function permitsAddress(boroName, hn, street, since) {
    const w = `boroughname='${boroName}' AND permitissuedate >= '${since}' AND permithousenumber='${sq(hn)}' ` +
      `AND upper(onstreetname) like '%${norm(street).split(' ').join('%')}%'`;
    return (await permits(w)).filter((r) => nm(r.onstreetname) === norm(street));
  }
  async function rampProgram(cids) {
    const ids = cids.map((c) => parseInt(c, 10)).join(',');
    if (!ids) return {};
    return Object.fromEntries((await soda('e7gc-ub6z', { $where: `cornerid in (${ids})` })).map((r) => [parseInt(r.cornerid, 10), r]));
  }
  function rampComplaints(cids, sr) {
    if (sr) return soda('jagj-gttd', { $where: `complaint_id like '%${sq(sr.replace('311-', ''))}%'` });
    const ids = (cids || []).map((c) => parseInt(c, 10)).join(',');
    return ids ? soda('jagj-gttd', { $where: `cmt_corner_id in (${ids})`, $order: 'complaint_date DESC' }) : Promise.resolve([]);
  }
  const capitalNear = (lat, lon, meters = 60) => soda('97nd-ff3i', { $where: `within_circle(the_geom, ${lat}, ${lon}, ${meters})` });
  function nyc311Near(lat, lon, meters = 50, since = null, dotSidewalkOnly = true, limit = 200) {
    let w = `within_circle(location, ${Number(lat)}, ${Number(lon)}, ${Number(meters)})`;
    if (since) w += ` AND created_date >= '${sq(since)}'`;
    if (dotSidewalkOnly) w += " AND agency='DOT' AND complaint_type in ('Sidewalk Condition', 'Curb Condition')";
    return soda('erm2-nwe9', { $select: NYC311_FIELDS, $where: w, $order: 'created_date DESC', $limit: limit });
  }

  // ---- the brief
  async function srBrief(o = {}) {
    const errors = [], notes = [];
    const call = async (label, fn, dflt) => { try { return await fn(); } catch (e) { errors.push(`${label}: ${e.message}`); return dflt; } };
    let sr = (o.sr || '').trim() || null;
    if (sr && !/^311-\d{8}$/.test(sr)) {
      const m = sr.match(/\b311-\d{8}\b/);
      notes.push(`SR '${sr}' is not in 311-xxxxxxxx form` + (m ? `; using ${m[0]}` : ''));
      sr = m ? m[0] : sr;
    }
    const parsed = parseSrAddress(o.address || null);
    const bn = boroNum(o.borough || parsed.borough);
    const boroName = OD_BORO[bn];
    const cdate = parseDate(o.complaint_date);
    if (!cdate) notes.push(o.complaint_date ? `Complaint date '${o.complaint_date}' not understood; using today.`
      : 'No complaint date given: the permit window and the made-safe-on-or-after check use today.');
    const ref = cdate || today();
    const s1 = o.street1 ? norm(o.street1) : parsed.cross_street ? parsed.street : null;
    const s2 = o.street2 ? norm(o.street2) : parsed.cross_street;
    const hn = parsed.house_number;
    const addrStreet = hn ? parsed.street : null;
    const words = cornersInWords([o.description, o.location_details].filter(Boolean).join(' '));
    const radius = Number(o.radius_ft ?? 100);
    const years = Number(o.permit_years ?? 1);

    let point = null, pointSrc = null;
    const lat = o.lat === '' || o.lat === undefined || o.lat === null ? null : Number(o.lat);
    const lon = o.lon === '' || o.lon === undefined || o.lon === null ? null : Number(o.lon);
    if (lat !== null && lon !== null && !Number.isNaN(lat) && !Number.isNaN(lon)) { point = [lat, lon]; pointSrc = 'Dynamics Lat/Lon'; }
    if (hn && addrStreet) {
      const ap = await call('locate_address', () => locateAddress(hn, addrStreet, bn), null);
      if (ap) {
        if (point) {
          const gap = ft(point[0], point[1], ap[0], ap[1]);
          if (gap > 100) {
            notes.push(`Dynamics point is ${gap.toFixed(0)} ft from the ${ap[2]} for ${hn} ${addrStreet}; per the corners note the address point is used. Check the address in imagery.`);
            point = [ap[0], ap[1]]; pointSrc = `${ap[2]} (Dynamics point ${gap.toFixed(0)} ft away)`;
          }
        } else { point = [ap[0], ap[1]]; pointSrc = ap[2]; }
      } else if (!point) notes.push(`${hn} ${addrStreet} did not geocode (AddressPoint, MapPLUTO and LION all empty).`);
    }

    let ix = [], ixSrc = null;
    if (s1 && s2) {
      ix = await call('intersection', () => intersection(s1, s2, bn), []);
      ixSrc = 'PRISM names';
      if (!ix.length) {
        const [pa, pb] = [s1, s2].map((x) => '%' + x.split(' ').join('%') + '%');
        const nodes = await call('lion_nodes', () => lionNodes(pa, pb, bn), []);
        if (nodes.length) {
          const n0 = nodes[0];
          ix = await call('corners_near (LION node)', () => cornersNear(n0.lat, n0.lon, 100), []);
          ixSrc = `LION node ${n0.node} (${n0.a} / ${n0.b})`;
          if (nodes.length > 1) notes.push(`${nodes.length} LION nodes share ${s1} and ${s2}; used node ${n0.node}. Others: ${nodes.slice(1, 5).map((n) => n.node).join(', ')}.`);
          if (!point) { point = [n0.lat, n0.lon]; pointSrc = ixSrc; }
        } else notes.push(`No PRISM corners and no shared LION node for ${s1} and ${s2} in ${boroName}.`);
      } else if (!point) {
        point = [ix.reduce((s, c) => s + c.lat, 0) / ix.length, ix.reduce((s, c) => s + c.lon, 0) / ix.length];
        pointSrc = 'centre of the PRISM corners at the intersection';
      }
    }
    if (!point && !ix.length) throw new Error('No location: give lat/lon, an SR Address that geocodes, or two streets that meet.');

    const near = point ? await call('corners_near', () => cornersNear(point[0], point[1], radius), []) : [];
    const [lotBbl, lotAddr] = point ? await call('lot_at', () => lotAt(point[0], point[1]), [null, null]) : [null, null];
    let reference = null;
    if (point && !near.length && !ix.length) {
      const wide = await call('corners_near (reference)', () => cornersNear(point[0], point[1], 800), []);
      const same = wide.filter((c) => addrStreet && (c.on === addrStreet || c.frm === addrStreet));
      const blk = same.filter((c) => lotBbl && c.block !== null && Math.trunc(c.block) === parseInt(lotBbl.slice(1, 6), 10));
      reference = (blk.length ? blk : same.length ? same : wide)[0] || null;
    }
    const pairs = [];
    const pk = (a, b) => [a, b].sort().join('\u0001');
    for (const c of [...ix, ...near, ...(reference ? [reference] : [])])
      if (!pairs.some(([a, b]) => pk(a, b) === pk(c.on, c.frm))) pairs.push([c.on, c.frm]);
    pairs.splice(4);
    const byCid = new Map();
    for (const c of [...ix, ...near, ...(reference ? [reference] : [])]) if (!byCid.has(c.cid)) byCid.set(c.cid, c);
    for (const [on, frm] of pairs)
      for (const c of await call(`intersection ${on} / ${frm}`, () => intersection(on, frm, bn), [])) if (!byCid.has(c.cid)) byCid.set(c.cid, c);
    const allCids = [...byCid.keys()].sort((a, b) => a - b);
    const ramps = allCids.length ? await call('ramps_by_corner', () => rampsByCorner(allCids), {}) : {};
    const approx = {};
    if (o.approx_directions !== false)
      for (const [cid, c] of byCid) if (!c.dir) approx[cid] = await call(`approx_dir ${cid}`, () => approxDir(c.lat, c.lon, c.on, c.frm), null);

    const nearIds = new Set(near.map((c) => c.cid)), ixIds = new Set(ix.map((c) => c.cid));
    const cornerOut = (r, ap) => {
      const d = {}; for (const k of ['cid', 'dir', 'ctype', 'on', 'frm', 'bbl', 'lat', 'lon', 'X', 'Y', 'link']) d[k] = r[k] ?? null;
      if (r.dist !== undefined) d.dist_ft = pyRound1(r.dist);
      d.dir_label = !d.dir && ap ? `${ap} (approx.)` : d.dir || null;
      d.ramps = ramps[r.cid] || [];
      d.on_sr_lot = !!(lotBbl && r.bbl === lotBbl);
      return d;
    };
    const corners = allCids.map((cid) => cornerOut(byCid.get(cid), approx[cid]));
    for (const c of corners) {
      if (point) c.dist_ft = pyRound1(ft(point[0], point[1], c.lat, c.lon));
      c.within_radius = nearIds.has(c.cid); c.at_named_intersection = ixIds.has(c.cid);
      c.named_by_caller = !!(c.dir && words.quadrants.includes(c.dir));
    }
    const key = (c) => [c.within_radius ? 0 : 1, c.dist_ft ?? 1e9, c.on || '', c.dir || ''];
    corners.sort((a, b) => { const x = key(a), y = key(b); for (let i = 0; i < 4; i++) { if (x[i] < y[i]) return -1; if (x[i] > y[i]) return 1; } return 0; });

    let rule;
    if (words.quadrants.length && (ix.length || near.length))
      rule = `Caller names ${words.quadrants.join(', ')}: the corners table says only those corners. Confirm in imagery; a quadrant word can describe the caller, not the defect.`;
    else if (words.all_corners || (ix.length && !hn)) rule = 'Intersection with no corner named: every corner there (four -> ALL_FOUR_CORNERS).';
    else if (hn && near.length) rule = `Street address: corners within ${radius} ft of the SR point. If the caller describes their own corner/house/property, the corner on the address's own tax lot (on_sr_lot).`;
    else if (reference) rule = 'Mid-block, no corner within 100 ft: reference corner = nearest on the same street and tax block. Look at the address in imagery first: a large mid-block building is not a corner (P12, building ramp -> DOB).';
    else rule = 'No corners table row fits the input cleanly; settle the corners from the Description and imagery.';
    if (words.sides.length) rule += ` Caller mentions the ${words.sides.map((s) => s.toLowerCase()).join(', ')} side: a non-quadrant label goes in the form's Median.`;

    const prog = allCids.length ? await call('ramp_program (e7gc-ub6z)', () => rampProgram(allCids), {}) : {};
    const hist = allCids.length ? await call('ramp_complaints (jagj-gttd)', () => rampComplaints(allCids), []) : [];
    const thisSr = sr ? await call('ramp_complaints by SR', () => rampComplaints(null, sr), []) : [];

    const since = addDays(ref, -Math.round(365 * years));
    const completions = Object.values(prog).filter((r) => r.construc_1).map((r) => parseDate(r.construc_1.slice(0, 10).replace(/\//g, '-'))).filter(Boolean).sort();
    const since2 = completions.length && completions[0] < since ? completions[0] : null;
    const streetPairs = pairs.slice();
    if (s1 && s2 && !streetPairs.some(([a, b]) => pk(a, b) === pk(s1, s2))) streetPairs.push([s1, s2]);
    const permitRows = new Map(), permitQueries = [];
    for (const [a, b] of streetPairs)
      for (const start of [since, ...(since2 ? [since2] : [])]) {
        const rows = await call(`permits_at ${a} / ${b}`, () => permitsAt(boroName, a, b, start), []);
        permitQueries.push({ kind: 'intersection', a, b, since: start, rows: rows.length });
        for (const r of rows) if (!permitRows.has(r.permitnumber)) permitRows.set(r.permitnumber, r);
      }
    if (hn && addrStreet) {
      const rows = await call(`permits_address ${hn} ${addrStreet}`, () => permitsAddress(boroName, hn, addrStreet, since), []);
      permitQueries.push({ kind: 'address', house_number: hn, street: addrStreet, since, rows: rows.length });
      for (const r of rows) if (!permitRows.has(r.permitnumber)) permitRows.set(r.permitnumber, r);
    }
    // newest first; permit number breaks ties (Socrata returns same-timestamp rows in no fixed order)
    const permitList = [...permitRows.values()].sort((a, b) => {
      const da = a.permitissuedate || '', db = b.permitissuedate || '';
      if (da !== db) return da < db ? 1 : -1;
      return a.permitnumber < b.permitnumber ? -1 : a.permitnumber > b.permitnumber ? 1 : 0;
    });

    const capital = [], seen = new Set();
    for (const c of corners) {
      if (!c.within_radius && !c.at_named_intersection) continue;
      for (const r of await call(`capital_near ${c.cid}`, () => capitalNear(c.lat, c.lon, 60), [])) {
        if (seen.has(r.projectid)) continue;
        seen.add(r.projectid);
        const d = {}; for (const k of ['projectid', 'projtitle', 'fmsid', 'leadagency', 'projectt_1', 'projectsta', 'construc_2', 'onstreetna', 'fromstreet', 'tostreetna']) d[k] = r[k] ?? null;
        d.near_cid = c.cid; capital.push(d);
      }
    }
    const n311 = point ? await call('311 near (erm2-nwe9)', () => nyc311Near(point[0], point[1], Number(o.nyc311_meters ?? 50), addDays(ref, -365)), []) : [];

    const madeSafe = [];
    for (const r of hist)
      for (const d of [parseDate(r.temp_repair_date), parseDate(r.date_second_temp_repair)].filter(Boolean))
        madeSafe.push({ cid: parseInt(r.cmt_corner_id, 10), complaint_id: r.complaint_id ?? null, complaint_date: odDate(r.complaint_date),
          temp_repair_date: odDate(d), temp_repair_type: r.temp_repair_type ?? null, on_or_after_complaint: !!(cdate && d >= cdate),
          days_before_complaint: daysBetween(ref, d) });
    const progOut = {};
    for (const [cid, r] of Object.entries(prog))
      progOut[cid] = { status: r.construc_2 ?? null, construction_type: r.constructi ?? null, completed: odDate(r.construc_1), street1: r.street_nam ?? null, street2: r.street_n_1 ?? null };
    const pclass = (r) => {
      const t = (r.permittypedesc || '').toUpperCase(), tags = [];
      if (cwcPermit(r)) tags.push('CWC (DOT in-house)');
      if (t.includes('RAMP')) tags.push('ped ramp');
      if (t.includes('TEMPORARY PEDESTRIAN WALK')) tags.push('temporary pedestrian walk');
      if (t.includes('TEST PIT')) tags.push('test pit');
      if (t.includes('FOUNDATION')) tags.push('foundation');
      if (t.includes('RESTORATION')) tags.push('restoration');
      if (t.includes('SIGNAL')) tags.push('signal');
      const st = (r.permitstatusshortdesc || '').toUpperCase();
      if (st.includes('DELINQUENT')) tags.push('DELINQUENT (missed a deadline)');
      if (st.includes('EXPIRED UNDER GUARANTEE')) tags.push('EXPIRED UNDER GUARANTEE (still responsible for restoration)');
      return tags;
    };
    const permitsOut = permitList.map((r) => {
      const d = {}; for (const k of PERMIT_FIELDS.split(',')) d[k] = r[k] ?? null;
      d.tags = pclass(r);
      const end = parseDate(r.issuedworkenddate), start = parseDate(r.issuedworkstartdate), iss = parseDate(r.permitissuedate);
      d.in_force_on_complaint_date = !!(cdate && start && end && start <= cdate && cdate <= end);
      d.issued_days_before_complaint = iss ? daysBetween(ref, iss) : null;
      d.nycstreets = NYCSTREETS + r.permitnumber;
      return d;
    });
    const keyPermits = permitList.filter((r) => { const j = pclass(r).join(' ');
      return ['CWC', 'ped ramp', 'temporary pedestrian walk', 'test pit', 'foundation', 'restoration', 'signal'].some((t) => j.includes(t)); });
    const labels = corners.filter((c) => c.dir_label && (c.within_radius || c.at_named_intersection)).map((c) => c.dir_label);
    const links = permitLinks(keyPermits, labels.length ? labels : ['--'], cdate || today());

    const logged = [...new Set(thisSr.filter((r) => r.cmt_corner_id).map((r) => parseInt(r.cmt_corner_id, 10)))].sort((a, b) => a - b);
    const typeHas = (r, s) => (r.permittypedesc || '').toUpperCase().includes(s);
    const facts = {
      this_sr_logged_in_jagj: sr ? thisSr.length > 0 : null,
      this_sr_logged_corners: logged,
      logged_corners_not_in_candidates: logged.filter((c) => !byCid.has(c)),
      made_safe_before: madeSafe,
      made_safe_on_or_after_complaint: madeSafe.filter((m) => m.on_or_after_complaint),
      earlier_complaints: hist.filter((r) => r.complaint_id !== sr).slice(0, 40).map((r) => ({ cid: parseInt(r.cmt_corner_id, 10),
        complaint_id: r.complaint_id ?? null, complaint_date: odDate(r.complaint_date), temp_repair_feasible: r.temp_repair_feasible ?? null })),
      cwc_permits: permitList.filter(cwcPermit).map((r) => r.permitnumber),
      ramp_permits: permitList.filter((r) => typeHas(r, 'RAMP')).map((r) => r.permitnumber),
      temporary_pedestrian_walk_permits: permitList.filter((r) => typeHas(r, 'TEMPORARY PEDESTRIAN WALK')).map((r) => r.permitnumber),
      delinquent_or_under_guarantee: permitList.filter((r) => ['DELINQUENT', 'EXPIRED UNDER GUARANTEE'].some((s) => (r.permitstatusshortdesc || '').toUpperCase().includes(s)))
        .map((r) => `${r.permitnumber} ${r.permitstatusshortdesc}`),
      ramp_program_completed: Object.entries(progOut).filter(([, v]) => v.completed).map(([cid, v]) => `${cid} ${v.completed} (${v.construction_type})`),
      corners_without_program_row: allCids.filter((c) => !(c in prog)),
      capital_projects: capital.length,
      public_311_ramp_or_curb_nearby: n311.length,
    };
    const feeds = [];
    if (facts.made_safe_on_or_after_complaint.length) feeds.push('Temporary repair on or after the complaint date: P58 (no Make Safe, N.TAR) if PavementWorks agrees.');
    else if (madeSafe.length) feeds.push('Corner made safe before: see made-safe-before (new Make Safe + PRP status email if the defect is obvious; PRP status email only if made safe long ago and defects not obvious).');
    if (facts.cwc_permits.length || facts.ramp_permits.length) feeds.push('CWC or ramp-contractor permits at the corner: confirm Quality of Work and the permittee (Stage 7; QoW routing). Ped ramp permit to screenshot is first in permit_links.');
    if (facts.temporary_pedestrian_walk_permits.length) feeds.push('Permitted temporary pedestrian walk: with a temporary-sounding ramp -> HIQA (decision order step 6).');
    if (facts.delinquent_or_under_guarantee.length) feeds.push('DELINQUENT / EXPIRED UNDER GUARANTEE permits: note in the index.');
    if (capital.length || facts.ramp_program_completed.length) feeds.push('Capital project or ramp program completion nearby: possibly QoW for that contract; keep only when photos or imagery tie the defect to that work.');
    if (sr && !thisSr.length) feeds.push('This SR is not in jagj-gttd yet (logging lags about a week).');
    if (facts.logged_corners_not_in_candidates.length) feeds.push('jagj-gttd logs this SR on corners outside the candidates: check the SR point and corners.');

    const out = {
      sr, borough: boroName, borough_code: CODE[bn], complaint_date: cdate, description: o.description || null,
      additional_location_details: o.location_details || null, dynamics_link: o.guid ? dynamicsLink(o.guid) : null,
      input: { address: o.address || null, parsed, street1: s1, street2: s2, lat: o.lat ?? null, lon: o.lon ?? null },
      point: point ? { lat: point[0], lon: point[1], source: pointSrc } : null,
      sr_lot: { bbl: lotBbl, address: lotAddr }, caller_corner_words: words, corners_rule: rule,
      intersection_source: ixSrc, corners,
      reference_corner: reference ? cornerOut(reference, approx[reference.cid]) : null,
      ramp_program: progOut, ramp_complaints_history: hist, ramp_complaints_this_sr: thisSr,
      permits: permitsOut, permit_queries: permitQueries, permit_window_since: since, permit_window_extended_to: since2,
      permit_links: links, capital_projects: capital, public_311_nearby: n311,
      facts, rules_these_facts_feed: feeds, notes, errors,
      not_covered: ['routing and type (decision order, type table)', 'corner choice against imagery (H2)',
        'Cyclomedia street views and visual check', 'PavementWorks export (signed-in)',
        'NYCStreets permit pages (signed-in, DOT network)', 'Dynamics customer photos and edits'],
      generated: new Date().toISOString().slice(0, 19),
    };
    out.summary = summaryText(out);
    return out;
  }

  return { srBrief, summaryText, cornersNear, cornersById, intersection, rampsByCorner, approxDir, locateAddress, lionNodes,
    lotAt, permitsAt, permitsAddress, rampProgram, rampComplaints, capitalNear, nyc311Near, streetsmart, dynamicsLink,
    stats: () => ({ requests: calls, cached: cache.size }) };
}

export function summaryText(b) {
  const L = [`${b.sr || '(no SR)'}  ${b.borough}  complaint ${b.complaint_date || 'date not given'}`];
  if (b.description) L.push(`  Description: "${b.description}"`);
  const p = b.point;
  if (p) L.push(`  Point: ${p.lat.toFixed(6)}, ${p.lon.toFixed(6)} (${p.source}); lot ${b.sr_lot.bbl || 'none found'}`);
  L.push(`  Corners rule: ${b.corners_rule}`);
  for (const c of b.corners) {
    const tag = [['within radius', c.within_radius], ['named intersection', c.at_named_intersection], ['on SR lot', c.on_sr_lot],
      ['named by caller', c.named_by_caller]].filter(([, on]) => on).map(([t]) => t).join(', ');
    L.push(`  Corner ${c.cid} ${c.dir_label || 'direction blank'} ${c.on} / ${c.frm}${c.dist_ft !== undefined && c.dist_ft !== null ? ' ' + c.dist_ft + ' ft' : ''}; ${c.ramps.length} ramps${tag ? '; ' + tag : ''}`);
    const pr = b.ramp_program[String(c.cid)];
    L.push('    Program: ' + (pr ? `${pr.status}, ${pr.construction_type}` + (pr.completed ? `, completed ${pr.completed}` : '') : 'no row'));
  }
  const f = b.facts;
  if (b.sr) L.push(`  This SR in jagj-gttd: ${f.this_sr_logged_in_jagj ? 'yes, corners ' + f.this_sr_logged_corners.join(', ') : 'not yet'}`);
  for (const m of f.made_safe_before) L.push(`  Temp repair ${m.temp_repair_date} on ${m.cid} (${m.complaint_id}, ${m.complaint_date})${m.on_or_after_complaint ? ' ON/AFTER complaint' : ''}`);
  L.push(`  Permits since ${b.permit_window_since}${b.permit_window_extended_to ? ' (and from ' + b.permit_window_extended_to + ')' : ''}: ${b.permits.length}`);
  for (const r of b.permits.slice(0, 15))
    L.push(`    ${r.permitnumber} ${r.permittypedesc} | ${r.permitteename} | ${r.permitstatusshortdesc} | ${odDate(r.issuedworkstartdate)}-${odDate(r.issuedworkenddate)}${r.tags.length ? ' | ' + r.tags.join(', ') : ''}`);
  L.push(`  Capital projects within 60 m: ${b.capital_projects.length}`);
  for (const c of b.capital_projects) L.push(`    ${c.fmsid} ${c.projtitle} (${c.leadagency}, ${c.construc_2 ? 'completed ' + odDate(c.construc_2) : 'completion date blank in 97nd-ff3i'})`);
  L.push(`  Public 311 sidewalk/curb requests within 50 m, last year: ${b.public_311_nearby.length}`);
  for (const r of b.public_311_nearby.slice(0, 8)) L.push(`    ${odDate(r.created_date)} ${r.descriptor} at ${r.incident_address || r.intersection_street_1} (${r.status})`);
  for (const x of b.rules_these_facts_feed) L.push(`  -> ${x}`);
  for (const x of b.notes) L.push(`  Note: ${x}`);
  for (const x of b.errors) L.push(`  ERROR (source not read, nothing filled in): ${x}`);
  return L.join('\n');
}

// ------------------------------------------------------------------ workbook intake (rows from SheetJS sheet_to_json with header:1)
const DYN_COLS = { guid: ['(do not modify) nyc service request'], created: ['created on', 'date/time submitted'], sr: ['sr number'],
  problem: ['problem'], problem_detail: ['problem detail'], additional_details: ['additional details'], attachment: ['sr attachment'],
  location_details: ['additional location details'], address: ['sr address'], borough: ['borough (sr address) (nyc address)', 'borough'],
  description: ['description'], lat: ['latitude'], lon: ['longitude'] };
const ARTS_COLS = { assigned: ['assigned'], created: ['date received'], sr: ['tracking #', 'tracking#'], borough: ['boro', 'borough'],
  address: ['location'], description: ['details'], status: ['status'] };
const h = (v) => (v === null || v === undefined ? '' : String(v).trim().toLowerCase().split(/\s+/).join(' '));
function mapCols(row, spec) {
  const hs = row.map(h), idx = {};
  for (const [k, names] of Object.entries(spec)) for (const n of names) { const i = hs.indexOf(n); if (i >= 0) { idx[k] = i; break; } }
  return idx;
}
export function readSrRows(rows, sheet) {
  const out = []; let cur = null, kind = null;
  rows.forEach((row, i) => {
    row = row || [];
    const hs = row.map(h);
    if (hs.includes('sr number')) { cur = mapCols(row, DYN_COLS); kind = 'dynamics'; return; }
    if (hs.includes('assigned') && hs.some((x) => x.startsWith('tracking'))) { cur = mapCols(row, ARTS_COLS); kind = 'arts'; return; }
    if (!cur || !('sr' in cur)) return;
    const v = row[cur.sr];
    if (v === null || v === undefined || String(v).trim() === '') return;
    const rec = { kind, sheet, row: i + 1 };
    for (const [k, j] of Object.entries(cur)) rec[k] = row[j] ?? null;
    rec.sr = String(rec.sr).trim();
    out.push(rec);
  });
  return out;
}
export function recordToInput(rec) {
  const num = (v) => (v === null || v === undefined || v === '' || Number.isNaN(Number(v)) ? null : Number(v));
  return { sr: rec.sr.startsWith('311-') ? rec.sr : null, borough: rec.borough, lat: num(rec.lat), lon: num(rec.lon), address: rec.address,
    // SheetJS gives Created On as a local-time Date; read the local calendar day (toISOString would shift evening times)
    complaint_date: rec.created instanceof Date
      ? `${rec.created.getFullYear()}-${String(rec.created.getMonth() + 1).padStart(2, '0')}-${String(rec.created.getDate()).padStart(2, '0')}`
      : rec.created,
    description: rec.description, location_details: rec.location_details, guid: rec.guid };
}
