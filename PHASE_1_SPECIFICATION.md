# PHASE 1: KPI Foundation - Implementation Specification
## Unified KPI Registry — Ready to Execute

**Status:** READY FOR IMPLEMENTATION  
**Scope:** Build KPIRegistry class + consolidate 51 KPIs  
**Success:** All 51 KPIs loaded, no duplicates, >95% test coverage  

---

## DELIVERABLES

### 1. `src/socrata_toolkit/kpi/models.py` (~400 lines)
Data structures from KPI_REGISTRY_COMPREHENSIVE_DESIGN.md Section 1:
- ThresholdLevel (bronze/silver/gold)
- TimeSeriesMetadata (forecasting config)
- DimensionConfig (dimension breakdowns)
- KPIDefinition (complete spec)
- KPIValue, Trend, KPIResult (computation results)

All with type hints, docstrings, validation methods.

### 2. `src/socrata_toolkit/kpi/registry.py` (~600 lines)
Singleton KPIRegistry class:
- load_definitions() → Load all 51 KPIs from DATASET_REGISTRY.yaml
- get_kpi(id) → Retrieve by ID
- get_kpis_by_category(cat) → Filter by category
- get_kpis_by_dashboard(db) → Filter by dashboard
- validate_registry() → Check for duplicates, missing fields
- get_chart_recommendations(id) → List optimal chart types

Cache in memory, thread-safe singleton pattern.

### 3. `DATASET_REGISTRY.yaml` Update
Ensure all 51 KPIs with complete specs:
- kpi_id, name, category, unit, direction, target
- Thresholds (bronze/silver/gold with colors)
- time_series_config, dimensions, materialization_sql
- primary_chart_type, alternative_charts
- dashboard_sections, refresh_frequency

Validate chart types against EXPANDED_KPI_CHART_REGISTRY.md.

### 4. `tests/test_kpi_registry.py` (~300 lines)
Unit tests:
- TestKPIDefinition: Validation, enums, immutability
- TestKPIRegistry: Load 51 KPIs, no duplicates, query methods
- TestTimeSeriesMetadata: Forecast configs
- TestDimensionConfig: Aggregations
- Coverage: >95% pass rate, >90% code coverage

### 5. `docs/PHASE_1_COMPLETION_REPORT.md`
Final report:
- 51 KPIs consolidated
- Validation results
- Test coverage metrics
- Integration points for Phase 2

---

## GIT WORKFLOW

Commit after EACH file:

1. Create `src/socrata_toolkit/kpi/__init__.py` → git add, commit, push
2. Create `src/socrata_toolkit/kpi/models.py` → commit, push
3. Create `src/socrata_toolkit/kpi/registry.py` → commit, push
4. Update `DATASET_REGISTRY.yaml` → commit, push
5. Create `tests/test_kpi_registry.py` → commit, push
6. Create `docs/PHASE_1_COMPLETION_REPORT.md` → commit, push

**Commit template:**
```
feat(kpi-registry): [subsystem]

- What was added
- Why it matters
- Impact on Phase 2

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

Before each push: `git pull origin main` to handle conflicts.

---

## SUCCESS CRITERIA

**Code:**
- [ ] All 51 KPIs loaded from YAML
- [ ] No duplicate IDs
- [ ] 100% type hints
- [ ] Docstrings on all public methods
- [ ] ruff check passes
- [ ] Black formatting

**Tests:**
- [ ] >95% pass rate
- [ ] >90% code coverage
- [ ] Edge cases covered

**Git:**
- [ ] All commits pushed to origin/main
- [ ] No uncommitted changes
- [ ] Ready for Phase 2

---

## READY FOR FOUNDATION ARCHITECT SUBAGENT

This specification is complete and sufficient for implementation.

Next step: Dispatch Foundation Architect with this spec.

