"""SR briefs on real SRs: recent 311 complaints that DOT has logged in jagj-gttd, read live each run."""
import pytest
from nycod import opendata as od
from nycod.sr import corners_in_words, parse_sr_address, sr_brief


def recent_logged(n=3):
    rows = od.soql('jagj-gttd', where="complaint_id like '311-%'", order='complaint_date DESC', limit=60)
    seen, out = set(), []
    for r in rows:
        if r['complaint_id'] not in seen and r.get('street_name1') and r.get('street_name2'):
            seen.add(r['complaint_id'])
            out.append(r)
        if len(out) == n:
            break
    assert out, 'jagj-gttd returned no recent 311 complaints'
    return out


@pytest.mark.parametrize('row', recent_logged())
def test_brief_by_intersection_finds_logged_corner(row):
    b = sr_brief(sr=row['complaint_id'], borough=row['borough'], street1=row['street_name1'], street2=row['street_name2'],
                 complaint_date=row['complaint_date'][:10])
    cids = {c['cid'] for c in b['corners']}
    assert int(row['cmt_corner_id']) in cids, (row, b['notes'], b['errors'])
    assert b['facts']['this_sr_logged_in_jagj'] is True
    assert int(row['cmt_corner_id']) in b['facts']['this_sr_logged_corners']
    assert not b['errors'], b['errors']
    assert b['summary'].startswith(row['complaint_id'])


def test_brief_by_point_of_logged_corner():
    row = recent_logged(1)[0]
    from nycod import geo
    c = geo.corners_by_id([int(row['cmt_corner_id'])])[0]
    b = sr_brief(sr=row['complaint_id'], borough=row['borough'], lat=c['lat'], lon=c['lon'],
                 complaint_date=row['complaint_date'][:10])
    near = [x for x in b['corners'] if x['within_radius']]
    assert near and near[0]['cid'] == c['cid'] and near[0]['dist_ft'] < 1


def test_brief_by_address_only():
    b = sr_brief(address='69-01 NORTHERN BOULEVARD, QUEENS (WOODSIDE), NY, 11377', complaint_date='2026-11-01',
                 description='The ramp at the corner by my building is cracked')
    assert b['point']['source'] == 'GAZETTEER AddressPoint'
    assert b['sr_lot']['bbl'] == '4011650045'
    assert b['corners'], b['notes']
    assert b['permit_queries'] and any(q['kind'] == 'address' for q in b['permit_queries'])
    assert not b['errors'], b['errors']


def test_brief_lincoln_place_matches_known_history():
    """7 Ave & Lincoln Pl (precedent P47): the 7/20/2026 asphalt patch and this SR's two logged corners."""
    b = sr_brief(sr='311-29399735', borough='Brooklyn', street1='7 Avenue', street2='Lincoln Place',
                 complaint_date='2026-10-20')
    assert sorted(b['facts']['this_sr_logged_corners']) == [1108794, 1108796]
    assert any(m['temp_repair_date'] == '7/20/2026' and m['cid'] == 1108794 for m in b['facts']['made_safe_before'])
    assert len(b['corners']) == 4 and b['corners_rule'].startswith('Intersection with no corner named')


def test_parse_and_words():
    a = parse_sr_address('7 AVENUE AND LINCOLN PLACE, BROOKLYN, NY')
    assert (a['street'], a['cross_street'], a['house_number'], a['borough']) == ('7 AVENUE', 'LINCOLN PLACE', None, 'BROOKLYN')
    a = parse_sr_address('76-19 ROOSEVELT AVENUE, QUEENS (JACKSON HEIGHTS), NY, 11372')
    assert (a['house_number'], a['street'], a['neighborhood'], a['zip']) == ('76-19', 'ROOSEVELT AVENUE', 'Jackson Heights', '11372')
    w = corners_in_words('The northeast corner ramp and the SW one are broken; also the north side')
    assert w['quadrants'] == ['NE', 'SW'] and w['sides'] == ['NORTH']
    assert corners_in_words('all four corners need ramps')['all_corners']


def test_bad_input_is_an_error_not_a_guess():
    with pytest.raises(ValueError):
        sr_brief(borough='Queens')
    with pytest.raises(ValueError):
        sr_brief(street1='A', street2='B', borough='Narnia')
