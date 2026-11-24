"""Write test/py_briefs.json: Python sr_brief results for live cases, for test/parity.mjs to compare against.

Run from the repo root:  python site/tests/make_py_briefs.py   (needs the package installed: pip install -e .)"""
import json
import os

from nycod import opendata as od
from nycod.sr import sr_brief

cases = [
    dict(sr='311-29399735', borough='Brooklyn', street1='7 Avenue', street2='Lincoln Place', complaint_date='2026-10-20'),
    dict(address='69-01 NORTHERN BOULEVARD, QUEENS (WOODSIDE), NY, 11377', complaint_date='2026-11-01',
         description='The ramp at the corner by my building is cracked'),
    dict(address='150 WILLIAM STREET, MANHATTAN, NY, 10038', complaint_date='2026-11-10',
         description='ramp in front of the building is broken'),
]
# plus the newest logged 311 complaint, read live
r = od.soql('jagj-gttd', where="complaint_id like '311-%'", order='complaint_date DESC', limit=1)[0]
cases.append(dict(sr=r['complaint_id'], borough=r['borough'], street1=r['street_name1'], street2=r['street_name2'],
                  complaint_date=r['complaint_date'][:10], description='northwest corner'))
out = [dict(input=c, brief=sr_brief(**c)) for c in cases]
p = os.path.join(os.path.dirname(__file__), 'py_briefs.json')
json.dump(out, open(p, 'w'), default=str)
print(f'wrote {len(out)} briefs to {p}')
