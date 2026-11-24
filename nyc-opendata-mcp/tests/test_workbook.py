"""Workbook intake by header. The test sheet is built from live jagj-gttd rows (real SR numbers, corners and dates),
laid out with the Dynamics column headers of Richard's tab; GUID and Description are left blank because jagj-gttd
does not carry them (no invented values)."""
import os

import openpyxl
from nycod import geo
from nycod import opendata as od
from nycod.workbook import read_srs, workbook_briefs

HEADERS = ['(Do Not Modify) NYC Service Request', 'Created On', 'SR Number', 'Problem Detail', 'SR Address',
           'Borough (SR Address) (NYC Address)', 'Description', 'Latitude', 'Longitude', 'Additional Location Details']


def build(path):
    rows = od.soql('jagj-gttd', where="complaint_id like '311-%'", order='complaint_date DESC', limit=20)
    picked, seen = [], set()
    for r in rows:
        if r['complaint_id'] not in seen:
            seen.add(r['complaint_id'])
            picked.append(r)
        if len(picked) == 2:
            break
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Richard'
    ws.append(['Make Safe Dynamics complaints (test sheet from live jagj-gttd rows)'])
    ws.append(HEADERS)
    for r in picked:
        c = geo.corners_by_id([int(r['cmt_corner_id'])])[0]
        ws.append([None, r['complaint_date'][:10], r['complaint_id'], None,
                   f"{r['street_name1']} AND {r['street_name2']}, {r['borough']}", r['borough'], None,
                   c['lat'], c['lon'], None])
    ws.append([None] * len(HEADERS))
    ws.append([None, None, None, 'Assigned', 'Date Received', 'Tracking #', 'Boro', 'Location', 'Details', 'Status'])
    wb.save(path)
    return picked


def test_read_and_brief(tmp_path):
    p = str(tmp_path / 'book.xlsx')
    picked = build(p)
    recs = read_srs(p, 'Richard')
    assert [r['sr'] for r in recs] == [x['complaint_id'] for x in picked]
    assert recs[0]['kind'] == 'dynamics' and recs[0]['lat'] is not None
    out = workbook_briefs(p, 'Richard', save_dir=str(tmp_path / 'opendata'))
    assert not out['failed'], out['failed']
    assert len(out['ok']) == len(picked)
    for x, src in zip(out['ok'], picked):
        assert x['logged_in_jagj'] is True
        assert any(c.startswith(src['cmt_corner_id']) for c in x['corners'])
        assert os.path.exists(x['saved']['json']) and os.path.exists(x['saved']['summary'])
    assert os.path.exists(tmp_path / 'opendata' / 'summary.txt')
