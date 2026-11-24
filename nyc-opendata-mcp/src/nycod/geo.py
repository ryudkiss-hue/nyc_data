"""Corners, ramps, geocoding and links from DOT ArcGIS (PRISM and GAZETTEER).

Ported from msb.py (make-safe-batch skill, fingerprint 32b7fd0c267a2749afb3df866a4e89e4), function for function.
Query strings, sorting and record fields are unchanged so results match the skill; tests/test_parity.py checks that.
"""
import collections
import math
import os
import re

from pyproj import Transformer

from .http import get_json, urlencode

ARCGIS = 'https://a841-dotweb01.nyc.gov/arcgis/rest/services'
# Dynamics record links: set NYCOD_DYNAMICS_BASE to the record URL prefix your AddDynamicsHyperlinks macro uses
# (everything before the GUID). It is not published here because it is an internal DOT address.
DYN = os.environ.get('NYCOD_DYNAMICS_BASE', '').strip()
TO2263 = Transformer.from_crs(4326, 2263, always_xy=True)
TO4326 = Transformer.from_crs(2263, 4326, always_xy=True)
TO3857_FROM_2263 = Transformer.from_crs(2263, 3857, always_xy=True)
BORO_NUM = {'MANHATTAN': 1, 'BRONX': 2, 'BROOKLYN': 3, 'QUEENS': 4, 'STATEN IS': 5, 'STATEN ISLAND': 5}
BORO = {'MANHATTAN': ('M', 'Manhattan'), 'BRONX': ('X', 'Bronx'), 'BROOKLYN': ('K', 'Brooklyn'),
        'QUEENS': ('Q', 'Queens'), 'STATEN IS': ('R', 'Staten Island'), 'STATEN ISLAND': ('R', 'Staten Island')}
BORO_ALIASES = {'M': 1, 'MN': 1, 'NEW YORK': 1, 'X': 2, 'BX': 2, 'K': 3, 'BK': 3, 'KINGS': 3, 'Q': 4, 'QN': 4,
                'R': 5, 'SI': 5, 'RICHMOND': 5}
OD_BORO = {1: 'MANHATTAN', 2: 'BRONX', 3: 'BROOKLYN', 4: 'QUEENS', 5: 'STATEN ISLAND'}


def boro_num(b):
    """1-5 from a number, a borough name (any case, 'STATEN IS' included) or a letter code (M X K Q R)."""
    if b is None or b == '':
        raise ValueError('borough is required: a name (Queens), a code (Q) or a number (4)')
    if isinstance(b, int) or str(b).strip().isdigit():
        n = int(b)
        if 1 <= n <= 5:
            return n
        raise ValueError(f'borough number must be 1-5, got {b}')
    s = ' '.join(str(b).upper().split())
    if s in BORO_NUM:
        return BORO_NUM[s]
    if s in BORO_ALIASES:
        return BORO_ALIASES[s]
    raise ValueError(f"unknown borough '{b}'; use Manhattan, Bronx, Brooklyn, Queens, Staten Island, a code M/X/K/Q/R or 1-5")


def q(service, layer, **params):
    """Query a DOT ArcGIS MapServer layer, e.g. q('PRISM/PRISM_CORNERS', 0, where=...)."""
    params.setdefault('f', 'json')
    params.setdefault('outFields', '*')
    params.setdefault('returnGeometry', 'true')
    return get_json(f'{ARCGIS}/{service}/MapServer/{layer}/query?' + urlencode(params))


def sq(s):
    return s.replace("'", "''")


ORD = {'FIRST': '1', 'SECOND': '2', 'THIRD': '3', 'FOURTH': '4', 'FIFTH': '5', 'SIXTH': '6', 'SEVENTH': '7',
       'EIGHTH': '8', 'NINTH': '9', 'TENTH': '10', 'ELEVENTH': '11', 'TWELFTH': '12'}


def norm(s):
    """Street name as PRISM/LION spell it: caps, single spaces, spelled ordinals to digits (FIRST AVENUE -> 1 AVENUE)."""
    s = re.sub(r'\s+', ' ', s.upper().replace('\xa0', ' ')).strip()
    return ' '.join(ORD.get(w, w) for w in s.split(' '))


def ft(lat1, lon1, lat2, lon2):
    x1, y1 = TO2263.transform(lon1, lat1)
    x2, y2 = TO2263.transform(lon2, lat2)
    return math.hypot(x2 - x1, y2 - y1)


# ------------------------------------------------------------------ corners and ramps (PRISM)
def streetsmart(X, Y, half=50):
    """Street Smart link: a 100 ft box around the corner. X, Y are EPSG:2263 feet; converted to EPSG:3857 metres
    first (msb.py fix of 11/23/2026)."""
    x, y = TO3857_FROM_2263.transform(X, Y)
    h = half * 0.3048
    return f'https://streetsmart.cyclomedia.com/streetsmart/?mq={x-h:.2f};{y-h:.2f};{x+h:.2f};{y+h:.2f}&msrs=EPSG:3857'


def dynamics_link(guid):
    """Dynamics record link from column A ((Do Not Modify) NYC Service Request); None when NYCOD_DYNAMICS_BASE is unset."""
    if not DYN or not guid:
        return None
    return DYN + str(guid).strip().strip('{}')


def corner_rec(f, ref=None):
    a, g = f['attributes'], f['geometry']
    bbl = f"{int(a['BoroughCode'])}{int(a['Block']):05d}{int(a['Lot']):04d}" if a.get('Block') is not None else None
    X, Y = TO2263.transform(g['x'], g['y'])
    r = dict(cid=a['CMTCornerID'], dir=a['CornerDirection'], ctype=a['CornerType'], on=a['OnStreetName'],
             frm=a['FromStreetName'], bbl=bbl, block=a.get('Block'), lot=a.get('Lot'), lat=g['y'], lon=g['x'], X=X, Y=Y,
             link=streetsmart(X, Y))
    if ref:
        r['dist'] = ft(ref[0], ref[1], g['y'], g['x'])
    return r


def corners_near(lat, lon, dist_ft=100):
    fs = q('PRISM/PRISM_CORNERS', 0, geometry=f'{lon},{lat}', geometryType='esriGeometryPoint', inSR=4326,
           spatialRel='esriSpatialRelIntersects', distance=dist_ft, units='esriSRUnit_Foot', outSR=4326)['features']
    return sorted((corner_rec(f, (lat, lon)) for f in fs), key=lambda r: r['dist'])


def corners_by_id(ids):
    ids = sorted({int(i) for i in ids})
    out = []
    for i in range(0, len(ids), 200):
        out += q('PRISM/PRISM_CORNERS', 0, where=f"CMTCornerID IN ({','.join(map(str, ids[i:i+200]))})", outSR=4326)['features']
    return [corner_rec(f) for f in out]


def intersection(a, b, boro):
    """All PRISM corners where two streets meet (PRISM spellings after norm())."""
    a, b = norm(a), norm(b)
    w = (f"BoroughCode={boro_num(boro)} AND ((OnStreetName='{sq(a)}' AND FromStreetName='{sq(b)}') OR "
         f"(OnStreetName='{sq(b)}' AND FromStreetName='{sq(a)}'))")
    return [corner_rec(f) for f in q('PRISM/PRISM_CORNERS', 0, where=w, outSR=4326)['features']]


def ramps_by_corner(cids):
    """{CMTCornerID: [ramp dicts]} from PRISM_RAMPS layer 0. An apex ramp facing two streets is kept once."""
    out = collections.defaultdict(dict)
    ids = sorted({int(i) for i in cids})
    for i in range(0, len(ids), 200):
        w = f"CMTCornerID IN ({','.join(map(str, ids[i:i+200]))})"
        for f in q('PRISM/PRISM_RAMPS', 0, where=w, outSR=4326)['features']:
            a, g = f['attributes'], f['geometry']
            prev = out[a['CMTCornerID']].get(a['CMTRampID'])
            if prev:
                if a['OnStreetName'] not in prev['street'].split(' / '):
                    prev['street'] += ' / ' + a['OnStreetName']
                continue
            out[a['CMTCornerID']][a['CMTRampID']] = dict(ramp=a['CMTRampID'], type=a['RampType'], street=a['OnStreetName'],
                                                         lat=g['y'], lon=g['x'])
    return {k: list(v.values()) for k, v in out.items()}


# ------------------------------------------------------------------ corner direction when PRISM leaves it blank
NOM = {'N': 0, 'NE': 45, 'E': 90, 'SE': 135, 'S': 180, 'SW': 225, 'W': 270, 'NW': 315}
OCT = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']


def _bearing(x0, y0, x, y):
    return (math.degrees(math.atan2(x - x0, y - y0)) + 360) % 360


def approx_dir(lat, lon, on, frm):
    """Estimate a blank CornerDirection from the labelled corners around it (matched PRISM 8/8 in the skill's test).
    Label the result '(approx.)'. A cardinal answer (N/E/S/W) needs the quadrant settled from the block layout."""
    recs = corners_near(lat, lon, 900)
    groups = collections.defaultdict(list)
    for r in recs:
        groups[frozenset((r['on'], r['frm']))].append(r)
    mine = [r for r in groups.get(frozenset((on, frm)), []) if r['dist'] < 400]
    if len(mine) < 2:
        return None

    def centroid(rs):
        return sum(r['X'] for r in rs) / len(rs), sum(r['Y'] for r in rs) / len(rs)
    local = [r for r in mine if r['dir'] in NOM]
    pool = [(mine, local)] if local else [(rs, [r for r in rs if r['dir'] in NOM]) for rs in groups.values()
                                          if len(rs) >= 3 and any(r['dir'] in NOM for r in rs)]
    offs = []
    for rs, lab in pool:
        cx, cy = centroid(rs)
        offs += [math.radians(NOM[r['dir']] - _bearing(cx, cy, r['X'], r['Y'])) for r in lab]
    if not offs:
        return None
    rot = math.degrees(math.atan2(sum(map(math.sin, offs)), sum(map(math.cos, offs))))
    cx, cy = centroid(mine)
    x, y = TO2263.transform(lon, lat)
    return OCT[int((((_bearing(cx, cy, x, y) + rot) % 360) + 22.5) % 360 // 45)]


# ------------------------------------------------------------------ geocoding SRs that have no Lat/Lon (GAZETTEER)
def _hn(hn):
    if '-' in hn:                       # Queens hyphenated numbers are stored zero-padded: 76-19 -> 76-019
        a, c = hn.split('-', 1)
        return f'{a}-{int(c):03d}' if c.isdigit() else hn
    return hn


def locate_address(hn, street, boro):
    """(lat, lon, source) for a house number: AddressPoint, then MapPLUTO, then LION address-range interpolation."""
    bn = boro_num(boro)
    street = norm(street)
    codes = sorted({f['attributes']['StreetCode'] for f in q('GAZETTEER/LION', 0,
                    where=f"Street='{sq(street)}' AND (LBoro={bn} OR RBoro={bn})", outFields='StreetCode',
                    returnGeometry='false')['features'] if f['attributes']['StreetCode']})
    for c in codes:
        fs = q('GAZETTEER/AddressPoint', 0, where=f"HOUSE_NUMBER='{_hn(hn)}' AND B7SC_ACTUAL LIKE '{c}%'",
               outFields='HOUSE_NUMBER,B7SC_ACTUAL', outSR=4326)['features']
        if fs:
            return fs[0]['geometry']['y'], fs[0]['geometry']['x'], 'GAZETTEER AddressPoint'
    fs = q('GAZETTEER/MapPLUTO', 0, where=f"Address='{sq(hn + ' ' + street)}' AND BoroCode={bn}",
           outFields='BBL,Latitude,Longitude', returnGeometry='false')['features']
    if fs:
        a = fs[0]['attributes']
        return a['Latitude'], a['Longitude'], 'MapPLUTO lot'
    try:
        n = int(hn.replace('-', ''))
    except ValueError:
        return None
    for f in q('GAZETTEER/LION', 0, where=f"Street='{sq(street)}' AND (LBoro={bn} OR RBoro={bn})",
               outFields='FromLeft,ToLeft,FromRight,ToRight,SegmentID', outSR=4326)['features']:
        a = f['attributes']
        for lo, hi in ((a['FromLeft'], a['ToLeft']), (a['FromRight'], a['ToRight'])):
            if lo and hi and min(lo, hi) <= n <= max(lo, hi) and lo % 2 == n % 2:
                pts = [p for path in f['geometry']['paths'] for p in path]
                t = 0.5 if hi == lo else (n - lo) / (hi - lo)
                i = min(int(t * (len(pts) - 1)), len(pts) - 2)
                fr = t * (len(pts) - 1) - i
                return (pts[i][1] + (pts[i+1][1] - pts[i][1]) * fr, pts[i][0] + (pts[i+1][0] - pts[i][0]) * fr,
                        'LION address-range interpolation')
    return None


def lion_nodes(a_like, b_like, boro):
    """Shared LION nodes of two streets (SQL LIKE patterns): finds intersections PRISM names differently."""
    bn = boro_num(boro)

    def segs(p):
        out = {}
        for f in q('GAZETTEER/LION', 0, where=f"Street LIKE '{sq(p)}' AND (LBoro={bn} OR RBoro={bn})",
                   outFields='Street,NodeIDFrom,NodeIDTo,XFrom,YFrom,XTo,YTo', returnGeometry='false')['features']:
            a = f['attributes']
            out[a['NodeIDFrom']] = (a['XFrom'], a['YFrom'], a['Street'])
            out[a['NodeIDTo']] = (a['XTo'], a['YTo'], a['Street'])
        return out
    A, B = segs(a_like), segs(b_like)
    res = []
    for n in set(A) & set(B):
        lon, lat = TO4326.transform(A[n][0], A[n][1])
        res.append(dict(node=n, lat=lat, lon=lon, a=A[n][2], b=B[n][2]))
    return res
