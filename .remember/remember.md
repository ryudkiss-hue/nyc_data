# Handoff

## State

**CRITICAL BLOCKER FOUND:** Max-effort design review revealed Chart Finder and enforcement loop are **NOT PRODUCTION READY**.

**Completed (2026-06-12):**
- **Design review (3 angles):**
  - Chart Finder routing: GOOD but 4 weight calibrations needed, 3 coverage gaps, 4 redundant questions
  - Enforcement loop: BROKEN — 5 critical gaps (dismissals undefined, city-work cost tracking fragmented, lien policy contradictory, protected-street timeline ambiguous, property-lookup fallback missing)
  - Dataset sourcing: NOT FEASIBLE — violations→lot_info→mappluto join schema UNVALIDATED, spatial join assumes missing geometry, defect-type classification logic UNDEFINED
- **NYC DOT policy research (definitive sources):**
  - 75-day cure window: CONFIRMED (NYC Admin Code § 19-152)
  - Tree exemption (1-3 family): CONFIRMED for City-owned trees only (Admin Code § 7-210)
  - Dismissals: MANDATORY inspection via 311; no auto-close
  - Lien authority: Department of Finance (after 90-day non-payment)
  - Cost calculation: square-ft × price-per-sqft (specified on violation notice)
  - Billing: DOF bills; non-payment → lien
  - No fine on violation itself; cost from city-performed repairs
  - Defect list: 11 official criteria (cracks >0.5", vertical displacement >0.5", trip hazards, etc.)

**Critical findings:**
- 8 research questions NOT answerable with current data (Q7, Q9, Q13–Q16, Q17, Q20, Q24, Q27, Q29–Q31)
- Schema unknowns will cause silent join failures
- 24/51 datasets have unknown update frequencies

## Next

1. **URGENT (20–24 hours work):**
   - Run actual schema validation on violations/lot_info (fetch sample, confirm join keys)
   - Define defect-type classification logic (binary columns → categories)
   - Define compliance rule ("violation is compliant if...")
   - Define cost-tracking (violation → city-work-dataset mapping)
   - Halt Chart Finder rollout until above complete

2. **Data Dictionary (blockers resolution):**
   - Document all join specifications with validated column names
   - Publish defect taxonomy + business rules
   - Map violations to city-work datasets (pothole_workorders, street_resurfacing, concrete_repair)
   - Define update frequency SLAs for 24 unknown datasets

3. **Reframe scope (37 questions → ~20 relevant):**
   - Remove Q7, Q9, Q13–Q16, Q20, Q24 (unfeasible without schema clarity)
   - Add mission-critical questions: "What's my compliance rate?" "Who's delinquent?" "Which blocks should I inspect next?"

## Context

**Policy sources:**
- NYC Admin Code § 19-152 (Sidewalk Maintenance Responsibility)
- Street Works Manual 4.6 (Enforcement Procedures)
- NYC Parks Trees & Sidewalks Program (Tree Exemption)
- NYC Council hearing (Feb 2026) on sidewalk enforcement & snow-clearing

**Gotchas:**
- Dismissal is NOT automatic; owner must call 311 for reinspection. This changes enforcement flow.
- City bears repair cost if owner doesn't comply within 75 days; DOF collects via lien. Two agencies involved.
- Tree exemption is **City-owned trees ONLY**, not private. Spatial proximity join is risky (false positives).
- Defect list is official (11 items). Violation binary columns (broken, trip_haz, etc.) must map to this list with business rules.
- No official OMB reporting metrics published; specific compliance rates unknown.

**Personal tool scope:** This is solo analyst automation, not enterprise. Fast iteration, ruthless scope focus.
