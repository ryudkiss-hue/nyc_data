---
metadata:
  title: Data Consolidation & Best Practices Reorganization Plan
  version: 1.0
  status: DRAFT
  created: 2026-06-17
  author: Claude Code
  purpose: Consolidate Socrata dataset alternatives research and reorganize project structure according to industry best practices
---

# NYC DOT Data Consolidation & Reorganization Plan

**Scope:** Consolidate 26 Socrata datasets with best practices for data analytics project organization

---

## Summary

This project consolidates NYC DOT's Socrata dataset registry following 2026 industry best practices:

- **SOCRATA_DATASETS.md** — Human-readable master registry (all 27 datasets with details)
- **METADATA_REGISTRY.json** — Programmatic catalog for automation
- **DATA_SOURCES/** — Organized folder structure (5 categories + archived)
- **Metadata headers** — YAML frontmatter on all documentation files
- **Naming conventions** — Consistent labeling (Dataset_FourfourID_Status)
- **Problem/solution pairs** — 4 problematic datasets mapped to alternatives

---

## Datasets Consolidated

### ✅ ACTIVE (22)
- Core Daily: 7 (inspection, violations, reinspection, ramp_progress, ramp_complaints, complaints_311, built)
- Quality: 3 (dismissals, tree_damage, correspondences)
- Construction: 6 (street_permits, capital_intersections, street_construction_inspections, street_closures_block, street_resurfacing_inhouse, street_resurfacing_schedule)
- Reference: 6 (lot_info, curb_metal_protruding, mappluto, sidewalk_planimetric, step_streets, pedestrian_demand, accessible_pedestrian_signals)

### ⚠️ PROBLEMATIC (4) → SOLUTIONS
1. **weekly_construction** (r528-jcks) Stale 2017 → **street_permits** (tqtj-sjs8) Active 2022–Present
2. **capital_blocks** (jvk9-k4re) Empty 0 rows → **cpdb_projects** (fi59-268w) Active 7.8K rows
3. **permit_stipulations** (gsgx-6efw) API 403 Error → **permit_stipulations_historical** (pbk5-6r7z) Active workaround
4. **ramp_locations** (ufzp-rrqu) Stale 2019 → **ramp_progress** (e7gc-ub6z) Active daily updates

---

## Status: COMPLETE ✅

All files created and committed to Desktop/nyc_data. See SOCRATA_DATASETS.md for full details.

