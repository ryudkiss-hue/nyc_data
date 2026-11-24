"""NYC Open Data (Socrata SODA) helpers used by make-safe-batch Stage 7, plus public 311 and general SoQL.

permits, permits_at, permits_address, ramp_program, ramp_complaints, capital_near and od_date are ported from msb.py
unchanged in their queries. nyc311_near, soql and dataset_info are additions.
"""
from .geo import norm, sq
from .http import get_json, urlencode

OPENDATA = 'https://data.cityofnewyork.us/resource'
PERMITS = 'https://data.cityofnewyork.us/resource/tqtj-sjs8.json'

DATASETS = {
    'tqtj-sjs8': 'Street Construction Permits (2022 - Present)',
    '97nd-ff3i': 'Street and Highway Capital Reconstruction Projects - Intersection',
    'e7gc-ub6z': 'Pedestrian Ramp - Program Progress',
    'jagj-gttd': 'Pedestrian Ramp Complaints',
    'erm2-nwe9': '311 Service Requests from 2010 to Present',
}


def soda(ds, **params):
    """SoQL query against an NYC Open Data dataset id, cached."""
    params.setdefault('$limit', 1000)
    return get_json(f'{OPENDATA}/{ds}.json?' + urlencode(params))


PERMIT_FIELDS = ('permitnumber,permitstatusshortdesc,permittypedesc,permitseriesshortdesc,permitissuedate,issuedworkstartdate,'
                 'issuedworkenddate,permithousenumber,onstreetname,fromstreetname,tostreetname,permitteename,'
                 'permitpurposecomments,permitlocationcomments')


def permits(where, limit=1000):
    p = {'$select': PERMIT_FIELDS, '$where': where, '$order': 'permitissuedate DESC', '$limit': limit}
    return get_json(PERMITS + '?' + urlencode(p))


def _nm(x):
    return ' '.join((x or '').upper().split())


RAMP_TYPES = ('RAMP', 'SIDEWALK', 'CURB', 'CORNER', 'PED', 'SIM/CWC', 'RESTORATION', 'TEST PIT', 'FOUNDATION', 'SIGNAL')


def permits_at(boro_name, a, b, since, keep=RAMP_TYPES):
    """Permits on street a at/from/to street b (either way round), issued since YYYY-MM-DD; boro_name e.g. 'QUEENS'.
    keep: permit-type substrings to keep (None = every type). Rows are kept only when both names match exactly after
    normalizing (the LIKE pattern over-matches numbered streets: WEST%58%STREET also hits WEST 158 STREET)."""
    A, B = ('%'.join(norm(x).split()) for x in (a, b))
    w = (f"boroughname='{boro_name}' AND permitissuedate >= '{since}' AND ("
         f"(upper(onstreetname) like '%{A}%' AND (upper(fromstreetname) like '%{B}%' OR upper(tostreetname) like '%{B}%')) OR "
         f"(upper(onstreetname) like '%{B}%' AND (upper(fromstreetname) like '%{A}%' OR upper(tostreetname) like '%{A}%')))")
    na, nb = norm(a), norm(b)

    def exact(r):
        on, fr, to = _nm(r.get('onstreetname')), _nm(r.get('fromstreetname')), _nm(r.get('tostreetname'))
        return (on == na and nb in (fr, to)) or (on == nb and na in (fr, to))
    rows = [r for r in permits(w) if exact(r)]
    return rows if keep is None else [r for r in rows if any(k in (r.get('permittypedesc') or '').upper() for k in keep)]


def permits_address(boro_name, hn, street, since):
    """Every permit at one house number on one street since YYYY-MM-DD (all types)."""
    w = (f"boroughname='{boro_name}' AND permitissuedate >= '{since}' AND permithousenumber='{sq(hn)}' "
         f"AND upper(onstreetname) like '%{'%'.join(norm(street).split())}%'")
    return [r for r in permits(w) if _nm(r.get('onstreetname')) == norm(street)]


def ramp_program(cids):
    """{cid: row} from Pedestrian Ramp - Program Progress (e7gc-ub6z). construc_2 = status, constructi = Upgrade /
    New Install, construc_1 = completed (YYYY/MM/DD)."""
    ids = ','.join(str(int(c)) for c in cids)
    return {int(r['cornerid']): r for r in soda('e7gc-ub6z', **{'$where': f'cornerid in ({ids})'})} if ids else {}


def ramp_complaints(cids=None, sr=None):
    """Pedestrian Ramp Complaints (jagj-gttd): earlier complaints and temporary repairs on these corners, newest first,
    or the rows for one SR (complaint_id holds 311 numbers such as '311-28438040'; logging lags about a week)."""
    if sr:
        return soda('jagj-gttd', **{'$where': f"complaint_id like '%{sq(sr.replace('311-', ''))}%'"})
    ids = ','.join(str(int(c)) for c in cids or [])
    return soda('jagj-gttd', **{'$where': f'cmt_corner_id in ({ids})', '$order': 'complaint_date DESC'}) if ids else []


def capital_near(lat, lon, meters=60):
    """Street and Highway Capital Reconstruction Projects - Intersection (97nd-ff3i) within `meters` of a point.
    Every row is a completed project; construc_2 is the completion date."""
    return soda('97nd-ff3i', **{'$where': f'within_circle(the_geom, {lat}, {lon}, {meters})'})


def od_date(s):
    """'2026/09/23' or '2026-09-23T00:00:00.000' -> '9/23/2026'."""
    if not s:
        return ''
    y, m, d = s[:10].replace('/', '-').split('-')
    return f'{int(m)}/{int(d)}/{y}'


# ------------------------------------------------------------------ additions
NYC311_FIELDS = ('unique_key,created_date,closed_date,agency,complaint_type,descriptor,incident_address,street_name,'
                 'cross_street_1,cross_street_2,intersection_street_1,intersection_street_2,address_type,status,'
                 'resolution_description,borough,bbl,latitude,longitude')


def nyc311_near(lat, lon, meters=50, since=None, dot_sidewalk_only=True, limit=200):
    """Public 311 requests (erm2-nwe9) within `meters` of a point, newest first. dot_sidewalk_only keeps DOT
    Sidewalk Condition and Curb Condition (where 'Pedestrian Ramp Defective' sits). The public unique_key is not the
    Dynamics 311-xxxxxxxx number, so matches are by place and date only."""
    w = f'within_circle(location, {float(lat)}, {float(lon)}, {float(meters)})'
    if since:
        w += f" AND created_date >= '{sq(since)}'"
    if dot_sidewalk_only:
        w += " AND agency='DOT' AND complaint_type in ('Sidewalk Condition', 'Curb Condition')"
    return soda('erm2-nwe9', **{'$select': NYC311_FIELDS, '$where': w, '$order': 'created_date DESC', '$limit': limit})


def soql(dataset_id, select=None, where=None, order=None, group=None, limit=100, offset=0, q=None):
    """General SoQL query against any NYC Open Data dataset id (4x4 such as 'tqtj-sjs8')."""
    p = {'$limit': limit, '$offset': offset}
    for k, v in (('$select', select), ('$where', where), ('$order', order), ('$group', group), ('$q', q)):
        if v:
            p[k] = v
    return get_json(f'{OPENDATA}/{dataset_id}.json?' + urlencode(p))


def dataset_info(dataset_id):
    """Name, description, update time and columns of an NYC Open Data dataset."""
    import datetime
    d = get_json(f'https://data.cityofnewyork.us/api/views/{dataset_id}.json')

    def ts(x):
        return datetime.datetime.fromtimestamp(x, datetime.timezone.utc).isoformat() if x else None
    return dict(id=dataset_id, name=d.get('name'), description=(d.get('description') or '')[:1500],
                attribution=d.get('attribution'), rows_updated_at=ts(d.get('rowsUpdatedAt')),
                view_last_modified=ts(d.get('viewLastModified')),
                columns=[dict(field=c['fieldName'], name=c.get('name'), type=c.get('dataTypeName'),
                              description=(c.get('description') or '')[:300])
                         for c in d.get('columns', []) if not c['fieldName'].startswith(':')])
