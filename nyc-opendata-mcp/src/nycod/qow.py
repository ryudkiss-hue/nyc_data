"""Quality of Work permit helpers, ported from msb.py (Richard's 10/1/2026 format; ped ramp permit first, 10/12)."""
import re

from .opendata import od_date

NYCSTREETS = 'https://nycstreets.nycdot.nyc/NYCStreets/Permit/Details/'   # DOT internal network; Richard's signed-in view


def cwc_permit(row):
    """True for a Citywide Concrete (DOT in-house crew) permit: permittee NYC DEPT OF TRANSPORTATION and a SIM/CWC-...
    type. Open Data has no contract field; the permit page's Contract Number DOT-INHSE is the confirmation."""
    return row.get('permitteename') == 'NYC DEPT OF TRANSPORTATION' and (row.get('permittypedesc') or '').startswith('SIM/CWC')


def permit_links(permits, corners, complaint_date, cwc=False):
    """[(permit number, label, url)] for one Quality of Work SR, the permit to screenshot first.

    permits: the SR's key permit rows; corners: its corner labels ('SW', 'NE (approx.)'); complaint_date 'YYYY-MM-DD...'.
    A permit whose location names quadrants is kept only when one is the SR's; one naming none is kept. First the ped
    ramp permit (in force on the complaint date when there is one), then those in force on the complaint date, then
    latest end date first. cwc is kept for callers; it no longer changes the pick."""
    mine = {c.split()[0].upper() for c in corners}

    def quads(r):
        return set(re.findall(r'\b(NE|NW|SE|SW)\b', (r.get('permitlocationcomments') or '').upper()))
    # Socrata omits null fields from a row, so every field is read with .get (msb.py indexes them directly).
    def g(r, k):
        return r.get(k) or ''
    keep = [r for r in permits if not quads(r) or quads(r) & mine]
    pref = 'RAMP'
    keep.sort(key=lambda r: pref not in g(r, 'permittypedesc'))
    keep.sort(key=lambda r: g(r, 'issuedworkenddate'), reverse=True)
    keep.sort(key=lambda r: g(r, 'issuedworkenddate')[:10] < (complaint_date or '')[:10])
    first = next((r for r in keep if pref in g(r, 'permittypedesc')), None)
    if first:
        keep.remove(first)
        keep.insert(0, first)
    return [(r['permitnumber'], f"{r['permitnumber']} ({g(r, 'permittypedesc').replace('SIM/CWC-', '').lower()}, "
             f"{g(r, 'permitteename')}, {g(r, 'permitstatusshortdesc').lower()}, {od_date(g(r, 'issuedworkstartdate'))}-"
             f"{od_date(g(r, 'issuedworkenddate'))})", NYCSTREETS + r['permitnumber']) for r in keep]
