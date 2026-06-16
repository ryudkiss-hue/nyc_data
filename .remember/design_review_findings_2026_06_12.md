---
name: design-review-critical-findings
description: Max-effort design review findings - Chart Finder routing, enforcement loop architecture, dataset sourcing feasibility
metadata:
  type: project
  date: 2026-06-12
  status: CRITICAL_BLOCKER
---

# Design Review: Critical Findings (2026-06-12)

## Angle 1: Chart Finder Routing ✅ GOOD (needs adjustments)

**Verdict:** Routing logic is fundamentally sound. 5 sampled questions routed to correct chart families.

**Issues Found:**
1. 4 weight calibration errors (CUSUM weight 5→3, Force Network 4→2, Ridge Plot 6→8, Line Chart weight 5→7)
2. 3 coverage gaps: cost breakdown, complaint resolution time patterns, violation recurrence patterns
3. 4 redundant questions: Q5 vs Q28 (both "geographic hotspot"), Q7 vs Q33 (neighborhood vs CB ranking), Q25 vs Q26 (both "violations overlapping layers"), Q21 vs Q23 (311 gap)

**Fix effort:** 1-2 hours (update weights, add 3 questions, consolidate redundant ones)

---

## Angle 2: Enforcement Loop Architecture 🔴 BROKEN (5 critical failures)

**Verdict:** Core 75-day enforcement flow has unresolved operational gaps. Not executable.

**Critical Failures:**

| Issue | Impact | Severity |
|-------|--------|----------|
| Dismissals handling UNDEFINED | When owner disputes violation: final or reversible? No decision logic. | CRITICAL |
| City work data FRAGMENTED | 3 datasets (pothole_workorders, street_resurfacing, concrete_repair) with no master join → cost billing impossible | CRITICAL |
| Lien policy CONTRADICTORY | Line 141: "NO LIENS for 1-3 family" vs Line 177: "NO LIENS except tree damage" → conflicting guidance | CRITICAL |
| Protected street timeline AMBIGUOUS | Violation can be issued during protection; 75-day clock timing relative to protection-window-end UNDEFINED → owner may have <30 days actual repair time | CRITICAL |
| Property lookup fallback MISSING | If BBL not found in MapPLUTO (orphaned lot), enforcement stops → coverage gap | CRITICAL |

**Additional gaps (7 more):**
- Reinspection disputes (appeals process undefined)
- City work authorization (who decides when to start? Proactive vs reactive?)
- Collections timing (bill on day 76 or on completion date?)
- Dismissal reinstatement (if dismissed day 20, does 75-day clock restart?)
- Tree damage defect vs spatial join logic (which is authoritative?)
- Protected street workflow (defer violation issuance or post-protection deadline?)
- Notification delivery verification (what if certified mail fails?)

**Fix effort:** 12-16 hours to define dismissal rules, merge city-work datasets, resolve lien policy, add protected-street logic, define compliance rules

---

## Angle 3: Dataset Sourcing 🔴 NOT FEASIBLE (schema unknowns = silent failures)

**Verdict:** Cannot confidently execute any analyst query. Critical schema unknowns will cause silent join failures.

**Critical Schema Unknowns:**

| Join | Status | Risk |
|------|--------|------|
| violations → lot_info → mappluto (MAIN ENFORCEMENT) | UNVALIDATED | Schema doesn't confirm if violations has `block`/`lot` or only `bblid`. If wrong, join silently fails. |
| violations → street_tree_census (SPATIAL) | UNCONFIRMED | Violations schema does NOT list geometry column. ST_DWithin will crash. |
| violations → defect classification (Q13-Q16) | NO LOGIC DEFINED | Violations has no `defect_type`. Categorization must infer from 10 binary columns with NO documented business rules. |
| violations → correspondences → reinspection (75-DAY CURE) | UNDEFINED COLUMNS | Join keys exist but compliance logic missing. What rule defines "compliant"? |
| violations → cost datasets | IMPOSSIBLE | Q27 (financial impact) requires violations → pothole_workorders/street_resurfacing/concrete_repair. No documented join. |

**Additional Risks:**
- 24/51 datasets have UNKNOWN update frequencies (cannot guarantee SLA)
- Orphaned violations: If block/lot not in lot_info, LEFT JOIN silently drops record (no detection)
- 5 conflicting construction datasets: street_permits, inspections, capital projects, closures, DOB permits; NO deduplication logic
- Type mismatches: violations.block may be INTEGER/TEXT mismatch with lot_info; silent coercion may fail joins

**Currently Answerable:** Q1 (trend), Q2 (seasonality), Q5 (hotspots), Q28 (311 complaints)

**NOT Answerable:** Q7, Q9, Q13–Q16, Q17, Q20, Q24, Q27, Q29–Q31 (8 of 37 questions)

**Fix effort:** 20-24 hours total (schema validation 2h, defect taxonomy 4h, compliance rules 6h, cost mapping 4h, dataset freshness docs 3h, join validation testing 5h)

---

## Remediation Roadmap

**HALT Chart Finder rollout immediately.** Resolve 4 CRITICAL issues before any analyst query:

1. **Schema Validation (2h)** — Fetch violations/lot_info samples, confirm join keys exist and match types
2. **Defect Taxonomy (4h)** — Define binary columns → violation types mapping
3. **Compliance Rules (6h)** — Define: "A violation is COMPLIANT if [RULE]" with join chain + date handling
4. **Cost Tracking (4h)** — Document violation → city-work-dataset mapping with deduplication logic
5. **Dataset Freshness (3h)** — Confirm 24 unknown update frequencies, set SLA thresholds
6. **Join Testing (5h)** — Test each join on 100+ rows, measure cardinality, detect orphans

**Then:** Publish Data Dictionary with all join specs, business rules, column mappings.

**Reframe scope:** 37 → ~20 relevant questions. Remove unfeasible ones (Q7, Q9, Q13–Q16, Q20, Q24). Add mission-critical: "What's my compliance rate?" "Who's delinquent?" "Which blocks to inspect next?"

