"""Headless-browser smoke test of every page of the static site, against live data (Playwright + Chrome).

Serves site/ on localhost and drives: the home quick-start box, Explore (open a dataset, filter and count by a column,
a within_circle query with a map, a column profile), Datasets (live freshness and row counts), DOT map layers (a PRISM
query with a map), and the Make Safe brief (one SR from URL parameters, a workbook tab built from live jagj-gttd rows,
keyboard tabs). Fails on any JavaScript error, any console error other than a failed network load, any failed load
of the site's own files, and any page that shows a source it could not read. Upstream 4xx/5xx answers that the page
retried and recovered from are listed, not failed: the browser logs them even when the retry worked.
Screenshots go to $SMOKE_OUT (default /tmp).

Run from the repo root:  python site/tests/browser_smoke.py
Set SMOKE_PROXY when outbound HTTPS needs a proxy, CHROME for the browser binary."""
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

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('SMOKE_OUT', '/tmp')
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{srv.server_address[1]}'

rows = json.load(urllib.request.urlopen(
    "https://data.cityofnewyork.us/resource/jagj-gttd.json?$where=complaint_id%20like%20'311-%25'&$order=complaint_date%20DESC&$limit=20",
    timeout=60))
seen, picked = set(), []
for r in rows:
    if r['complaint_id'] not in seen:
        seen.add(r['complaint_id'])
        picked.append(r)
    if len(picked) == 2:
        break
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Richard'
ws.append(['(Do Not Modify) NYC Service Request', 'Created On', 'SR Number', 'SR Address', 'Borough (SR Address) (NYC Address)',
           'Description', 'Latitude', 'Longitude'])
for r in picked:
    ws.append([None, r['complaint_date'][:10], r['complaint_id'], f"{r['street_name1']} AND {r['street_name2']}, {r['borough']}",
               r['borough'], None, None, None])
wb.create_sheet('Empty')
xlsx = os.path.join(tempfile.mkdtemp(), 'book.xlsx')
wb.save(xlsx)

errors = []      # JavaScript errors and console errors other than network loads
bad_local = []   # failed loads of the site's own files
upstream = []    # upstream 4xx/5xx answers (reported; the pages retry and the checks below catch real failures)
LONG = 240000


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


with sync_playwright() as p:
    kw = dict(executable_path=os.environ.get('CHROME', '/usr/bin/google-chrome'), headless=True)
    if os.environ.get('SMOKE_PROXY'):
        kw['proxy'] = dict(server=os.environ['SMOKE_PROXY'], bypass='127.0.0.1,localhost')
    br = p.chromium.launch(**kw)
    pg = br.new_page(viewport=dict(width=1280, height=900))
    pg.set_default_timeout(LONG)
    pg.on('console', lambda m: m.type == 'error' and not m.text.startswith('Failed to load resource') and errors.append(f'{pg.url}: {m.text}'))
    pg.on('pageerror', lambda e: errors.append(f'{pg.url}: {e}'))

    def on_response(r):
        if r.status >= 400:
            (bad_local if r.url.startswith(BASE) else upstream).append(f'{r.status} {r.url[:140]}')
    pg.on('response', on_response)

    # home -> explore by dataset ID
    pg.goto(f'{BASE}/index.html')
    pg.fill('#go-q', 'jagj-gttd')
    pg.click('#go-form button[type=submit]')
    pg.wait_for_url('**/explore.html?ds=jagj-gttd')
    pg.wait_for_function("document.querySelector('#ds-title').textContent.includes('Pedestrian Ramp Complaints')")
    pg.wait_for_function("[...document.querySelectorAll('#ds-info dd')].some(d => /^[0-9,]+$/.test(d.textContent))")
    print('home -> explore: ok')

    # explore: filter borough = BROOKLYN via the builder, then count by temp_repair_feasible
    pg.click('#add-filter')
    pg.select_option('#f1-col', 'borough')
    pg.fill('#f1-val', 'BROOKLYN')
    pg.select_option('#q-countby', 'temp_repair_feasible')
    check(pg.input_value('#s-where') == "`borough` = 'BROOKLYN'", pg.input_value('#s-where'))
    pg.click('#query-form button[type=submit]')
    pg.wait_for_selector('#results table')
    n = pg.locator('#results tbody tr').count()
    check(1 <= n <= 4, f'count-by rows {n}')
    print('explore count-by:', pg.inner_text('#q-status'), n, 'groups')
    pg.click('#profile')
    pg.wait_for_function("/Profile done|Profile stopped/.test(document.querySelector('#q-status').textContent)")
    check('Profile done' in pg.inner_text('#q-status'), pg.inner_text('#q-status'))
    print('explore profile: ok')

    # explore: within_circle on a point column, from a shared link, with a map
    pg.goto(f"{BASE}/explore.html?ds=e7gc-ub6z&where={urllib.request.quote('within_circle(the_geom, 40.6757, -73.9744, 50)')}")
    pg.wait_for_selector('#results table')
    pg.wait_for_selector('#results .leaflet-container')
    check(pg.locator('#results tbody tr').count() == 4, 'expected the 4 Lincoln Pl corners')
    pg.screenshot(path=f'{OUT}/smoke_explore.png', full_page=True)
    print('explore within_circle + map: ok')

    # datasets board
    pg.goto(f'{BASE}/datasets.html?q=ramp')
    pg.wait_for_function("document.querySelector('#status').textContent.startsWith('Done.')")
    print('datasets:', pg.inner_text('#status'), '|', pg.inner_text('#board caption'))
    check('unreadable' not in pg.inner_text('#board caption'), 'some dataset update dates could not be read')
    pg.click('#count')
    pg.wait_for_function("document.querySelector('#status').textContent.startsWith('Counted rows')")
    check(pg.locator('#board tbody tr').count() >= 3, 'ramp filter rows')
    pg.screenshot(path=f'{OUT}/smoke_datasets.png', full_page=True)

    # DOT map layers
    pg.goto(f'{BASE}/layers.html?svc=PRISM/PRISM_CORNERS&layer=0&where=CMTCornerID%3D1108794')
    pg.wait_for_selector('#results table')
    pg.wait_for_selector('#results .leaflet-container')
    check('1108794' in pg.inner_text('#results tbody'), 'corner 1108794 not returned')
    check(pg.locator('#svc-list li').count() >= 3, 'PRISM services not listed')
    pg.screenshot(path=f'{OUT}/smoke_layers.png', full_page=True)
    print('layers: ok')

    # Make Safe brief: one SR, then a workbook tab, keyboard tabs
    pg.goto(f'{BASE}/make-safe/?sr=311-29399735&borough=Brooklyn&street1=7%20Avenue&street2=Lincoln%20Place&complaint_date=2026-10-20&run=1')
    pg.wait_for_selector('#one-result article h2')
    check(pg.locator('#one-result table').first.locator('tbody tr').count() == 4, 'make-safe corners')
    check('yes, corners 1108794, 1108796' in pg.inner_text('#one-result dl'), pg.inner_text('#one-result dl'))
    print('make-safe one SR:', pg.inner_text('#one-status'))
    check('sources failed' not in pg.inner_text('#one-status'), pg.inner_text('#one-status'))
    pg.focus('#tab-one')
    pg.keyboard.press('ArrowRight')
    check(pg.get_attribute('#tab-book', 'aria-selected') == 'true', 'ArrowRight did not select Workbook')
    pg.set_input_files('#b-file', xlsx)
    pg.wait_for_function("document.querySelector('#b-sheet').options.length > 1")
    pg.click('#book-form button[type=submit]')
    pg.wait_for_function("/briefed/.test(document.querySelector('#book-status').textContent)")
    check(pg.locator('#book-result tbody tr').count() == len(picked), 'workbook rows')
    print('make-safe workbook:', pg.inner_text('#book-status'))
    check('sources failed' not in pg.inner_text('#book-result'), 'a workbook brief had sources that failed')
    br.close()
srv.shutdown()
print('upstream 4xx/5xx answers (retried):', upstream or 'none')
print('failed site files:', bad_local or 'none')
print('errors:', errors or 'none')
sys.exit(1 if errors or bad_local else 0)
