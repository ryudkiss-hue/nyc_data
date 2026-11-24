"""Read SRs from the weekly 'Make Safe Dynamics and ARTs complaints' workbook, columns found by header (Stage 1 intake).

The workbook is opened read-only and never written (H9). Two kinds of table are recognised on any sheet:
- Dynamics: a header row holding 'SR Number' (Richard's tab carries GUID, Created On, SR Address, Borough, Description,
  Latitude, Longitude, Additional Location Details; other team members' tables carry fewer columns).
- ARTs: a header row with 'Assigned' and 'Tracking #' (Assigned | Date Received | Tracking # | Boro | Location | Details | Status).
"""
import openpyxl

from .sr import sr_brief

DYN_COLS = {
    'guid': ('(do not modify) nyc service request',),
    'created': ('created on', 'date/time submitted'),
    'sr': ('sr number',),
    'problem': ('problem',),
    'problem_detail': ('problem detail',),
    'additional_details': ('additional details',),
    'attachment': ('sr attachment',),
    'location_details': ('additional location details',),
    'address': ('sr address',),
    'borough': ('borough (sr address) (nyc address)', 'borough'),
    'description': ('description',),
    'lat': ('latitude',),
    'lon': ('longitude',),
}
ARTS_COLS = {
    'assigned': ('assigned',), 'created': ('date received',), 'sr': ('tracking #', 'tracking#'),
    'borough': ('boro', 'borough'), 'address': ('location',), 'description': ('details',), 'status': ('status',),
}


def _h(v):
    return ' '.join(str(v).strip().lower().split()) if v is not None else ''


def _map(header, spec):
    idx = {}
    hs = [_h(v) for v in header]
    for key, names in spec.items():
        for n in names:
            if n in hs:
                idx[key] = hs.index(n)
                break
    return idx


def sheets(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        return wb.sheetnames
    finally:
        wb.close()


def read_srs(path, sheet=None):
    """[{kind, sheet, row, sr, created, address, borough, lat, lon, description, ...}] from one sheet (or every sheet)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    try:
        names = [sheet] if sheet else wb.sheetnames
        for name in names:
            if name not in wb.sheetnames:
                raise ValueError(f"no sheet '{name}' in {path}; sheets: {', '.join(wb.sheetnames)}")
            ws = wb[name]
            cur, kind = None, None
            for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
                hs = [_h(v) for v in row]
                if 'sr number' in hs:
                    cur, kind = _map(row, DYN_COLS), 'dynamics'
                    continue
                if 'assigned' in hs and any(h.startswith('tracking') for h in hs):
                    cur, kind = _map(row, ARTS_COLS), 'arts'
                    continue
                if not cur or 'sr' not in cur:
                    continue
                v = row[cur['sr']] if cur['sr'] < len(row) else None
                if v is None or str(v).strip() == '':
                    continue
                rec = dict(kind=kind, sheet=name, row=i)
                for k, j in cur.items():
                    rec[k] = row[j] if j < len(row) else None
                rec['sr'] = str(rec['sr']).strip()
                out.append(rec)
    finally:
        wb.close()
    return out


def _num(v):
    try:
        return float(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


def brief_record(rec, save_dir=None, **kw):
    """sr_brief for one workbook record. ARTs rows have a free-text Location: it is passed as the address."""
    created = rec.get('created')
    return sr_brief(sr=rec['sr'] if rec['sr'].startswith('311-') else None,
                    borough=rec.get('borough'), lat=_num(rec.get('lat')), lon=_num(rec.get('lon')),
                    address=rec.get('address'), complaint_date=created.isoformat() if hasattr(created, 'isoformat') else created,
                    description=rec.get('description'), location_details=rec.get('location_details'),
                    guid=rec.get('guid'), save_dir=save_dir, **kw)


def workbook_briefs(path, sheet, save_dir=None, only=None, limit=None, **kw):
    """Brief every SR on a sheet. Returns {'ok': [...short rows...], 'failed': [...]}; full briefs go to save_dir."""
    recs = read_srs(path, sheet)
    if only:
        want = {s.strip() for s in only}
        recs = [r for r in recs if r['sr'] in want]
    if limit:
        recs = recs[:int(limit)]
    ok, failed = [], []
    for r in recs:
        try:
            b = brief_record(r, save_dir=save_dir, **kw)
            ok.append(dict(sr=r['sr'], row=r['row'], kind=r['kind'], description=r.get('description'),
                           corners=[f"{c['cid']} {c['dir_label'] or '?'}" for c in b['corners'] if c['within_radius'] or c['at_named_intersection']],
                           permits=len(b['permits']), made_safe_before=len(b['facts']['made_safe_before']),
                           logged_in_jagj=b['facts']['this_sr_logged_in_jagj'], feeds=b['rules_these_facts_feed'],
                           notes=b['notes'], errors=b['errors'], saved=b.get('saved')))
        except Exception as e:
            failed.append(dict(sr=r['sr'], row=r['row'], description=r.get('description'), error=f'{type(e).__name__}: {e}'))
    return dict(workbook=path, sheet=sheet, count=len(recs), ok=ok, failed=failed)
