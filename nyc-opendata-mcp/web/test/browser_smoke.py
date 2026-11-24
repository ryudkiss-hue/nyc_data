"""Headless-browser smoke test of the Pages app against live data (Playwright + Chrome).

Serves web/ on localhost, runs one SR from URL parameters, briefs a workbook tab built from live jagj-gttd rows, and
checks the tabs by keyboard. Screenshots go to $SMOKE_OUT (default /tmp). Set SMOKE_PROXY when outbound HTTPS needs a proxy.
Run from nyc-opendata-mcp/web:  python test/browser_smoke.py"""
import functools
import http.server
import json
import os
import sys
import tempfile
import threading
import urllib.request

import openpyxl
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('SMOKE_OUT', '/tmp')
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=HERE))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{srv.server_address[1]}/index.html'

# workbook from live jagj-gttd rows (real SRs, corners, dates; Description left blank: jagj-gttd has none)
rows = json.load(urllib.request.urlopen("https://data.cityofnewyork.us/resource/jagj-gttd.json?$where=complaint_id%20like%20'311-%25'&$order=complaint_date%20DESC&$limit=20", timeout=60))
seen, picked = set(), []
for r in rows:
    if r['complaint_id'] not in seen:
        seen.add(r['complaint_id'])
        picked.append(r)
    if len(picked) == 2: break
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Richard'
ws.append(['(Do Not Modify) NYC Service Request', 'Created On', 'SR Number', 'SR Address', 'Borough (SR Address) (NYC Address)', 'Description', 'Latitude', 'Longitude'])
for r in picked:
    ws.append([None, r['complaint_date'][:10], r['complaint_id'], f"{r['street_name1']} AND {r['street_name2']}, {r['borough']}", r['borough'], None, None, None])
wb.create_sheet('Empty')
xlsx = os.path.join(tempfile.mkdtemp(), 'book.xlsx')
wb.save(xlsx)

errors, failed = [], []
with sync_playwright() as p:
    kw = dict(executable_path=os.environ.get('CHROME', '/usr/bin/google-chrome'), headless=True)
    if os.environ.get('SMOKE_PROXY'):
        kw['proxy'] = dict(server=os.environ['SMOKE_PROXY'], bypass='127.0.0.1,localhost')
    br = p.chromium.launch(**kw)
    pg = br.new_page(viewport=dict(width=1280, height=900))
    pg.on('console', lambda m: m.type == 'error' and errors.append(m.text))
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('requestfailed', lambda r: failed.append(f'{r.url[:120]} {r.failure}'))

    pg.goto(base + '?sr=311-29399735&borough=Brooklyn&street1=7%20Avenue&street2=Lincoln%20Place&complaint_date=2026-10-20&run=1')
    pg.wait_for_selector('#one-result article h2', timeout=180000)
    h = pg.inner_text('#one-result article h2')
    st = pg.inner_text('#one-status')
    corners = pg.locator('#one-result table').first.locator('tbody tr').count()
    assert '311-29399735' in h, h
    assert corners == 4, corners
    assert 'yes, corners 1108794, 1108796' in pg.inner_text('#one-result dl'), pg.inner_text('#one-result dl')
    assert pg.locator('.leaflet-container').count() == 1
    pg.screenshot(path=f'{OUT}/smoke_one.png', full_page=True)
    print('one SR:', st)

    pg.focus('#tab-one')
    pg.keyboard.press('ArrowRight')
    assert pg.get_attribute('#tab-book', 'aria-selected') == 'true', 'ArrowRight did not move to Workbook'
    assert pg.get_attribute('#panel-one', 'hidden') is not None and pg.get_attribute('#panel-book', 'hidden') is None
    pg.set_input_files('#b-file', xlsx)
    pg.wait_for_function("document.querySelector('#b-sheet').options.length > 1", timeout=30000)
    print('sheets:', pg.inner_text('#b-sheet').replace('\n', ' | '))
    pg.click('#book-form button[type=submit]')
    pg.wait_for_function("/briefed/.test(document.querySelector('#book-status').textContent)", timeout=300000)
    print('workbook:', pg.inner_text('#book-status'))
    nrows = pg.locator('#book-result tbody tr').count()
    assert nrows == len(picked), nrows
    for r in picked:
        assert r['complaint_id'] in pg.inner_text('#book-result tbody')
    pg.locator('#book-result tbody tr').first.get_by_role('button', name='Open').click()
    pg.wait_for_selector('#book-detail article h3')
    pg.screenshot(path=f'{OUT}/smoke_book.png', full_page=True)
    br.close()
srv.shutdown()
bad = [e for e in errors if 'favicon' not in e]
print('console errors:', bad or 'none')
print('failed requests:', [f for f in failed if 'favicon' not in f] or 'none')
sys.exit(1 if bad else 0)
