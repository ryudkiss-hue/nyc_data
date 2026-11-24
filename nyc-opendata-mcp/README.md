# nyc-opendata-mcp

A local MCP server that gives Claude Desktop or Claude Code the public-data side of the make-safe-batch skill (NYC DOT SIM, SOP 20). It queries NYC Open Data and DOT's ArcGIS server (PRISM corners and ramps, GAZETTEER LION, AddressPoint and MapPLUTO) with the same query logic as the skill's `msb.py`, and the test suite checks that each helper returns what `msb.py` returns for the same live input.

The tools report facts. Routing, type and the final choice of corners rest on the imagery and the caller's words (hard rules H1 and H2), so they stay with the skill and with you. Each brief lists what it did not cover under `not_covered`.

## What it reads

| Source | Used for |
|---|---|
| PRISM_CORNERS, PRISM_RAMPS (a841-dotweb01.nyc.gov) | candidate corners, CMTCornerIDs, directions, BBL, ramps |
| GAZETTEER LION, AddressPoint, MapPLUTO | geocoding an SR with no Lat/Lon, intersections PRISM names differently, the SR's own tax lot |
| tqtj-sjs8 Street Construction Permits | permits one year back per street pair and house number |
| 97nd-ff3i Capital Reconstruction Projects - Intersection | completed projects within 60 m of each corner |
| e7gc-ub6z Pedestrian Ramp - Program Progress | program status for every corner at the intersection |
| jagj-gttd Pedestrian Ramp Complaints | earlier complaints, temporary repairs (made safe before), whether this SR is logged |
| erm2-nwe9 311 Service Requests | public sidewalk and curb requests near the SR, for duplicates (not in msb.py) |

Street Smart, Dynamics and NYCStreets come back as links only, since those need your sign-in. Dynamics links need `NYCOD_DYNAMICS_BASE` set to the record URL prefix your AddDynamicsHyperlinks macro uses (everything before the GUID); it isn't published here because it is an internal DOT address.

## Web app

The same brief runs in a browser as the Make Safe page of the repo's GitHub Pages site, **https://ryudkiss-hue.github.io/nyc_data/make-safe/**, built from `site/make-safe/`. It needs no install: NYC Open Data and DOT's ArcGIS server both allow browser requests from that page, so it queries them directly, and a workbook you open there is read in the browser and never uploaded. A link such as `make-safe/?sr=311-29399735&borough=Brooklyn&street1=7%20Avenue&street2=Lincoln%20Place&complaint_date=2026-10-20&run=1` opens with the form filled and runs it.

`site/make-safe/brief.js` is a port of `src/nycod`, and `site/tests/parity.mjs` checks it against this package on the same live SRs (from the repo root):

```
pip install -e nyc-opendata-mcp
python site/tests/make_py_briefs.py
cd site && npm ci && npm run parity
```

## Install on Windows

You need Python 3.10 or newer. Clone `ryudkiss-hue/nyc_data` (or download it as a zip from GitHub) somewhere permanent, open a terminal in its `nyc-opendata-mcp` folder, and run:

```
py -m pip install --user .
```

Then check it works against live data before wiring it into Claude:

```
py -m nycod.cli --sr 311-29399735 --borough Brooklyn --street1 "7 Avenue" --street2 "Lincoln Place" --date 2026-10-20
```

That SR is the Lincoln Place case from precedent P47, so the output should show its two logged corners (1108794, 1108796) and the 7/20/2026 temporary repair.

### Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Settings, Developer, Edit Config) and add the server under `mcpServers`; `configs/claude_desktop_config.json` has the block. If `py` isn't on the PATH Claude Desktop sees, replace it with the full path that `where python` prints. Restart Claude Desktop afterwards.

### Claude Code

```
claude mcp add nyc-opendata -- py -m nycod.server
```

## On the DOT network

The server uses Python's standard HTTP library, so `HTTPS_PROXY` works as usual. If DOT's TLS inspection makes requests fail with a certificate error, export the DOT root certificate as a PEM file and set `NYCOD_CA_BUNDLE` to its path in the `env` block of the config. A Socrata app token in `NYC_OPENDATA_APP_TOKEN` raises the Open Data rate limit, which helps with whole-workbook runs.

Answers are cached in `%USERPROFILE%\.cache\nycod` (or `NYCOD_CACHE`): Open Data for 6 hours (`NYCOD_TTL_OPENDATA`) and ArcGIS for 7 days (`NYCOD_TTL_ARCGIS`). Unlike `msb.py`, whose cache never expires, a cached answer here goes stale on schedule, because a server left running for weeks would otherwise keep handing back last month's permits. Any tool takes `fresh: true` to skip the cache, and `nycod_clear_cache` empties it.

## Tools

`nycod_sr_brief` is the one to start with. Give it the SR number with whatever Dynamics has (Lat/Lon, SR Address, Created On, Description, GUID) or two streets and a borough. It resolves the SR point the way the corners note describes, including the switch to the AddressPoint when the Dynamics point is more than 100 ft off. It then reads every source above for every corner at the intersection and returns:

- candidate corners, flagged for within the radius, at the named intersection, on the SR's lot, or named by the caller
- the corners-table row that fits the input
- permits tagged CWC, ped ramp, temporary pedestrian walk, test pit, delinquent or expired under guarantee
- the QoW permit links in the order `permit_links` uses
- a `facts` block with the rules those facts feed (P58, made-safe-before, QoW routing, decision order step 6) and a plain-text `summary`

With `save_dir` set to `<batch>/work/opendata` it writes `<SR>.json`, `<SR>.summary.txt` and a combined `summary.txt`, matching where Stage 7 keeps its raw pulls.

`nycod_workbook_briefs` runs the same brief for every SR on one tab of the weekly workbook, finding columns by header as the intake note requires (Dynamics tables and ARTs blocks). The workbook is opened read-only. Call it without `sheet` to see which tabs hold SRs.

The remaining tools are the individual helpers, one per job: `nycod_corners_near`, `nycod_intersection_corners` (with the LION fallback), `nycod_corners_by_id`, `nycod_ramps_by_corner`, `nycod_locate_address`, `nycod_lion_nodes`, `nycod_approx_direction`, `nycod_permits_at_intersection`, `nycod_permits_at_address`, `nycod_permit_links`, `nycod_ramp_program`, `nycod_ramp_complaints`, `nycod_capital_projects_near` and `nycod_311_near`. They're joined by `nycod_parse_sr_text` and `nycod_links`, which make no network calls, and by general access through `nycod_soql_query`, `nycod_dataset_info` and `nycod_arcgis_query`.

## Command line

`nycod-brief` (or `py -m nycod.cli`) runs the brief without an MCP client:

```
py -m nycod.cli --workbook "Make Safe Dynamics and ARTs complaints as of 11-23-26.xlsx"
py -m nycod.cli --workbook "Make Safe Dynamics and ARTs complaints as of 11-23-26.xlsx" --sheet Richard --save work\opendata
py -m nycod.cli --address "150 WILLIAM STREET, MANHATTAN, NY, 10038" --date 2026-11-10 --json
```

## Tests

Every test reads the live services; nothing is mocked. The parity tests compare against the skill's own `msb.py`, which isn't published in this repository: set `MSB_REFERENCE` to a local copy (the skill's `assets/msb.py`) to run them, and they check its AST fingerprint is `32b7fd0c267a2749afb3df866a4e89e4` first. Without it they are skipped. The SR tests pull the most recent 311 complaints from jagj-gttd at run time and check that the brief finds the corner DOT logged. The MCP test starts the server over stdio, as Claude Desktop does.

```
py -m pip install --user .[test]
py -m pytest -q
```

A full run takes two to three minutes, mostly waiting on ArcGIS.

## Differences from msb.py

The query strings, filters and sort orders are unchanged. A few changes were made on purpose. The cache expires. Borough arguments also accept names and letter codes, not only 1-5. `permit_links` reads permit fields with `.get`, because Socrata leaves null fields out of a row and `msb.py` would raise a KeyError on a permit with no end date. `locate_address` returns nothing, instead of raising, for a house number that isn't numeric after the hyphen is removed. The brief sorts its permits by issue date and then permit number, because Socrata returns permits issued at the same second in no fixed order, and two runs of the same SR should list them the same way. And the Dynamics link prefix comes from `NYCOD_DYNAMICS_BASE` instead of being written into the code.
