# Memory Index: NYC DOT Sidewalk Program Automation Tool

## Project Status
- [Handoff](remember.md) — Current state, blockers, next steps
- [Design Review Findings](design_review_findings_2026_06_12.md) — Max-effort audit (Chart Finder, enforcement loop, dataset sourcing) - CRITICAL BLOCKERS
- [NYC DOT Policy Definitive](nyc_dot_policy_definitive_2026_06_12.md) — Official policies sourced from Admin Code, Street Works Manual, OMB

## Project Context
- [Sidewalk Program Mission](sidewalk_program_mission.md) — Program context, enforcement loop, property owner classification, financial flows
- [Project Analyst Role](project_analyst_role.md) — Your actual responsibilities (6–9 hrs/week automation target)
- [311 Integration Plan](project_analyst_311_integration.md) — How 311 complaints feed the enforcement loop

## Key Decisions
- **Architecture:** Hybrid Edge-Cloud (local DuckDB cache + MotherDuck source + Claude NLP batch)
- **Scope:** Personal automation tool (single analyst, not enterprise)
- **Datasets:** 51 registered (inspection, violations, complaints_311, mappluto, permits, etc.)
- **Charts:** 65+ visualizations (8 multi-dim, 6 statistical, 6 D3.js)
- **Chart Finder:** 37 research questions → recommendations (needs weight calibration + schema validation)

## Critical Blockers (2026-06-12)
1. **Chart Finder:** Routing is GOOD; 4 weight calibrations + 3 coverage gaps needed (1–2 hours)
2. **Enforcement Loop:** BROKEN; 5 critical gaps (dismissals, city-work fragmentation, lien contradiction, timeline ambiguity, fallbacks) (12–16 hours)
3. **Dataset Sourcing:** NOT FEASIBLE; violations→lot_info→mappluto join schema UNVALIDATED, spatial join assumes missing geometry, defect-type logic UNDEFINED (20–24 hours)

**Action:** HALT Chart Finder rollout until schema validated + compliance rules defined + cost mapping documented.

