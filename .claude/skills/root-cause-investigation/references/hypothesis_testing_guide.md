# Hypothesis Testing Guide — NYC DOT SIM Root Cause Investigation

Common root cause patterns for NYC DOT SIM metric changes, with diagnostic tests for each.

---

## Hypothesis Pattern Library

### H1: Staffing / Capacity Change

**Trigger:** Completion rate drops, throughput falls
**Test:** Plot `COUNT(objectid) GROUP BY unit_id` over time. Check if #active inspectors decreased.
**Data:** `inspection` (dntt-gqwq) → `unit_id` distinct count per month
**Confirmation:** Active inspector count correlates (r > 0.7) with completion rate change

### H2: Seasonal / Weather Effect

**Trigger:** Metric drops in December–February or during extreme heat (July–August)
**Test:** Compare same months across prior years. If drop recurs annually, seasonal.
**Data:** Monthly completion rate for 3+ years from `inspection`
**Confirmation:** YoY pattern consistent (< 5pp variance between same months in different years)

### H3: Data Entry / Recording Lag

**Trigger:** Apparent drop in recent months that doesn't match field reports
**Test:** Check null rate for `completion_date` and `inspection_date` in recent periods.
**Data:** `SELECT COUNT(*), SUM(CASE WHEN completion_date IS NULL THEN 1 ELSE 0 END) FROM inspection GROUP BY TRUNC(created_date, 'month')`
**Confirmation:** Null rate elevated in recent period; expected to self-correct

### H4: Dataset Staleness / Pipeline Failure

**Trigger:** Metric suddenly drops to zero or to an implausibly low value
**Test:** Check `last_modified` of dataset metadata vs. expected update frequency
**Data:** `client.get_metadata("data.cityofnewyork.us", "dntt-gqwq").row_modification_date`
**Confirmation:** `last_modified` > SLA threshold → pipeline issue, not a real program change

### H5: Geographic Concentration (Single-Borough Driver)

**Trigger:** City-wide metric drops but field reports indicate only one area affected
**Test:** Borough decomposition in `drilldown_analyzer.py`. One borough accounts for >60% of change.
**Data:** `completion_rate GROUP BY borough, month`
**Confirmation:** City-wide change is fully explained by one borough's change × its weight

### H6: Defect Type Mix Shift

**Trigger:** Completion rate changes without apparent capacity or process change
**Test:** Check mix of defect_type in current vs. baseline period.
**Data:** `SELECT defect_type, COUNT(*) FROM inspection GROUP BY defect_type, month`
**Confirmation:** Share of slow-resolving defect types (e.g. structural) increased in current period

### H7: Policy / Process Change

**Trigger:** Abrupt change (single-period step) that can't be explained by data quality
**Test:** Correlate exact change date with known DOT program events, regulatory changes, or system releases
**Data:** Internal change log, meeting minutes, JIRA/system release notes
**Confirmation:** Policy change date aligns within ±2 weeks of metric shift

### H8: Construction Conflict / Permit Surge

**Trigger:** Inspection delays spike in specific geographic areas
**Test:** `spatial_intersects_join(street_permits, inspection, "the_geom", "the_geom")` — check if permit density increased in affected area
**Data:** `street_permits` (tqtj-sjs8), `inspection` (dntt-gqwq)
**Confirmation:** Areas with high permit overlap show higher SLA breach rates

### H9: 311 Complaint Volume Spike

**Trigger:** Violation or inspection volume suddenly increases (driven by complaints)
**Test:** `complaints_311` (erm2-nwe9) — filter `agency = 'DOT'` and check for complaint surge in same period/geography
**Data:** `SELECT COUNT(*), borough FROM complaints_311 WHERE agency='DOT' GROUP BY month, borough`
**Confirmation:** Complaint spike precedes inspection volume increase by 7–14 days

---

## Diagnostic Checklist

Before closing an RCA:

- [ ] Is the change real (>2σ)? If not, document and close.
- [ ] Is the data current? (`last_modified` within SLA)
- [ ] Was it one borough or city-wide?
- [ ] Is it a rate change or a mix/volume change?
- [ ] Does it align with any known event (staffing, season, policy, permit, 311)?
- [ ] Has the hypothesis been tested against data, not just asserted?
- [ ] Is confidence level documented (Confirmed / Supported / Plausible / Speculative)?

---

## Correlation vs. Causation Warning

A high correlation between a suspected driver and the metric change does not confirm causation.

Required for "Supported" status:
1. Correlation exists (r > 0.65 or obvious visual alignment)
2. Timing is correct (cause precedes effect)
3. Mechanism is plausible (logical pathway exists)
4. No better alternative hypothesis explains the data equally well

If only (1) is present: "Plausible, not yet supported."
