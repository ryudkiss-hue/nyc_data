"""Each ported helper returns what the skill's msb.py returns for the same live input."""
import json

from nycod import geo, qow
from nycod import opendata as od

# 7 Avenue & Lincoln Place, Brooklyn: four PRISM corners, jagj-gttd history incl. the 7/20/2026 temporary repair (P47)
LINCOLN = (40.67576199383651, -73.97443037301491)
LINCOLN_CIDS = [1108793, 1108794, 1108795, 1108796]
# 4 Avenue & 94 Street, Brooklyn: a completed capital project (first row of 97nd-ff3i)
CAPITAL_PT = (40.61669948866578, -74.03084507407647)


def same(a, b):
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_corners_near(msb):
    assert same(geo.corners_near(*LINCOLN, 150), msb.corners_near(*LINCOLN, 150))


def test_corners_by_id_and_intersection(msb):
    assert same(geo.corners_by_id(LINCOLN_CIDS), msb.corners_by_id(LINCOLN_CIDS))
    mine = geo.intersection('7 Avenue', 'Lincoln Place', 3)
    assert same(mine, msb.intersection('7 Avenue', 'Lincoln Place', 3))
    assert sorted(c['cid'] for c in mine) == LINCOLN_CIDS
    # borough names are accepted too and give the same answer
    assert same(geo.intersection('7 Avenue', 'Lincoln Place', 'Brooklyn'), mine)


def test_ramps_by_corner(msb):
    cids = [c['cid'] for c in geo.corners_near(40.7544786, -73.8973721, 400)]   # around 69-01 Northern Blvd, Queens
    assert cids
    mine, ref = geo.ramps_by_corner(cids), msb.ramps_by_corner(cids)

    # ArcGIS does not promise feature order between two live calls; order sets list order and the 'A / B' street
    # order of apex ramps, so compare as sets of ramps with their street sets.
    def canon(d):
        return {k: sorted((dict(r, street=' / '.join(sorted((r['street'] or '').split(' / ')))) for r in v),
                          key=lambda r: r['ramp']) for k, v in d.items()}
    assert same(canon(mine), canon(ref))
    assert any(mine.values()), 'expected ramps on at least one corner near Northern Blvd & 69 St'


def test_locate_address_and_lion(msb):
    assert same(geo.locate_address('69-01', 'NORTHERN BOULEVARD', 4), msb.locate_address('69-01', 'NORTHERN BOULEVARD', 4))
    assert same(sorted(geo.lion_nodes('%7 AVENUE%', '%LINCOLN PLACE%', 3), key=lambda r: r['node']),
                sorted(msb.lion_nodes('%7 AVENUE%', '%LINCOLN PLACE%', 3), key=lambda r: r['node']))


def test_approx_dir(msb):
    blank = geo.q('PRISM/PRISM_CORNERS', 0, where="CornerDirection IS NULL AND OnStreetName IS NOT NULL",
                  outSR=4326, resultRecordCount=3)['features']
    assert blank, 'PRISM has no blank-direction corner to test with'
    for f in blank:
        c = geo.corner_rec(f)
        assert geo.approx_dir(c['lat'], c['lon'], c['on'], c['frm']) == msb.approx_dir(c['lat'], c['lon'], c['on'], c['frm'])


def same_permits(a, b):
    """Same rows, both newest first. Socrata returns rows with an identical permitissuedate in no fixed order between
    two calls, so the order within a tie is not compared."""
    rows = lambda rs: sorted(json.dumps(r, sort_keys=True) for r in rs)   # noqa: E731
    newest_first = lambda rs: [r.get('permitissuedate') or '' for r in rs] == sorted(   # noqa: E731
        (r.get('permitissuedate') or '' for r in rs), reverse=True)
    return rows(a) == rows(b) and newest_first(a) and newest_first(b)


def test_permits(msb):
    a = od.permits_at('BROOKLYN', '7 AVENUE', 'LINCOLN PLACE', '2025-10-20')
    assert same_permits(a, msb.permits_at('BROOKLYN', '7 AVENUE', 'LINCOLN PLACE', '2025-10-20'))
    assert a, 'expected permits at 7 Ave & Lincoln Pl since 10/20/2025'
    assert same_permits(od.permits_at('BROOKLYN', '7 AVENUE', 'LINCOLN PLACE', '2025-10-20', keep=None),
                        msb.permits_at('BROOKLYN', '7 AVENUE', 'LINCOLN PLACE', '2025-10-20', keep=None))
    assert same_permits(od.permits_address('QUEENS', '69-01', 'NORTHERN BOULEVARD', '2024-01-01'),
                        msb.permits_address('QUEENS', '69-01', 'NORTHERN BOULEVARD', '2024-01-01'))


def test_permit_links(msb):
    rows = od.permits_at('BROOKLYN', '7 AVENUE', 'LINCOLN PLACE', '2025-10-20')
    full = [r for r in rows if all(r.get(k) for k in ('issuedworkenddate', 'issuedworkstartdate', 'permittypedesc',
                                                      'permitteename', 'permitstatusshortdesc'))]
    assert same(qow.permit_links(full, ['NE'], '2026-10-20'), msb.permit_links(full, ['NE'], '2026-10-20'))


def test_ramp_program_and_complaints(msb):
    assert same(od.ramp_program(LINCOLN_CIDS), msb.ramp_program(LINCOLN_CIDS))
    h = od.ramp_complaints(LINCOLN_CIDS)
    assert same(h, msb.ramp_complaints(LINCOLN_CIDS))
    assert any(r.get('temp_repair_date', '').startswith('2026-07-20') for r in h), 'P47 temp repair 7/20/2026 missing'
    assert same(od.ramp_complaints(sr='311-29399735'), msb.ramp_complaints(sr='311-29399735'))


def test_capital_near(msb):
    a = od.capital_near(*CAPITAL_PT, 60)
    assert same(a, msb.capital_near(*CAPITAL_PT, 60))
    assert a


def test_links(msb):
    c = geo.corners_by_id([1108794])[0]
    assert geo.streetsmart(c['X'], c['Y']) == msb.streetsmart(c['X'], c['Y'])
    g = 'fa78f734-fe9f-f111-b8dc-7ced8d17c336'
    if geo.DYN:   # only with NYCOD_DYNAMICS_BASE set to the same prefix msb.py uses
        assert geo.dynamics_link('{' + g + '}') == msb.dynamics_link('{' + g + '}')
