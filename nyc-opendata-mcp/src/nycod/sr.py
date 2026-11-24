"""SR brief: everything public data says about one Make Safe SR, laid out for the make-safe-batch stages.

The brief follows the skill's Stage 2 (corners) and Stage 7 (Open Data check) notes. It reports facts and names the rule
each fact feeds. It does not choose a route, a type or the final corners: those rest on the imagery and the caller's
words (hard rules H1, H2), so the skill and Richard make them.
"""
import datetime as dt
import json
import os
import re

from . import geo, qow
from . import opendata as od
from .http import FetchError

QUADS = ('NE', 'NW', 'SE', 'SW')
WORDS = {'NORTHEAST': 'NE', 'NORTH EAST': 'NE', 'NORTHWEST': 'NW', 'NORTH WEST': 'NW', 'SOUTHEAST': 'SE',
         'SOUTH EAST': 'SE', 'SOUTHWEST': 'SW', 'SOUTH WEST': 'SW'}
SR_RE = re.compile(r'\b311-\d{8}\b')
TYPE_TAGS = (('RAMP', 'ped ramp'), ('TEMPORARY PEDESTRIAN WALK', 'temporary pedestrian walk'), ('TEST PIT', 'test pit'),
             ('FOUNDATION', 'foundation'), ('RESTORATION', 'restoration'), ('SIGNAL', 'signal'))
STATUS_TAGS = (('DELINQUENT', 'DELINQUENT (missed a deadline)'),
               ('EXPIRED UNDER GUARANTEE', 'EXPIRED UNDER GUARANTEE (still responsible for restoration)'))


# ------------------------------------------------------------------ parsing what Dynamics gives
def parse_sr_address(addr):
    """Split a Dynamics SR Address into parts.

    '69-01 NORTHERN BOULEVARD, QUEENS (WOODSIDE), NY, 11377' -> house number, street, borough, neighborhood, zip.
    'NORTHERN BOULEVARD AND 69 STREET, QUEENS' (or & / at) -> street and cross street.
    Parts that are not there stay None."""
    out = dict(raw=addr, house_number=None, street=None, cross_street=None, borough=None, neighborhood=None, zip=None)
    if not addr or not str(addr).strip():
        return out
    s = ' '.join(str(addr).replace('\xa0', ' ').split())
    parts = [p.strip() for p in s.split(',')]
    head = parts[0]
    for p in parts[1:]:
        m = re.match(r'^([A-Za-z ]+?)\s*(?:\(([^)]+)\))?$', p)
        if m and m.group(1).strip().upper() in geo.BORO_NUM:
            out['borough'] = m.group(1).strip().upper()
            out['neighborhood'] = m.group(2).title() if m.group(2) else None
        elif re.fullmatch(r'\d{5}', p):
            out['zip'] = p
    m = re.split(r'\s+(?:AND|&|AT)\s+|\s*/\s*|\s*&\s*', head, maxsplit=1, flags=re.I)
    if len(m) == 2 and m[0].strip() and m[1].strip():   # '7 AVENUE AND LINCOLN PLACE' is two streets, not house 7
        out['street'], out['cross_street'] = geo.norm(m[0]), geo.norm(m[1])
        return out
    m = re.match(r'^(\d+[A-Z]?(?:-\d+[A-Z]?)?)\s+(.+)$', head, flags=re.I)
    if m:
        out['house_number'], out['street'] = m.group(1).upper(), geo.norm(m.group(2))
    else:
        out['street'] = geo.norm(head)
    return out


def corners_in_words(text):
    """Corner words in the caller's Description: quadrants named, 'all four corners', sides. A hint for the corners
    table, not a decision: the corners an SR covers are settled with the imagery (H2)."""
    if not text:
        return dict(quadrants=[], all_corners=False, sides=[])
    t = ' ' + re.sub(r'[^A-Z0-9 ]+', ' ', str(text).upper()) + ' '
    t = ' '.join(t.split())
    found = []
    for w, qd in WORDS.items():
        if re.search(rf'\b{w}\b', t):
            found.append(qd)
    for qd in QUADS:
        if re.search(rf'\b{qd}\b', t):
            found.append(qd)
    allc = bool(re.search(r'\bALL (?:4|FOUR) CORNERS\b|\bALL (?:THE )?CORNERS\b|\bEVERY CORNER\b|\bEACH CORNER\b', t))
    sides = sorted({m.group(1) for m in re.finditer(r'\b(NORTH|SOUTH|EAST|WEST)\s+SIDE\b', t)})
    return dict(quadrants=sorted(set(found)), all_corners=allc, sides=sides)


def _date(s):
    """'11/3/2026 9:14 AM', '2026-11-03', '2026-11-03T09:14:00' or a datetime -> date, or None."""
    if s is None or s == '':
        return None
    if isinstance(s, dt.datetime):
        return s.date()
    if isinstance(s, dt.date):
        return s
    s = str(s).strip()
    for fmt in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y %I:%M %p',
                '%m/%d/%Y %I:%M:%S %p', '%m/%d/%Y %H:%M', '%m/%d/%Y'):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def lot_at(lat, lon):
    """MapPLUTO tax lot under a point: (BBL as 10-char string, lot address) or (None, None)."""
    fs = geo.q('GAZETTEER/MapPLUTO', 0, geometry=f'{lon},{lat}', geometryType='esriGeometryPoint', inSR=4326,
               spatialRel='esriSpatialRelIntersects', outFields='BBL,Address', returnGeometry='false')['features']
    if not fs:
        return None, None
    a = fs[0]['attributes']
    return (f"{int(a['BBL']):010d}" if a.get('BBL') else None), a.get('Address')


# ------------------------------------------------------------------ the brief
class _Run:
    """Collects results, notes and errors; a failed source is reported, never filled in (H1)."""

    def __init__(self):
        self.errors, self.notes = [], []

    def call(self, label, fn, *a, default=None, **k):
        try:
            return fn(*a, **k)
        except (FetchError, ValueError, KeyError, TypeError, IndexError) as e:
            self.errors.append(f'{label}: {e}')
            return default


def _corner_out(r, ramps, lot_bbl, approx=None):
    d = {k: r.get(k) for k in ('cid', 'dir', 'ctype', 'on', 'frm', 'bbl', 'lat', 'lon', 'X', 'Y', 'link')}
    if r.get('dist') is not None:
        d['dist_ft'] = round(r['dist'], 1)
    if not d['dir'] and approx:
        d['dir_label'] = f'{approx} (approx.)'
    else:
        d['dir_label'] = d['dir'] or None
    d['ramps'] = ramps.get(r['cid'], [])
    d['on_sr_lot'] = bool(lot_bbl and r.get('bbl') == lot_bbl)
    return d


def sr_brief(sr=None, borough=None, lat=None, lon=None, address=None, street1=None, street2=None,
             complaint_date=None, description=None, guid=None, radius_ft=100, permit_years=1.0,
             nyc311_meters=50, approx_directions=True, save_dir=None, location_details=None):
    """Public-data brief for one SR. Give at least one location: lat/lon, a Dynamics SR Address, or two streets.

    sr: '311-xxxxxxxx' (used for the jagj-gttd lookup and file names). complaint_date: the SR's Created On (sets the
    permit window and the made-safe-on-or-after check); today when not given, and the brief says so."""
    run = _Run()
    sr = (sr or '').strip() or None
    if sr and not SR_RE.fullmatch(sr):
        m = SR_RE.search(sr)
        run.notes.append(f"SR '{sr}' is not in 311-xxxxxxxx form" + (f'; using {m.group(0)}' if m else ''))
        sr = m.group(0) if m else sr
    parsed = parse_sr_address(address) if address else parse_sr_address(None)
    boro_in = borough or parsed['borough']
    bn = geo.boro_num(boro_in)
    boro_name = geo.OD_BORO[bn]
    code = {1: 'M', 2: 'X', 3: 'K', 4: 'Q', 5: 'R'}[bn]
    cdate = _date(complaint_date)
    today = dt.date.today()
    if not cdate:
        run.notes.append('No complaint date given: the permit window and the made-safe-on-or-after check use today.'
                         if complaint_date in (None, '') else f"Complaint date '{complaint_date}' not understood; using today.")
    ref = cdate or today
    s1 = geo.norm(street1) if street1 else parsed['street'] if parsed['cross_street'] else None
    s2 = geo.norm(street2) if street2 else parsed['cross_street']
    hn = parsed['house_number']
    addr_street = parsed['street'] if hn else None
    words = corners_in_words(' '.join(x for x in (description, location_details) if x))

    # ---- location: Stage 2 "SR point"
    point, point_src, addr_point = None, None, None
    if lat not in (None, '') and lon not in (None, ''):
        point, point_src = (float(lat), float(lon)), 'Dynamics Lat/Lon'
    if hn and addr_street:
        addr_point = run.call('locate_address', geo.locate_address, hn, addr_street, bn)
        if addr_point:
            if point:
                gap = geo.ft(point[0], point[1], addr_point[0], addr_point[1])
                if gap > 100:
                    run.notes.append(f'Dynamics point is {gap:.0f} ft from the {addr_point[2]} for {hn} {addr_street}; '
                                     'per the corners note the address point is used. Check the address in imagery.')
                    point, point_src = addr_point[:2], f'{addr_point[2]} (Dynamics point {gap:.0f} ft away)'
            else:
                point, point_src = addr_point[:2], addr_point[2]
        elif not point:
            run.notes.append(f'{hn} {addr_street} did not geocode (AddressPoint, MapPLUTO and LION all empty).')

    # ---- corners
    ix_corners, ix_src = [], None
    if s1 and s2:
        ix_corners = run.call('intersection', geo.intersection, s1, s2, bn, default=[])
        ix_src = 'PRISM names'
        if not ix_corners:
            pa, pb = ('%' + '%'.join(x.split()) + '%' for x in (s1, s2))
            nodes = run.call('lion_nodes', geo.lion_nodes, pa, pb, bn, default=[])
            if nodes:
                n0 = nodes[0]
                ix_corners = run.call('corners_near (LION node)', geo.corners_near, n0['lat'], n0['lon'], 100, default=[])
                ix_src = f"LION node {n0['node']} ({n0['a']} / {n0['b']})"
                if len(nodes) > 1:
                    run.notes.append(f'{len(nodes)} LION nodes share {s1} and {s2}; used node {n0["node"]}. '
                                     f'Others: {", ".join(str(n["node"]) for n in nodes[1:5])}.')
                if not point:
                    point, point_src = (n0['lat'], n0['lon']), ix_src
            else:
                run.notes.append(f'No PRISM corners and no shared LION node for {s1} and {s2} in {boro_name}.')
        elif not point:
            point = (sum(c['lat'] for c in ix_corners) / len(ix_corners), sum(c['lon'] for c in ix_corners) / len(ix_corners))
            point_src = 'centre of the PRISM corners at the intersection'
    if not point and not ix_corners:
        raise ValueError('No location: give lat/lon, an SR Address that geocodes, or two streets that meet.')

    near = run.call('corners_near', geo.corners_near, point[0], point[1], radius_ft, default=[]) if point else []
    lot_bbl, lot_addr = run.call('lot_at', lot_at, point[0], point[1], default=(None, None)) if point else (None, None)

    reference = None
    if point and not near and not ix_corners:
        wide = run.call('corners_near (reference)', geo.corners_near, point[0], point[1], 800, default=[])
        same = [c for c in wide if addr_street and addr_street in (c['on'], c['frm'])]
        blk = [c for c in same if lot_bbl and c.get('block') is not None and int(c['block']) == int(lot_bbl[1:6])]
        reference = (blk or same or wide or [None])[0]

    # every corner at each intersection touched (ramp program and history are read for the whole intersection)
    pairs = []
    for c in ix_corners + near + ([reference] if reference else []):
        p = (c['on'], c['frm'])
        if frozenset(p) not in {frozenset(x) for x in pairs}:
            pairs.append(p)
    pairs = pairs[:4]
    by_cid = {c['cid']: c for c in ix_corners + near + ([reference] if reference else [])}
    for on, frm in pairs:
        for c in run.call(f'intersection {on} / {frm}', geo.intersection, on, frm, bn, default=[]):
            by_cid.setdefault(c['cid'], c)
    all_cids = sorted(by_cid)
    ramps = run.call('ramps_by_corner', geo.ramps_by_corner, all_cids, default={}) if all_cids else {}

    approx = {}
    if approx_directions:
        for cid, c in by_cid.items():
            if not c.get('dir'):
                approx[cid] = run.call(f'approx_dir {cid}', geo.approx_dir, c['lat'], c['lon'], c['on'], c['frm'])

    near_ids = [c['cid'] for c in near]
    ix_ids = [c['cid'] for c in ix_corners]
    corners = [_corner_out(by_cid[cid], ramps, lot_bbl, approx.get(cid)) for cid in all_cids]
    for c in corners:
        if point:   # distance from the SR point for every corner, not only those found by the radius search
            c['dist_ft'] = round(geo.ft(point[0], point[1], c['lat'], c['lon']), 1)
        c['within_radius'] = c['cid'] in near_ids
        c['at_named_intersection'] = c['cid'] in ix_ids
        c['named_by_caller'] = bool(c['dir'] and c['dir'] in words['quadrants'])
    corners.sort(key=lambda c: (not c['within_radius'], c['dist_ft'] if c.get('dist_ft') is not None else 1e9,
                                c['on'] or '', c['dir'] or ''))

    # which row of the corners table applies to the input (a pointer, not the decision)
    if words['quadrants'] and (ix_corners or near):
        rule = ('Caller names ' + ', '.join(words['quadrants']) + ': the corners table says only those corners. '
                'Confirm in imagery; a quadrant word can describe the caller, not the defect.')
    elif words['all_corners'] or (ix_corners and not hn):
        rule = 'Intersection with no corner named: every corner there (four -> ALL_FOUR_CORNERS).'
    elif hn and near:
        rule = (f'Street address: corners within {radius_ft} ft of the SR point. If the caller describes their own '
                'corner/house/property, the corner on the address\'s own tax lot (on_sr_lot).')
    elif reference:
        rule = ('Mid-block, no corner within 100 ft: reference corner = nearest on the same street and tax block. '
                'Look at the address in imagery first: a large mid-block building is not a corner (P12, building ramp -> DOB).')
    else:
        rule = 'No corners table row fits the input cleanly; settle the corners from the Description and imagery.'
    if words['sides']:
        rule += f" Caller mentions the {', '.join(s.lower() for s in words['sides'])} side: a non-quadrant label goes in the form's Median."

    # ---- Stage 7: ramp program, complaints, permits, capital, 311
    prog = run.call('ramp_program (e7gc-ub6z)', od.ramp_program, all_cids, default={}) if all_cids else {}
    hist = run.call('ramp_complaints (jagj-gttd)', od.ramp_complaints, all_cids, default=[]) if all_cids else []
    this_sr = run.call('ramp_complaints by SR', od.ramp_complaints, sr=sr, default=[]) if sr else []

    since = ref - dt.timedelta(days=round(365 * float(permit_years)))
    completions = sorted(d for d in (_date(r['construc_1'][:10].replace('/', '-')) for r in prog.values()
                                     if r.get('construc_1')) if d)
    since2 = completions[0] if completions and completions[0] < since else None
    street_pairs = list(pairs)
    if s1 and s2 and frozenset((s1, s2)) not in {frozenset(p) for p in street_pairs}:
        street_pairs.append((s1, s2))
    permit_rows, permit_queries = {}, []
    for a, b in street_pairs:
        for start in [since] + ([since2] if since2 else []):
            rows = run.call(f'permits_at {a} / {b}', od.permits_at, boro_name, a, b, start.isoformat(), default=[])
            permit_queries.append(dict(kind='intersection', a=a, b=b, since=start.isoformat(), rows=len(rows)))
            for r in rows:
                permit_rows.setdefault(r['permitnumber'], r)
    if hn and addr_street:
        rows = run.call(f'permits_address {hn} {addr_street}', od.permits_address, boro_name, hn, addr_street,
                        since.isoformat(), default=[])
        permit_queries.append(dict(kind='address', house_number=hn, street=addr_street, since=since.isoformat(), rows=len(rows)))
        for r in rows:
            permit_rows.setdefault(r['permitnumber'], r)
    # newest first; permit number breaks ties (Socrata returns same-timestamp rows in no fixed order)
    permits = sorted(sorted(permit_rows.values(), key=lambda r: r['permitnumber']),
                     key=lambda r: r.get('permitissuedate') or '', reverse=True)

    capital, seen = [], set()
    for c in corners:
        if not c['within_radius'] and not c['at_named_intersection']:
            continue
        for r in run.call(f"capital_near {c['cid']}", od.capital_near, c['lat'], c['lon'], 60, default=[]):
            if r.get('projectid') not in seen:
                seen.add(r.get('projectid'))
                capital.append({k: r.get(k) for k in ('projectid', 'projtitle', 'fmsid', 'leadagency', 'projectt_1',
                                                      'projectsta', 'construc_2', 'onstreetna', 'fromstreet', 'tostreetna')}
                               | {'near_cid': c['cid']})
    n311 = (run.call('311 near (erm2-nwe9)', od.nyc311_near, point[0], point[1], nyc311_meters,
                     (ref - dt.timedelta(days=365)).isoformat(), default=[]) if point else [])

    # ---- facts each routing rule reads
    def tr_dates(r):
        return [d for d in (_date(r.get('temp_repair_date')), _date(r.get('date_second_temp_repair'))) if d]
    made_safe = []
    for r in hist:
        for d in tr_dates(r):
            made_safe.append(dict(cid=int(r['cmt_corner_id']), complaint_id=r.get('complaint_id'),
                                  complaint_date=od.od_date(r.get('complaint_date')), temp_repair_date=od.od_date(d.isoformat()),
                                  temp_repair_type=r.get('temp_repair_type'),
                                  on_or_after_complaint=bool(cdate and d >= cdate),
                                  days_before_complaint=(ref - d).days))
    prog_out = {str(cid): dict(status=r.get('construc_2'), construction_type=r.get('constructi'),
                               completed=od.od_date(r.get('construc_1')), street1=r.get('street_nam'), street2=r.get('street_n_1'))
                for cid, r in prog.items()}
    missing_prog = [cid for cid in all_cids if cid not in prog]

    def pclass(r):
        t = (r.get('permittypedesc') or '').upper()
        tags = []
        if qow.cwc_permit(r):
            tags.append('CWC (DOT in-house)')
        tags += [tag for word, tag in TYPE_TAGS if word in t]
        st = (r.get('permitstatusshortdesc') or '').upper()
        tags += [tag for word, tag in STATUS_TAGS if word in st]
        return tags
    permits_out = []
    for r in permits:
        d = {k: r.get(k) for k in od.PERMIT_FIELDS.split(',')}
        d['tags'] = pclass(r)
        end, start = _date(r.get('issuedworkenddate')), _date(r.get('issuedworkstartdate'))
        d['in_force_on_complaint_date'] = bool(cdate and start and end and start <= cdate <= end)
        iss = _date(r.get('permitissuedate'))
        d['issued_days_before_complaint'] = (ref - iss).days if iss else None
        d['nycstreets'] = qow.NYCSTREETS + r['permitnumber']
        permits_out.append(d)
    key = [r for r in permits if any(t in ' '.join(pclass(r)) for t in ('CWC', 'ped ramp', 'temporary pedestrian walk',
                                                                       'test pit', 'foundation', 'restoration', 'signal'))]
    labels = [c['dir_label'] for c in corners if c['dir_label'] and (c['within_radius'] or c['at_named_intersection'])]
    links = qow.permit_links(key, labels or ['--'], (cdate or today).isoformat())

    logged = sorted({int(r['cmt_corner_id']) for r in this_sr if r.get('cmt_corner_id')})
    facts = dict(
        this_sr_logged_in_jagj=bool(this_sr) if sr else None,
        this_sr_logged_corners=logged,
        logged_corners_not_in_candidates=[c for c in logged if c not in by_cid],
        made_safe_before=made_safe,
        made_safe_on_or_after_complaint=[m for m in made_safe if m['on_or_after_complaint']],
        earlier_complaints=[dict(cid=int(r['cmt_corner_id']), complaint_id=r.get('complaint_id'),
                                 complaint_date=od.od_date(r.get('complaint_date')), temp_repair_feasible=r.get('temp_repair_feasible'))
                            for r in hist if r.get('complaint_id') != sr][:40],
        cwc_permits=[r['permitnumber'] for r in permits if qow.cwc_permit(r)],
        ramp_permits=[r['permitnumber'] for r in permits if 'RAMP' in (r.get('permittypedesc') or '').upper()],
        temporary_pedestrian_walk_permits=[r['permitnumber'] for r in permits
                                           if 'TEMPORARY PEDESTRIAN WALK' in (r.get('permittypedesc') or '').upper()],
        delinquent_or_under_guarantee=[f"{r['permitnumber']} {r.get('permitstatusshortdesc')}" for r in permits
                                       if any(s in (r.get('permitstatusshortdesc') or '').upper()
                                              for s in ('DELINQUENT', 'EXPIRED UNDER GUARANTEE'))],
        ramp_program_completed=[f"{cid} {v['completed']} ({v['construction_type']})" for cid, v in prog_out.items() if v['completed']],
        corners_without_program_row=missing_prog,
        capital_projects=len(capital),
        public_311_ramp_or_curb_nearby=len(n311),
    )
    # which rules those facts feed (pointers to the skill's notes, wording of the notes)
    feeds = []
    if facts['made_safe_on_or_after_complaint']:
        feeds.append('Temporary repair on or after the complaint date: P58 (no Make Safe, N.TAR) if PavementWorks agrees.')
    elif made_safe:
        feeds.append('Corner made safe before: see made-safe-before (new Make Safe + PRP status email if the defect is '
                     'obvious; PRP status email only if made safe long ago and defects not obvious).')
    if facts['cwc_permits'] or facts['ramp_permits']:
        feeds.append('CWC or ramp-contractor permits at the corner: confirm Quality of Work and the permittee (Stage 7; '
                     'QoW routing). Ped ramp permit to screenshot is first in permit_links.')
    if facts['temporary_pedestrian_walk_permits']:
        feeds.append('Permitted temporary pedestrian walk: with a temporary-sounding ramp -> HIQA (decision order step 6).')
    if facts['delinquent_or_under_guarantee']:
        feeds.append('DELINQUENT / EXPIRED UNDER GUARANTEE permits: note in the index.')
    if capital or facts['ramp_program_completed']:
        feeds.append('Capital project or ramp program completion nearby: possibly QoW for that contract; keep only when '
                     'photos or imagery tie the defect to that work.')
    if sr and not this_sr:
        feeds.append('This SR is not in jagj-gttd yet (logging lags about a week).')
    if facts['logged_corners_not_in_candidates']:
        feeds.append('jagj-gttd logs this SR on corners outside the candidates: check the SR point and corners.')

    out = dict(
        sr=sr, borough=boro_name, borough_code=code, complaint_date=cdate.isoformat() if cdate else None,
        description=description, additional_location_details=location_details, dynamics_link=geo.dynamics_link(guid) if guid else None,
        input=dict(address=address, parsed=parsed, street1=s1, street2=s2, lat=lat, lon=lon),
        point=dict(lat=point[0], lon=point[1], source=point_src) if point else None,
        sr_lot=dict(bbl=lot_bbl, address=lot_addr),
        caller_corner_words=words, corners_rule=rule,
        intersection_source=ix_src, corners=corners,
        reference_corner=_corner_out(reference, ramps, lot_bbl, approx.get(reference['cid'])) if reference else None,
        ramp_program=prog_out, ramp_complaints_history=hist, ramp_complaints_this_sr=this_sr,
        permits=permits_out, permit_queries=permit_queries, permit_window_since=since.isoformat(),
        permit_window_extended_to=since2.isoformat() if since2 else None,
        permit_links=[dict(permit=p, label=lbl, url=u) for p, lbl, u in links],
        capital_projects=capital, public_311_nearby=n311,
        facts=facts, rules_these_facts_feed=feeds, notes=run.notes, errors=run.errors,
        not_covered=['routing and type (decision order, type table)', 'corner choice against imagery (H2)',
                     'Cyclomedia street views and visual check', 'PavementWorks export (signed-in)',
                     'NYCStreets permit pages (signed-in, DOT network)', 'Dynamics customer photos and edits'],
        generated=dt.datetime.now().isoformat(timespec='seconds'),
    )
    out['summary'] = summary_text(out)
    if save_dir:
        out['saved'] = save_brief(out, save_dir)
    return out


def summary_text(b):
    """Plain lines for summary.txt: what each source returned, in the order the Stage 7 note reads them."""
    L = [f"{b['sr'] or '(no SR)'}  {b['borough']}  complaint {b['complaint_date'] or 'date not given'}"]
    if b['description']:
        L.append(f'  Description: "{b["description"]}"')
    p = b['point']
    if p:
        L.append(f"  Point: {p['lat']:.6f}, {p['lon']:.6f} ({p['source']}); lot {b['sr_lot']['bbl'] or 'none found'}")
    L.append(f"  Corners rule: {b['corners_rule']}")
    for c in b['corners']:
        tag = ', '.join(t for t, on in (('within radius', c['within_radius']), ('named intersection', c['at_named_intersection']),
                                        ('on SR lot', c['on_sr_lot']), ('named by caller', c['named_by_caller'])) if on)
        L.append(f"  Corner {c['cid']} {c['dir_label'] or 'direction blank'} {c['on']} / {c['frm']}"
                 f"{' ' + str(c['dist_ft']) + ' ft' if c.get('dist_ft') is not None else ''}; {len(c['ramps'])} ramps"
                 f"{'; ' + tag if tag else ''}")
        pr = b['ramp_program'].get(str(c['cid']))
        L.append('    Program: ' + (f"{pr['status']}, {pr['construction_type']}"
                                    + (f", completed {pr['completed']}" if pr['completed'] else '') if pr else 'no row'))
    f = b['facts']
    if b['sr']:
        L.append(f"  This SR in jagj-gttd: {'yes, corners ' + ', '.join(map(str, f['this_sr_logged_corners'])) if f['this_sr_logged_in_jagj'] else 'not yet'}")
    for m in f['made_safe_before']:
        L.append(f"  Temp repair {m['temp_repair_date']} on {m['cid']} ({m['complaint_id']}, {m['complaint_date']})"
                 f"{' ON/AFTER complaint' if m['on_or_after_complaint'] else ''}")
    L.append(f"  Permits since {b['permit_window_since']}"
             f"{' (and from ' + b['permit_window_extended_to'] + ')' if b['permit_window_extended_to'] else ''}: {len(b['permits'])}")
    for r in b['permits'][:15]:
        L.append(f"    {r['permitnumber']} {r.get('permittypedesc')} | {r.get('permitteename')} | {r.get('permitstatusshortdesc')}"
                 f" | {od.od_date(r.get('issuedworkstartdate'))}-{od.od_date(r.get('issuedworkenddate'))}"
                 f"{' | ' + ', '.join(r['tags']) if r['tags'] else ''}")
    L.append(f"  Capital projects within 60 m: {len(b['capital_projects'])}")
    for c in b['capital_projects']:
        L.append(f"    {c['fmsid']} {c['projtitle']} ({c['leadagency']}, "
                 f"{'completed ' + od.od_date(c['construc_2']) if c.get('construc_2') else 'completion date blank in 97nd-ff3i'})")
    L.append(f"  Public 311 sidewalk/curb requests within 50 m, last year: {len(b['public_311_nearby'])}")
    for r in b['public_311_nearby'][:8]:
        L.append(f"    {od.od_date(r.get('created_date'))} {r.get('descriptor')} at {r.get('incident_address') or r.get('intersection_street_1')} ({r.get('status')})")
    for x in b['rules_these_facts_feed']:
        L.append(f'  -> {x}')
    for x in b['notes']:
        L.append(f'  Note: {x}')
    for x in b['errors']:
        L.append(f'  ERROR (source not read, nothing filled in): {x}')
    return '\n'.join(L)


def save_brief(b, save_dir):
    """Write <save_dir>/<SR>.json and <SR>.summary.txt, then rebuild <save_dir>/summary.txt from every SR summary there."""
    os.makedirs(save_dir, exist_ok=True)
    stem = b['sr'] or f"no-sr_{b['generated'].replace(':', '')}"
    jp, sp = os.path.join(save_dir, f'{stem}.json'), os.path.join(save_dir, f'{stem}.summary.txt')
    with open(jp, 'w', encoding='utf-8') as f:
        json.dump(b, f, indent=1, default=str)
    with open(sp, 'w', encoding='utf-8') as f:
        f.write(b['summary'] + '\n')
    parts = sorted(n for n in os.listdir(save_dir) if n.endswith('.summary.txt'))
    with open(os.path.join(save_dir, 'summary.txt'), 'w', encoding='utf-8') as f:
        for n in parts:
            with open(os.path.join(save_dir, n), encoding='utf-8') as g:
                f.write(g.read() + '\n')
    return dict(json=jp, summary=sp, combined=os.path.join(save_dir, 'summary.txt'))
