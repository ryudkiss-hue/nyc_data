"""nyc-opendata-mcp: local MCP server (stdio) for make-safe-batch SRs.

Run:  nyc-opendata-mcp            (after pip install)
      python -m nycod.server

Every tool is read-only. Tools return facts from NYC Open Data and DOT ArcGIS; none of them decides a route.
"""
from typing import Annotated, Any

from pydantic import Field

from . import geo, qow
from . import opendata as od
from . import workbook as wbk
from .http import CACHE, bypass_cache, clear_cache
from .sr import corners_in_words, parse_sr_address, sr_brief

try:   # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:   # 1.x
    from mcp.server.fastmcp import FastMCP as _Server
from mcp.types import ToolAnnotations

INSTRUCTIONS = """NYC Open Data and DOT ArcGIS (PRISM corners/ramps, GAZETTEER LION/AddressPoint/MapPLUTO) for NYC DOT SIM
Make Safe SRs (the make-safe-batch skill, SOP 20). Start with nycod_sr_brief for one SR, or nycod_workbook_briefs for a
tab of the weekly workbook. The other tools are the same helpers the skill's msb.py uses, one per job.

These tools return facts. They never choose a route, a type or the final corners: those rest on the imagery and the
caller's words (hard rules H1, H2). Empty results are real empties; errors name the source that failed and nothing is
filled in. Boroughs accept names (Queens, STATEN IS), codes (M X K Q R) or numbers 1-5. Dates are YYYY-MM-DD.
Set fresh=true to skip the cache (Open Data 6 h, ArcGIS 7 days)."""

mcp = _Server('nyc_opendata_mcp', instructions=INSTRUCTIONS)


def _ann(title):
    try:
        return ToolAnnotations(title=title, read_only_hint=True, destructive_hint=False, idempotent_hint=True,
                               open_world_hint=True)
    except Exception:
        return ToolAnnotations(title=title, readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                               openWorldHint=True)


Boro = Annotated[str, Field(description="Borough: name (Queens, STATEN IS), code (M X K Q R) or number 1-5")]
Fresh = Annotated[bool, Field(description='Skip the cache for this call')]


def _run(fn, fresh, *a, **k):
    with bypass_cache(fresh):
        return fn(*a, **k)


# ------------------------------------------------------------------ workflow tools
@mcp.tool(name='nycod_sr_brief', annotations=_ann('SR brief (all public data for one SR)'))
def nycod_sr_brief(
    sr: Annotated[str | None, Field(description="SR number, '311-xxxxxxxx'")] = None,
    borough: Annotated[str | None, Field(description='Borough; taken from the SR Address when it names one')] = None,
    lat: Annotated[float | None, Field(description='Dynamics Latitude')] = None,
    lon: Annotated[float | None, Field(description='Dynamics Longitude')] = None,
    address: Annotated[str | None, Field(description="Dynamics SR Address, e.g. '69-01 NORTHERN BOULEVARD, QUEENS (WOODSIDE), NY, 11377' or 'A STREET AND B AVENUE, BROOKLYN'")] = None,
    street1: Annotated[str | None, Field(description='First street of an intersection')] = None,
    street2: Annotated[str | None, Field(description='Second street of an intersection')] = None,
    complaint_date: Annotated[str | None, Field(description="Created On (YYYY-MM-DD or M/D/YYYY); sets the permit window")] = None,
    description: Annotated[str | None, Field(description="Caller's Description, verbatim (H3)")] = None,
    location_details: Annotated[str | None, Field(description='Additional Location Details')] = None,
    guid: Annotated[str | None, Field(description='(Do Not Modify) NYC Service Request GUID, for the Dynamics link')] = None,
    radius_ft: Annotated[float, Field(description='Corner search radius around the SR point, feet', ge=10, le=1000)] = 100,
    permit_years: Annotated[float, Field(description='Permit look-back before the complaint date, years', gt=0, le=5)] = 1.0,
    save_dir: Annotated[str | None, Field(description='Folder (e.g. <batch>/work/opendata) to write <SR>.json, <SR>.summary.txt and summary.txt')] = None,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """Everything public data says about one Make Safe SR, in the order the skill reads it.

    Resolves the SR point (Dynamics Lat/Lon, else AddressPoint/MapPLUTO/LION; switches to the address point when the
    Dynamics point is over 100 ft off), lists candidate PRISM corners with ramps, BBL, direction ('(approx.)' when PRISM is
    blank), Street Smart links and which corners-table row applies; then for every corner at the intersection: ramp program
    (e7gc-ub6z), complaint and temporary-repair history (jagj-gttd), this SR's own jagj-gttd rows; permits one year back per
    street pair and house number (tqtj-sjs8, extended to the earliest ramp program completion), QoW permit links; completed
    capital projects within 60 m (97nd-ff3i); public 311 sidewalk/curb requests within 50 m (erm2-nwe9). 'facts' and
    'rules_these_facts_feed' name what each routing rule reads. 'summary' is the plain-text version."""
    return _run(sr_brief, fresh, sr=sr, borough=borough, lat=lat, lon=lon, address=address, street1=street1,
                street2=street2, complaint_date=complaint_date, description=description, location_details=location_details,
                guid=guid, radius_ft=radius_ft, permit_years=permit_years, save_dir=save_dir)


@mcp.tool(name='nycod_workbook_briefs', annotations=_ann('Briefs for every SR on a workbook tab'))
def nycod_workbook_briefs(
    path: Annotated[str, Field(description='Full path to the weekly workbook (.xlsx); opened read-only')],
    sheet: Annotated[str | None, Field(description="Sheet name, e.g. 'Richard'. Omit to list the sheets and the SRs found on each")] = None,
    save_dir: Annotated[str | None, Field(description='Folder for the per-SR JSON and summaries (recommended: <batch>/work/opendata)')] = None,
    only: Annotated[list[str] | None, Field(description='Only these SR numbers')] = None,
    limit: Annotated[int | None, Field(description='At most this many SRs', ge=1)] = None,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """Run nycod_sr_brief for every SR on one sheet of the 'Make Safe Dynamics and ARTs complaints' workbook.

    Columns are found by header (SR Number, Created On, SR Address, Borough (SR Address) (NYC Address), Latitude,
    Longitude, Description, Additional Location Details, (Do Not Modify) NYC Service Request), plus ARTs blocks (Assigned |
    Date Received | Tracking # | Boro | Location | Details | Status). Returns one short row per SR with the caller's
    Description; full briefs go to save_dir. Without sheet: lists sheets and SR counts."""
    if not sheet:
        names = wbk.sheets(path)
        found = {}
        for n in names:
            try:
                found[n] = [dict(sr=r['sr'], kind=r['kind'], row=r['row'], description=r.get('description'))
                            for r in wbk.read_srs(path, n)]
            except Exception as e:
                found[n] = f'{type(e).__name__}: {e}'
        return dict(workbook=path, sheets=names, srs_by_sheet=found)
    return _run(wbk.workbook_briefs, fresh, path, sheet, save_dir=save_dir, only=only, limit=limit)


@mcp.tool(name='nycod_parse_sr_text', annotations=_ann('Parse an SR Address and corner words'))
def nycod_parse_sr_text(
    address: Annotated[str | None, Field(description='Dynamics SR Address')] = None,
    description: Annotated[str | None, Field(description="Caller's Description")] = None,
) -> dict[str, Any]:
    """Split an SR Address into house number / street / cross street / borough / neighborhood / zip, and list the corner
    words in the Description (quadrants, 'all four corners', sides). No network calls."""
    return dict(address=parse_sr_address(address), corner_words=corners_in_words(description))


# ------------------------------------------------------------------ corners and geocoding (DOT ArcGIS)
@mcp.tool(name='nycod_corners_near', annotations=_ann('PRISM corners near a point'))
def nycod_corners_near(
    lat: float, lon: float,
    dist_ft: Annotated[float, Field(description='Search radius in feet', ge=1, le=2000)] = 100,
    with_ramps: Annotated[bool, Field(description='Attach PRISM_RAMPS for each corner')] = True,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """PRISM corners within dist_ft of a WGS84 point, nearest first: CMTCornerID, direction, type, On/From street, BBL,
    lat/lon, State Plane X/Y, distance, Street Smart link (msb.py corners_near)."""
    with bypass_cache(fresh):
        cs = geo.corners_near(lat, lon, dist_ft)
        if with_ramps and cs:
            rm = geo.ramps_by_corner([c['cid'] for c in cs])
            for c in cs:
                c['ramps'] = rm.get(c['cid'], [])
    return dict(count=len(cs), corners=cs)


@mcp.tool(name='nycod_intersection_corners', annotations=_ann('PRISM corners at an intersection'))
def nycod_intersection_corners(
    street1: str, street2: str, borough: Boro,
    lion_fallback: Annotated[bool, Field(description='When PRISM names do not match, find the shared LION node and list corners within 100 ft of it')] = True,
    with_ramps: bool = True,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """Every PRISM corner where two streets meet (names normalised as PRISM spells them: FIRST AVENUE -> 1 AVENUE).
    With lion_fallback, a miss is retried through LION nodes (University Plaza vs Flatbush Ave Ext; Grace Court vs 155 Street)."""
    with bypass_cache(fresh):
        cs, src = geo.intersection(street1, street2, borough), 'PRISM names'
        nodes = []
        if not cs and lion_fallback:
            pa, pb = ('%' + '%'.join(geo.norm(x).split()) + '%' for x in (street1, street2))
            nodes = geo.lion_nodes(pa, pb, borough)
            if nodes:
                cs = geo.corners_near(nodes[0]['lat'], nodes[0]['lon'], 100)
                src = f"LION node {nodes[0]['node']} ({nodes[0]['a']} / {nodes[0]['b']})"
        if with_ramps and cs:
            rm = geo.ramps_by_corner([c['cid'] for c in cs])
            for c in cs:
                c['ramps'] = rm.get(c['cid'], [])
    return dict(count=len(cs), source=src if cs else None, lion_nodes=nodes, corners=cs)


@mcp.tool(name='nycod_corners_by_id', annotations=_ann('PRISM corners by CMTCornerID'))
def nycod_corners_by_id(
    cids: Annotated[list[int], Field(description='CMTCornerIDs', min_length=1, max_length=2000)],
    with_ramps: bool = True, fresh: Fresh = False,
) -> dict[str, Any]:
    """PRISM corner records for CMTCornerIDs (msb.py corners_by_id), with ramps."""
    with bypass_cache(fresh):
        cs = geo.corners_by_id(cids)
        if with_ramps and cs:
            rm = geo.ramps_by_corner([c['cid'] for c in cs])
            for c in cs:
                c['ramps'] = rm.get(c['cid'], [])
    found = {c['cid'] for c in cs}
    return dict(count=len(cs), not_found=[c for c in cids if int(c) not in found], corners=cs)


@mcp.tool(name='nycod_ramps_by_corner', annotations=_ann('PRISM ramps per corner'))
def nycod_ramps_by_corner(cids: Annotated[list[int], Field(min_length=1, max_length=2000)], fresh: Fresh = False) -> dict[str, Any]:
    """{CMTCornerID: [ramps]} from PRISM_RAMPS (CMTRampID, RampType, street, lat/lon). An apex ramp facing two streets
    is listed once with both streets."""
    r = _run(geo.ramps_by_corner, fresh, cids)
    return dict(ramps={str(k): v for k, v in r.items()}, corners_without_ramps=[c for c in cids if int(c) not in r])


@mcp.tool(name='nycod_locate_address', annotations=_ann('Geocode a house number (GAZETTEER)'))
def nycod_locate_address(
    house_number: Annotated[str, Field(description="e.g. '150' or Queens '76-19'")], street: str, borough: Boro,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """(lat, lon, source) for a house number: GAZETTEER AddressPoint, then MapPLUTO, then LION address-range
    interpolation (msb.py locate_address). Record the source as SR Point Source."""
    r = _run(geo.locate_address, fresh, house_number, street, borough)
    if not r:
        return dict(found=False, house_number=house_number, street=geo.norm(street),
                    note='AddressPoint, MapPLUTO and LION address ranges all returned nothing. Check the spelling against LION.')
    return dict(found=True, lat=r[0], lon=r[1], source=r[2])


@mcp.tool(name='nycod_lion_nodes', annotations=_ann('Shared LION nodes of two streets'))
def nycod_lion_nodes(
    street1_like: Annotated[str, Field(description="SQL LIKE pattern, e.g. '%FLATBUSH%EXT%'")],
    street2_like: Annotated[str, Field(description="SQL LIKE pattern, e.g. '%DE KALB%'")],
    borough: Boro, fresh: Fresh = False,
) -> dict[str, Any]:
    """LION nodes two streets share (GAZETTEER LION 26A): finds intersections PRISM names differently, and shows when two
    SRs with different street names sit on one node (possible duplicates)."""
    r = _run(geo.lion_nodes, fresh, street1_like, street2_like, borough)
    return dict(count=len(r), nodes=r)


@mcp.tool(name='nycod_approx_direction', annotations=_ann('Estimate a blank corner direction'))
def nycod_approx_direction(
    cid: Annotated[int, Field(description='CMTCornerID whose CornerDirection is blank')], fresh: Fresh = False,
) -> dict[str, Any]:
    """Estimate a blank PRISM CornerDirection from the labelled corners around it (msb.py approx_dir). Label the answer
    '(approx.)'. A cardinal result (N/E/S/W) means the quadrant still has to be read from the block layout."""
    with bypass_cache(fresh):
        cs = geo.corners_by_id([cid])
        if not cs:
            return dict(cid=cid, found=False)
        c = cs[0]
        d = geo.approx_dir(c['lat'], c['lon'], c['on'], c['frm'])
    return dict(cid=cid, prism_direction=c['dir'], approx=d, label=f'{d} (approx.)' if d else None,
                cardinal=d in ('N', 'E', 'S', 'W') if d else None, on=c['on'], frm=c['frm'])


# ------------------------------------------------------------------ Open Data (Stage 7)
@mcp.tool(name='nycod_permits_at_intersection', annotations=_ann('Street permits at an intersection'))
def nycod_permits_at_intersection(
    borough: Boro, street1: str, street2: str,
    since: Annotated[str, Field(description='Issued on or after, YYYY-MM-DD (skill: one year before the complaint)')],
    all_types: Annotated[bool, Field(description='Every permit type; default keeps ramp/sidewalk/curb/corner/ped/SIM-CWC/restoration/test pit/foundation/signal')] = False,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """Street Construction Permits (tqtj-sjs8) on street1 at/from/to street2 either way round, exact street-name match
    after normalising (msb.py permits_at). Each row is tagged CWC when permittee NYC DEPT OF TRANSPORTATION has a SIM/CWC type."""
    bn = geo.OD_BORO[geo.boro_num(borough)]
    rows = _run(od.permits_at, fresh, bn, street1, street2, since, keep=None if all_types else od.RAMP_TYPES)
    for r in rows:
        r['cwc'] = qow.cwc_permit(r)
        r['nycstreets'] = qow.NYCSTREETS + r['permitnumber']
    return dict(count=len(rows), borough=bn, since=since, permits=rows)


@mcp.tool(name='nycod_permits_at_address', annotations=_ann('Street permits at a house number'))
def nycod_permits_at_address(
    borough: Boro, house_number: str, street: str, since: str, fresh: Fresh = False,
) -> dict[str, Any]:
    """Every permit (all types) at one house number on one street since YYYY-MM-DD (msb.py permits_address)."""
    bn = geo.OD_BORO[geo.boro_num(borough)]
    rows = _run(od.permits_address, fresh, bn, house_number, street, since)
    for r in rows:
        r['cwc'] = qow.cwc_permit(r)
        r['nycstreets'] = qow.NYCSTREETS + r['permitnumber']
    return dict(count=len(rows), permits=rows)


@mcp.tool(name='nycod_permit_links', annotations=_ann('Quality of Work permit links'))
def nycod_permit_links(
    permits: Annotated[list[dict[str, Any]], Field(description='Key permit rows (as returned by the permit tools)')],
    corners: Annotated[list[str], Field(description="The SR's corner labels, e.g. ['SW', 'NE (approx.)']")],
    complaint_date: Annotated[str, Field(description='YYYY-MM-DD')],
) -> dict[str, Any]:
    """Order permits for a Quality of Work email: the ped ramp permit to screenshot first (in force on the complaint date
    when there is one), then those in force on the complaint date, then latest end date. Permits naming other quadrants
    are dropped. Links go to Richard's signed-in NYCStreets view (DOT network). No network calls."""
    r = qow.permit_links(permits, corners, complaint_date)
    return dict(links=[dict(permit=p, label=lbl, url=u) for p, lbl, u in r])


@mcp.tool(name='nycod_ramp_program', annotations=_ann('Pedestrian Ramp Program Progress'))
def nycod_ramp_program(cids: Annotated[list[int], Field(min_length=1, max_length=1000)], fresh: Fresh = False) -> dict[str, Any]:
    """Pedestrian Ramp - Program Progress (e7gc-ub6z) per CMTCornerID: status (construc_2: Constructed, Planned
    Construction, Not Assigned, Not Required, Complex ...), construction type (constructi: Upgrade / New Install),
    completed (construc_1). Credit each row to its own CMTCornerID, never by direction."""
    r = _run(od.ramp_program, fresh, cids)
    return dict(rows={str(k): dict(status=v.get('construc_2'), construction_type=v.get('constructi'),
                                   completed=od.od_date(v.get('construc_1')), street1=v.get('street_nam'),
                                   street2=v.get('street_n_1'), borough=v.get('borough')) for k, v in r.items()},
                corners_without_row=[c for c in cids if int(c) not in r])


@mcp.tool(name='nycod_ramp_complaints', annotations=_ann('Pedestrian Ramp Complaints history'))
def nycod_ramp_complaints(
    cids: Annotated[list[int] | None, Field(description='CMTCornerIDs')] = None,
    sr: Annotated[str | None, Field(description="Or one SR number, '311-xxxxxxxx'")] = None,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """Pedestrian Ramp Complaints (jagj-gttd): earlier complaints and temporary repairs on corners (newest first), or the
    rows logged for one SR (logging lags about a week). temp_repair_date marks a corner made safe before."""
    if not cids and not sr:
        raise ValueError('give cids or sr')
    r = _run(od.ramp_complaints, fresh, cids=cids, sr=sr)
    return dict(count=len(r), rows=r, made_safe=[x for x in r if x.get('temp_repair_date') or x.get('date_second_temp_repair')])


@mcp.tool(name='nycod_capital_projects_near', annotations=_ann('Completed capital projects near a point'))
def nycod_capital_projects_near(
    lat: float, lon: float, meters: Annotated[float, Field(ge=1, le=2000)] = 60, fresh: Fresh = False,
) -> dict[str, Any]:
    """Street and Highway Capital Reconstruction Projects - Intersection (97nd-ff3i) within `meters` (skill: 60 per
    corner). Every row is a completed project; construc_2 is the completion date."""
    r = _run(od.capital_near, fresh, lat, lon, meters)
    return dict(count=len(r), projects=r)


@mcp.tool(name='nycod_311_near', annotations=_ann('Public 311 requests near a point'))
def nycod_311_near(
    lat: float, lon: float, meters: Annotated[float, Field(ge=1, le=1000)] = 50,
    since: Annotated[str | None, Field(description='Created on or after, YYYY-MM-DD')] = None,
    dot_sidewalk_only: Annotated[bool, Field(description='Only DOT Sidewalk Condition / Curb Condition (incl. Pedestrian Ramp Defective)')] = True,
    limit: Annotated[int, Field(ge=1, le=2000)] = 200,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """Public 311 Service Requests (erm2-nwe9) near a point, newest first: duplicates and repeat complaints at a corner.
    The public unique_key is not the Dynamics 311-xxxxxxxx number; match by place and date."""
    r = _run(od.nyc311_near, fresh, lat, lon, meters, since, dot_sidewalk_only, limit)
    return dict(count=len(r), requests=r)


# ------------------------------------------------------------------ general access
@mcp.tool(name='nycod_soql_query', annotations=_ann('SoQL query on any NYC Open Data dataset'))
def nycod_soql_query(
    dataset_id: Annotated[str, Field(description="Dataset 4x4 id, e.g. 'tqtj-sjs8'", pattern=r'^[a-z0-9]{4}-[a-z0-9]{4}$')],
    select: str | None = None, where: str | None = None, order: str | None = None, group: str | None = None,
    q: Annotated[str | None, Field(description='Full-text search')] = None,
    limit: Annotated[int, Field(ge=1, le=50000)] = 100, offset: Annotated[int, Field(ge=0)] = 0,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """SoQL against any NYC Open Data dataset ($select/$where/$order/$group/$q/$limit/$offset). Use nycod_dataset_info
    first for the field names. Text values in $where take single quotes."""
    r = _run(od.soql, fresh, dataset_id, select, where, order, group, limit, offset, q)
    return dict(count=len(r), rows=r, next_offset=offset + len(r) if len(r) == limit else None)


@mcp.tool(name='nycod_dataset_info', annotations=_ann('NYC Open Data dataset columns and freshness'))
def nycod_dataset_info(
    dataset_id: Annotated[str, Field(pattern=r'^[a-z0-9]{4}-[a-z0-9]{4}$')], fresh: Fresh = False,
) -> dict[str, Any]:
    """Name, description, last update and columns (field name, label, type) of an NYC Open Data dataset. The skill's four:
    tqtj-sjs8 permits, 97nd-ff3i capital projects, e7gc-ub6z ramp program, jagj-gttd ramp complaints; also erm2-nwe9 (311)."""
    return _run(od.dataset_info, fresh, dataset_id)


@mcp.tool(name='nycod_arcgis_query', annotations=_ann('Query a DOT ArcGIS MapServer layer'))
def nycod_arcgis_query(
    service: Annotated[str, Field(description="e.g. 'PRISM/PRISM_CORNERS', 'GAZETTEER/LION', 'GAZETTEER/MapPLUTO'", pattern=r'^[A-Za-z0-9_]+/[A-Za-z0-9_]+$')],
    layer: Annotated[int, Field(ge=0)] = 0,
    where: Annotated[str, Field(description="SQL where, e.g. \"CMTCornerID=1108794\"")] = '1=1',
    out_fields: str = '*',
    return_geometry: bool = False,
    result_record_count: Annotated[int, Field(ge=1, le=2000)] = 200,
    fresh: Fresh = False,
) -> dict[str, Any]:
    """Read-only query on a DOT ArcGIS MapServer layer at a841-dotweb01.nyc.gov (outSR 4326). For layer schemas use
    where='1=0' and read 'fields'."""
    with bypass_cache(fresh):
        r = geo.q(service, layer, where=where, outFields=out_fields,
                  returnGeometry='true' if return_geometry else 'false', outSR=4326, resultRecordCount=result_record_count)
    feats = r.get('features', [])
    return dict(count=len(feats), exceeded_transfer_limit=r.get('exceededTransferLimit', False),
                fields=[dict(name=f['name'], type=f.get('type'), alias=f.get('alias')) for f in r.get('fields', [])],
                features=[(f['attributes'] | ({'geometry': f['geometry']} if return_geometry and 'geometry' in f else {}))
                          for f in feats])


@mcp.tool(name='nycod_links', annotations=_ann('Street Smart, Dynamics and NYCStreets links'))
def nycod_links(
    lat: float | None = None, lon: float | None = None,
    guid: Annotated[str | None, Field(description='Dynamics record GUID')] = None,
    permit: Annotated[str | None, Field(description='Permit number')] = None,
) -> dict[str, Any]:
    """Build links without a network call: Street Smart (100 ft box, EPSG:3857), Dynamics record, NYCStreets permit page."""
    out = {}
    if lat is not None and lon is not None:
        X, Y = geo.TO2263.transform(lon, lat)
        out['streetsmart'] = geo.streetsmart(X, Y)
        out['state_plane'] = dict(X=X, Y=Y)
    if guid:
        out['dynamics'] = geo.dynamics_link(guid)
    if permit:
        out['nycstreets'] = qow.NYCSTREETS + permit.strip()
    return out


@mcp.tool(name='nycod_clear_cache', annotations=ToolAnnotations(title='Clear the local answer cache', read_only_hint=False,
          destructive_hint=False, idempotent_hint=True, open_world_hint=False) if 'read_only_hint' in ToolAnnotations.model_fields
          else ToolAnnotations(title='Clear the local answer cache', readOnlyHint=False, destructiveHint=False,
                               idempotentHint=True, openWorldHint=False))
def nycod_clear_cache() -> dict[str, Any]:
    """Delete this server's cached answers (only files it wrote in its cache folder). Use when you need every source re-read."""
    return dict(removed=clear_cache(), cache=CACHE)


def main():
    mcp.run()


if __name__ == '__main__':
    main()
