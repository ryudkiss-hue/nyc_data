# 🏛️ NYC DOT SIM Dataset Directory

**Last Generated:** 2026-06-06 23:37:42

This document serves as the technical reference for all 26 datasets integrated into the Manhattan Mission Control Powerhouse.

| # | Official Title | 4x4 ID | Schema Link |
| :--- | :--- | :--- | :--- |
| 1 | **SMD Inspection** | `dntt-gqwq` | [View Dataset](https://data.cityofnewyork.us/d/dntt-gqwq) |
| 2 | **SMD Violations** | `6kbp-uz6m` | [View Dataset](https://data.cityofnewyork.us/d/6kbp-uz6m) |
| 3 | **SMD Built** | `ugc8-s3f6` | [View Dataset](https://data.cityofnewyork.us/d/ugc8-s3f6) |
| 4 | **SMD Lot Info** | `i642-2fxq` | [View Dataset](https://data.cityofnewyork.us/d/i642-2fxq) |
| 5 | **SMD ReInspection** | `gx72-kirf` | [View Dataset](https://data.cityofnewyork.us/d/gx72-kirf) |
| 6 | **All Tree Damage** | `j6v2-6uxq` | [View Dataset](https://data.cityofnewyork.us/d/j6v2-6uxq) |
| 7 | **Sidewalk Dismissal Inspection Tracking** | `p4u2-3jgx` | [View Dataset](https://data.cityofnewyork.us/d/p4u2-3jgx) |
| 8 | **Sidewalk Correspondences** | `bheb-sjfi` | [View Dataset](https://data.cityofnewyork.us/d/bheb-sjfi) |
| 9 | **Pedestrian Ramp Locations** | `ufzp-rrqu` | [View Dataset](https://data.cityofnewyork.us/d/ufzp-rrqu) |
| 10 | **Ramp Complaints** | `jagj-gttd` | [View Dataset](https://data.cityofnewyork.us/d/jagj-gttd) |
| 11 | **Ramp Program Progress** | `e7gc-ub6z` | [View Dataset](https://data.cityofnewyork.us/d/e7gc-ub6z) |
| 12 | **Street Construction Permits** | `tqtj-sjs8` | [View Dataset](https://data.cityofnewyork.us/d/tqtj-sjs8) |
| 13 | **Weekly Construction Schedule** | `r528-jcks` | [View Dataset](https://data.cityofnewyork.us/d/r528-jcks) |
| 14 | **Capital Reconstruction Blocks** | `jvk9-k4re` | [View Dataset](https://data.cityofnewyork.us/d/jvk9-k4re) |
| 15 | **Capital Reconstruction Projects - Intersection** | `97nd-ff3i` | [View Dataset](https://data.cityofnewyork.us/d/97nd-ff3i) |
| 16 | **Street Construction Inspections (HIQA)** | `ydkf-mpxb` | [View Dataset](https://data.cityofnewyork.us/d/ydkf-mpxb) |
| 17 | **Street Closures by Block** | `i6b5-j7bu` | [View Dataset](https://data.cityofnewyork.us/d/i6b5-j7bu) |
| 18 | **Street Construction Permit Stipulations** | `gsgx-6efw` | [View Dataset](https://data.cityofnewyork.us/d/gsgx-6efw) |
| 19 | **Curb Metal Protruding Data** | `i2y3-sx2e` | [View Dataset](https://data.cityofnewyork.us/d/i2y3-sx2e) |
| 20 | **Step Streets Locations** | `u9au-h79y` | [View Dataset](https://data.cityofnewyork.us/d/u9au-h79y) |
| 21 | **Street Resurfacing Schedule** | `xnfm-u3k5` | [View Dataset](https://data.cityofnewyork.us/d/xnfm-u3k5) |
| 22 | **DOT In-house Street Resurfacing Projects** | `ffaf-8mrv` | [View Dataset](https://data.cityofnewyork.us/d/ffaf-8mrv) |
| 23 | **Planimetric Sidewalks** | `vfx9-tbb6` | [View Dataset](https://data.cityofnewyork.us/d/vfx9-tbb6) |
| 24 | **Pedestrian Demand** | `fwpa-qxaf` | [View Dataset](https://data.cityofnewyork.us/d/fwpa-qxaf) |
| 25 | **MapPLUTO** | `64uk-42ks` | [View Dataset](https://data.cityofnewyork.us/d/64uk-42ks) |
| 26 | **311 Sidewalk/Curb** | `erm2-nwe9` | [View Dataset](https://data.cityofnewyork.us/d/erm2-nwe9) |

---

## 🛠️ Automated Discovery Workflow

To discover and integrate a new dataset, run the following workflow:

```python
python scripts/discover_socrata.py --id [FOUR-FOUR]
```

This workflow will:
1. Query Socrata Metadata API.
2. Extract column names and types.
3. Validate Four Moments (Integrity Check).
4. Append to `config/datasets.yaml` and update `DATASETS.md`.
