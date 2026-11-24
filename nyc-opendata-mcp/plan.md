# plan.md: NYC Open Data MCP for make-safe-batch

Status: approved by request 11/24/2026 ("plan then create"). This file is the source of truth; change it before changing scope.

## Goal

Run the data side of `/make-safe-batch` locally (Claude Desktop or Claude Code on Richard's machine) for any SR, using one MCP server that reaches the same public sources `msb.py` uses, with the same query logic, so the results match what the skill would compute in a cloud session.

"To the greatest possible extent" means: every step whose input is public data is a tool. Steps that rest on judgment, imagery, signed-in DOT systems or Richard's own actions stay where the skill puts them, and the server says so in its output instead of guessing (H1, H2).

## What the skill needs from outside data (from the skill notes, 11/24/2026)

| Stage | Need | Source | Reachable publicly |
|---|---|---|---|
| 2 Corners | corners near a point, at a named intersection, by ID; ramps per corner; BBL; direction when blank | DOT ArcGIS `PRISM/PRISM_CORNERS` 0, `PRISM/PRISM_RAMPS` 0 | yes |
| 2 Corners | geocode an SR with no Lat/Lon; intersections PRISM names differently | DOT ArcGIS `GAZETTEER/AddressPoint`, `GAZETTEER/MapPLUTO`, `GAZETTEER/LION` | yes |
| 3 Routing (step 2, made-safe-before, P58) | earlier complaints and temporary repairs per corner; whether this SR is logged | Open Data `jagj-gttd` | yes |
| 7 Open Data check | street permits one year back per street pair and house number | Open Data `tqtj-sjs8` | yes |
| 7 | completed capital projects within 60 m of each corner | Open Data `97nd-ff3i` | yes |
| 7 | ramp program status per corner (whole intersection) | Open Data `e7gc-ub6z` | yes |
| 1 Intake (duplicates) | other public 311 complaints at the same place | Open Data `erm2-nwe9` (DOT Sidewalk/Curb Condition) | yes; extra, not in msb.py |
| QoW | permit page links | NYCStreets (internal, sign-in) | link only |
| Imagery | Street Smart link | built from coordinates | link only |
| Intake | Dynamics deep link | built from the record GUID | link only |

## Out of scope (stays in the skill, or with Richard)

Routing decisions and type (decision order, type table), corner narrowing from the caller's words, Cyclomedia rendering and the visual check, forms, drafts, PavementWorks export (a signed-in CSV he exports), NYCStreets permit screenshots, Dynamics edits. The server returns facts and the rule each fact feeds; it never returns a route.

## Design

- Python 3.10+, MCP Python SDK 2.x (`MCPServer`), falling back to 1.x `FastMCP` if that is what is installed. stdio transport (local).
- Dependencies kept to what a locked-down Windows box will take: `mcp`, `pyproj`, `openpyxl`. HTTP is stdlib `urllib`, so `HTTPS_PROXY` and a custom CA bundle (`NYCOD_CA_BUNDLE`) work on the DOT network.
- Query logic ported from `msb.py` (fingerprint `32b7fd0c267a2749afb3df866a4e89e4`) function for function; parity is a test, not a hope.
- One change from msb.py, on purpose: the on-disk cache has a time limit (Open Data 6 h, ArcGIS 7 days, set by env), because msb.py's cache never expires and a long-lived local server would serve stale permits. `fresh=true` on any tool bypasses it.
- Socrata app token optional (`NYC_OPENDATA_APP_TOKEN`) for higher rate limits.
- Every data tool is read-only and says so in its annotations (`nycod_clear_cache` only touches its own cache folder).

### Package layout

```
nyc-opendata-mcp/
  plan.md
  README.md
  pyproject.toml
  src/nycod/
    __init__.py
    http.py        cached GET, retries, proxy/CA, app token
    geo.py         PRISM + GAZETTEER: corners, ramps, intersection, LION nodes, geocode, approx direction, links
    opendata.py    SODA: permits_at, permits_address, ramp_program, ramp_complaints, capital_near, nyc311_near, generic soql, metadata
    qow.py         cwc_permit, permit_links (Richard's 10/1 format)
    sr.py          SR parsing (address, borough, corners named in the caller's words) and the SR brief
    workbook.py    read the Dynamics table from his workbook by header, brief every SR
    server.py      MCP tools
    cli.py         nycod-brief command (same brief without an MCP client)
  tests/           live tests only (no mocks): parity with msb.py, real SRs, MCP stdio round trip
  configs/         Claude Desktop and Claude Code snippets
```

### Tools (prefix `nycod_`)

Workflow:
1. `nycod_sr_brief`: everything public for one SR: location resolved (Lat/Lon, intersection, or address), candidate corners with ramps, BBL, direction (approx. when PRISM is blank), Street Smart links; ramp program for every corner at the intersection; jagj-gttd history per corner and for this SR; permits one year back per street pair (PRISM and SR spellings) and house number, extended back to the earliest ramp program completion; capital projects per corner; nearby public 311 complaints; QoW permit links; plain facts each routing rule reads (made safe before, CWC permits, DELINQUENT / EXPIRED UNDER GUARANTEE, this SR logged or not). Optional `save_dir` writes `opendata/<SR>.json` and `summary.txt` in the layout Stage 7 records.
2. `nycod_workbook_briefs`: the same for every SR in a sheet of his workbook, columns found by header (intake rule).

Building blocks (each mirrors one msb.py helper):
3. `nycod_corners_near` 4. `nycod_intersection_corners` (with LION fallback) 5. `nycod_corners_by_id` 6. `nycod_ramps_by_corner` 7. `nycod_locate_address` 8. `nycod_lion_nodes` 9. `nycod_approx_direction` 10. `nycod_permits_at_intersection` 11. `nycod_permits_at_address` 12. `nycod_permit_links` 13. `nycod_ramp_program` 14. `nycod_ramp_complaints` 15. `nycod_capital_projects_near` 16. `nycod_311_near`

General:
17. `nycod_soql_query` any NYC Open Data dataset 18. `nycod_dataset_info` columns and freshness 19. `nycod_arcgis_query` any DOT ArcGIS MapServer layer (read-only query)

Added while building (11/24/2026):
20. `nycod_parse_sr_text` SR Address parts and corner words in the Description, no network 21. `nycod_links` Street Smart / Dynamics / NYCStreets links, no network 22. `nycod_clear_cache` deletes only this server's cache files (the one tool not marked read-only)

## Rules the code keeps

- H1: unknown stays blank and is flagged; nothing is filled in. Empty results are reported as empty, with the query that ran.
- H3: the brief carries the caller's Description verbatim when it is given.
- H10: directions from geometry carry "(approx.)".
- Cyclomedia, Dynamics and PavementWorks credentials never pass through this server.

## Test plan (live, no mocks)

1. Parity: for real corners and streets, each ported function returns the same result as `msb.py`'s function.
2. Real SRs from jagj-gttd (e.g. 311-29486864, 311-29399735): the brief finds the logged corner among its candidates and the SR in the complaint history.
3. Address-only and intersection-only inputs resolve.
4. MCP stdio round trip: list tools, call `nycod_sr_brief`, get JSON back.
5. Workbook reader: a sheet built from live jagj-gttd rows (test fixture made from real data, marked as such) parses by header.

## Done when

Tests pass, the README gives the Claude Desktop and Claude Code setup for Windows, and the zip is delivered.
