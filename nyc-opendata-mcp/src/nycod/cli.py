"""nycod-brief: the SR brief from a terminal, without an MCP client.

  nycod-brief --sr 311-29399735 --borough Brooklyn --street1 "7 Avenue" --street2 "Lincoln Place" --date 2026-10-20
  nycod-brief --address "69-01 NORTHERN BOULEVARD, QUEENS (WOODSIDE), NY, 11377"
  nycod-brief --workbook "Make Safe Dynamics and ARTs complaints as of 11-23-26.xlsx" --sheet Richard --save work/opendata
  nycod-brief --workbook book.xlsx            (lists sheets and the SRs found on each)
"""
import argparse
import json
import sys

from . import workbook as wbk
from .http import bypass_cache
from .sr import sr_brief


def main(argv=None):
    p = argparse.ArgumentParser(prog='nycod-brief', description='Public-data brief for Make Safe SRs (NYC Open Data + DOT ArcGIS).')
    p.add_argument('--sr')
    p.add_argument('--borough')
    p.add_argument('--lat', type=float)
    p.add_argument('--lon', type=float)
    p.add_argument('--address')
    p.add_argument('--street1')
    p.add_argument('--street2')
    p.add_argument('--date', help='complaint date (Created On)')
    p.add_argument('--description')
    p.add_argument('--guid')
    p.add_argument('--radius', type=float, default=100)
    p.add_argument('--years', type=float, default=1.0)
    p.add_argument('--workbook')
    p.add_argument('--sheet')
    p.add_argument('--only', nargs='*')
    p.add_argument('--save', help='folder for <SR>.json, <SR>.summary.txt and summary.txt')
    p.add_argument('--json', action='store_true', help='print the full JSON instead of the summary')
    p.add_argument('--fresh', action='store_true', help='skip the cache')
    a = p.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    with bypass_cache(a.fresh):
        if a.workbook:
            if not a.sheet:
                for n in wbk.sheets(a.workbook):
                    rs = wbk.read_srs(a.workbook, n)
                    print(f'{n}: {len(rs)} SRs' + (f" ({', '.join(r['sr'] for r in rs[:8])}{' ...' if len(rs) > 8 else ''})" if rs else ''))
                return 0
            r = wbk.workbook_briefs(a.workbook, a.sheet, save_dir=a.save, only=a.only)
            if a.json:
                print(json.dumps(r, indent=1, default=str))
            else:
                for x in r['ok']:
                    print(f"{x['sr']} (row {x['row']}): corners {', '.join(x['corners']) or 'none'}; {x['permits']} permits; "
                          f"made safe before {x['made_safe_before']}; in jagj-gttd {x['logged_in_jagj']}")
                    print(f'  "{x["description"]}"')
                    for f in x['feeds']:
                        print(f'  -> {f}')
                    for e in x['errors']:
                        print(f'  ERROR: {e}')
                for x in r['failed']:
                    print(f"{x['sr']} (row {x['row']}): FAILED {x['error']}")
                print(f"{len(r['ok'])} briefed, {len(r['failed'])} failed" + (f'; saved under {a.save}' if a.save else ''))
            return 1 if r['failed'] else 0
        b = sr_brief(sr=a.sr, borough=a.borough, lat=a.lat, lon=a.lon, address=a.address, street1=a.street1,
                     street2=a.street2, complaint_date=a.date, description=a.description, guid=a.guid,
                     radius_ft=a.radius, permit_years=a.years, save_dir=a.save)
        print(json.dumps(b, indent=1, default=str) if a.json else b['summary'])
        return 0


if __name__ == '__main__':
    sys.exit(main())
