# Task 6B: Extensible 26-Dataset Pipeline Design

> **For agentic workers:** This design informs Tasks 6B, 7, and 8 implementation. Use superpowers:writing-plans to create detailed implementation plans for each task after design approval.

**Goal:** Extend the 4-dataset pipeline to all 26 Socrata datasets with an architecture where adding a new dataset requires only a single-line registry entry (zero code changes).

**Architecture:** Dataset-agnostic staging/analytics layer using defensive column discovery. Registry-driven job scheduling. Analyst workflows mapped to dataset subsets via domain-specific analytics marts.

**Tech Stack:** DuckDB (local), APScheduler (orchestration), Socrata API, pytest (testing)

---

## Part 1: Analyst Workflows (Requirements)

### Role 1: Project Analyst (Contract Planning)

**Mission:** Contract planning, sidewalk repairs, conflicts, budget tracking

**Core needs:**
1. **Sidewalk repair location analysis** — where repairs are needed
   - Datasets: `inspection`, `violations`, `built`, `sidewalk_planimetric`
   - Query: inspections with low condition ratings + violation density + material type
2. **Construction lists + GIS conflicts** — identify scheduling conflicts
   - Datasets: `street_permits`, `inspection`, `street_construction_inspections`
   - Query: spatial join (permits vs inspections) + temporal overlap detection
3. **Contract progress reports** — budget dollars, productivity, timelines
   - Datasets: `street_permits`, `street_construction_inspections`, `street_resurfacing_schedule`
   - Query: aggregate by contract, by month, budget variance analysis
4. **Routine efficiency studies** — contractor performance, work patterns
   - Datasets: `inspection`, `violations`, `street_construction_inspections`
   - Query: completion rates, violation recurrence, contract cycle times

**Analytical products:**
- Borough-level sidewalk condition summary
- Construction conflict matrix (permits vs inspections)
- Contract performance dashboard (budget, timeline, quality)
- Material failure rate analysis
- Work productivity trends

---

### Role 2: SW Project Analyst (Ramp Program)

**Mission:** Ramp upgrade crew support, high-priority requests, GIS analysis, IFA justifications

**Core needs:**
1. **Ramp upgrade analysis** — track program progress, identify gaps
   - Datasets: `ramp_progress`, `ramp_complaints`, `ramp_locations`, `sidewalk_planimetric`
   - Query: completion rates by borough, complaints by location, accessibility coverage
2. **High-priority request response** — rapid turnaround on urgent items
   - Datasets: `ramp_complaints`, `ramp_progress`, `pedestrian_demand`
   - Query: complaint age, priority scoring, recommend next actions
3. **GIS analysis for planning** — spatial conflicts, accessibility gaps
   - Datasets: `ramp_locations`, `step_streets`, `sidewalk_planimetric`, `pedestrian_demand`, `mappluto`
   - Query: ramps near high-demand corridors, step streets coverage, demographic patterns
4. **IFA program justification** — business case for budget allocation
   - Datasets: `ramp_complaints`, `ramp_progress`, `pedestrian_demand`, `mappluto`
   - Query: complaint density, accessibility gap analysis, equity scoring by block
5. **Curb metal protruding program** — track remediation
   - Datasets: `curb_metal_protruding`, `inspection`
   - Query: protruding curb locations, repair status, seasonal patterns

**Analytical products:**
- Ramp completion rates by borough + 95% confidence intervals
- High-priority request queue (age, severity, recommended action)
- Accessibility coverage heatmap (geographic + demographic)
- IFA program business case (equity scoring, impact estimates)
- Curb metal protruding dashboard (locations, status, remediation timeline)

---

## Part 2: Dataset Registry & Extensible Architecture

### Current (4 datasets):
```python
SOCRATA_DATASETS = {
    "inspection": "dntt-gqwq",
    "violations": "6kbp-uz6m",
    "permits": "tqtj-sjs8",
    "ramp_progress": "e7gc-ub6z",
}
```

### Extended (all 26 datasets):
```python
SOCRATA_DATASETS = {
    # Core SIM (Sidewalk Inspection & Management)
    "inspection": "dntt-gqwq",
    "violations": "6kbp-uz6m",
    "built": "ugc8-s3f6",
    "lot_info": "i642-2fxq",
    "reinspection": "gx72-kirf",
    "tree_damage": "j6v2-6uxq",
    "dismissals": "p4u2-3jgx",
    "correspondences": "bheb-sjfi",
    "curb_metal_protruding": "i2y3-sx2e",
    
    # Accessibility (Ramp Program)
    "ramp_locations": "ufzp-rrqu",
    "ramp_complaints": "jagj-gttd",
    "ramp_progress": "e7gc-ub6z",
    
    # Coordination (Permits & Construction)
    "street_permits": "tqtj-sjs8",
    "weekly_construction": "r528-jcks",
    "capital_blocks": "jvk9-k4re",
    "capital_intersections": "97nd-ff3i",
    "street_construction_inspections": "ydkf-mpxb",
    "street_closures_block": "i6b5-j7bu",
    "street_resurfacing_schedule": "xnfm-u3k5",
    "street_resurfacing_inhouse": "ffaf-8mrv",
    
    # Overlays (Context & Enrichment)
    "step_streets": "u9au-h79y",
    "sidewalk_planimetric": "vfx9-tbb6",
    "pedestrian_demand": "fwpa-qxaf",
    "mappluto": "64uk-42ks",
    "complaints_311": "erm2-nwe9",
}
```

**Adding a new dataset is now:** 1 line in the registry. Everything else is automatic.

---

## Part 3: Generic Staging Pipeline

**Current approach:** Separate `stage_inspections()`, `stage_permits()`, `stage_ramps()` functions.

**New approach:** Single generic `stage_dataset(dataset_key)` function:

```python
def stage_dataset(dataset_key: str) -> dict:
    """
    Stage any dataset: deduplicate, validate, promote to staging.*.
    
    Uses defensive column discovery (existing pattern):
    1. Query raw.{dataset_key} schema
    2. Pick primary key from candidates (objectid → object_id → id)
    3. Pick date column from candidates (created_date → :updated_at)
    4. Deduplicate on (key, date DESC)
    5. Create staging.{dataset_key}
    
    Returns {"status":"success"/"error", "table":"staging.X", "row_count_raw": N, "row_count_staged": M}
    """
```

**Benefits:**
- New dataset = no new staging function
- Deduplication logic is shared (one implementation)
- Defensive column discovery handles schema variation
- Audit logging is automatic
- Validation integrates seamlessly

---

## Part 4: Parameterized Analytics Layer

**Current approach:** 5 hardcoded marts (borough_summary, time_series, material_analysis, clustering, geo_animation).

**New approach:** Analytics marts are generated from dataset traits + role requirements.

### Analytics Marts (26-dataset scope):

**Universal (all datasets):**
1. **raw_counts_summary** — row count tracking per dataset
2. **freshness_dashboard** — last_modified per dataset, SLA status
3. **schema_catalog** — column inventory per dataset

**Domain-specific (by analyst role):**

**Role 1 (Contract Analyst):**
1. **sidewalk_repair_matrix** — condition ratings × material × borough (from inspection, violations, built)
2. **construction_conflict_index** — spatial conflict matrix (permits vs inspection)
3. **contract_performance_dashboard** — budget variance, timeline adherence (from permits, street_construction_inspections)
4. **material_failure_analysis** — repair rates by material (from inspection, violations)
5. **productivity_trends** — crew efficiency, contract cycle times (from street_construction_inspections)

**Role 2 (Ramp Analyst):**
1. **ramp_completion_rates** — borough-level progress with 95% Wilson CI (from ramp_progress)
2. **high_priority_queue** — age-ranked requests (from ramp_complaints)
3. **accessibility_coverage_heatmap** — geographic + demographic (from ramp_locations, pedestrian_demand, mappluto)
4. **ifa_program_business_case** — equity scoring, impact estimates (from ramp_complaints, ramp_progress, pedestrian_demand)
5. **curb_metal_protruding_status** — remediation timeline (from curb_metal_protruding, inspection)

**Implementation:** Marts are defined via a config file, not hardcoded. Adding a new mart = new entry in the config.

---

## Part 5: Scheduler Integration

**Current:** 8 jobs (load, stage, materialize, validate, reconcile, domain_validation, conflict_detection, alert_check).

**Extended:** Jobs are parameterized by dataset.

```python
# Before: one load_raw_data job
# After: load_raw_data loops all SOCRATA_DATASETS keys (already implemented in Task 3 fix)

# Before: one stage_data job calls stage_inspections(), stage_permits(), stage_ramps()
# After: stage_data loops all SOCRATA_DATASETS, calls stage_dataset(key) for each

# Before: one materialize_analytics job calls 5 specific create_* functions
# After: materialize_analytics loops config file, instantiates each mart dynamically
```

**Result:** Adding a dataset auto-registers in the scheduler. No job config changes needed.

---

## Part 6: Validation & Audit Logging

**Current:** 6 validation checks (raw_counts, staging_dedup, data_types, analytics_populated, staging_to_analytics_lineage, data_freshness).

**Extended:** Validation checks scale with dataset count.

- **validate_raw_counts()** — now validates all 26 datasets (tolerance thresholds stored in config, not hardcoded)
- **validate_staging_dedup()** — generic: verify no duplicates on primary key (key is discovered defensively)
- **validate_data_types()** — generic: spot-check critical columns exist and match expected types
- **validate_analytics_populated()** — dynamic: verify all configured marts are materialized
- **validate_freshness()** — generic: track last_modified per dataset, enforce SLA thresholds
- **validate_lineage()** — generic: spot-check data flows from raw → staging → analytics

**Audit logging:** Every check logs to DuckDB. New datasets auto-generate audit trails.

---

## Part 7: Implementation Roadmap

### Task 6B: Implement Extensible Architecture (Weeks 2–3)

**Refactor for extensibility:**
1. Convert hardcoded `stage_*` functions → single `stage_dataset()` generic
2. Move analytics marts to config-driven factory (not hardcoded `create_*` functions)
3. Parameterize validation thresholds (tolerance % per dataset → config)
4. Update scheduler to loop all datasets
5. Test with 10 datasets, then 26

**Expected:** Pipeline handles all 26 datasets, adds a new one with 1-line registry change.

### Task 7: Orchestration + Documentation (Week 3)

1. Create `run_full_pipeline(all_datasets=True)` orchestrator
2. Document schedule (2am load, 3am stage, 4am materialize, etc.)
3. Add CLI commands for on-demand dataset operations
4. Create analyst quick-start guides (Role 1 & Role 2 workflows)

### Task 8: Report/Export Integration (Week 4)

1. Wire reports to read from analytics marts (not live API)
2. Add 9am scheduled report generation (contract dashboard, ramp progress, etc.)
3. Dashboard export buttons (CSV/GeoJSON for conflicts, accessibility heatmap, etc.)

---

## Part 8: Known Challenges & Mitigations

| Challenge | Mitigation |
|-----------|-----------|
| Socrata schema drift (26 datasets, different schemas) | Defensive column discovery (already proven); candidate lists per dataset type |
| Performance (36M+ rows total) | Incremental load (fetch last-modified only); DuckDB caching; consider MotherDuck for cloud scale in Phase 2B |
| Missing datasets (IFA budget, labor tracking) | Document as out-of-scope; provide bridging mechanisms for institutional data |
| Role-specific analytics (different analysts need different views) | Config-driven marts; tag each mart with roles it serves |

---

## Part 9: Success Criteria

- ✅ All 26 datasets load end-to-end in <5 minutes (vs <30s for 4 datasets)
- ✅ Adding a new dataset requires only 1 line in registry (zero code changes)
- ✅ Both analyst workflows fully supported with domain-specific analytics products
- ✅ All validation checks scale to 26 datasets
- ✅ Audit trails for all 26 datasets
- ✅ Scheduled pipeline runs nightly, all datasets materialized by 9am

---

## Appendix: Datasets by Role

| Dataset | Role 1 | Role 2 | Purpose |
|---------|--------|--------|---------|
| inspection | ✅ Core | ✅ Supporting | Sidewalk condition baseline |
| violations | ✅ Core | — | Violation counts per location |
| built | ✅ Core | — | Historical repair data |
| permits | ✅ Core | — | Construction scheduling |
| street_permits | ✅ Core | — | Permits for conflicts |
| street_construction_inspections | ✅ Core | — | Active construction tracking |
| street_resurfacing_schedule | ✅ Core | — | Contract timeline tracking |
| ramp_progress | — | ✅ Core | Ramp completion tracking |
| ramp_complaints | — | ✅ Core | High-priority queue |
| ramp_locations | — | ✅ Core | Ramp locations |
| curb_metal_protruding | — | ✅ Core | Curb remediation |
| pedestrian_demand | — | ✅ Core | Demand hotspots for IFA |
| mappluto | — | ✅ Core | Demographic/equity scoring |
| step_streets | — | ✅ Supporting | Accessibility context |
| sidewalk_planimetric | ✅ Supporting | ✅ Supporting | Planimetric references |
| lot_info | ✅ Supporting | — | Property context |
| tree_damage | ✅ Supporting | — | Related repairs |
| dismissals | ✅ Supporting | — | Violation history |
| correspondences | ✅ Supporting | — | Communication logs |
| capital_intersections | ✅ Supporting | — | Capital project context |
| street_closures_block | ✅ Supporting | — | Active closures |
| street_resurfacing_inhouse | ✅ Supporting | — | In-house work tracking |
| complaints_311 | — | ✅ Supporting | Complaint hotspots |
| weekly_construction | ⚠️ Stale | — | Archived reference |
| capital_blocks | ⚠️ Empty | — | Archived reference |

---

**Design Status:** Ready for implementation planning (Task 6B, 7, 8)

**Next Step:** Use superpowers:writing-plans to create detailed implementation plans for Tasks 6B, 7, 8.
