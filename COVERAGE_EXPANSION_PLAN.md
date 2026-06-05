# Test Coverage Expansion Plan: 45.54% → 80%+ (NYC DOT SIM Toolkit)

## Current State
- **Overall Coverage**: 45.54% (1701 tests passing)
- **Target**: 80%+ overall coverage
- **Gap**: +34.46 percentage points

## Coverage Distribution Analysis

### Zero-Coverage Modules (Immediate Candidates)
These modules are untested and have moderate-to-large line counts:
- `lineage/manager.py`: 205 lines (0%)
- `lineage/persistence.py`: 196 lines (0%)
- `lineage/tracking.py`: 132 lines (0%)
- `spatial/database.py`: 285 lines (0%)
- `spatial/geodataframe.py`: 88 lines (0%)
- `spatial/metrics.py`: 184 lines (0%)
- `spatial/queries.py`: 220 lines (0%)
- `llm/chatbot.py`: 147 lines (0%)
- `llm/sql_engine.py`: 175 lines (0%)
- `ui/blocks/*`: 10+ modules with 0% coverage

### Low-Coverage Critical Modules (<40%)
These have high line counts and low coverage:
- `core/cli.py`: 1874 lines, 37% (1174 missing) — **HIGH IMPACT**
- `governance/audit.py`: 264 lines, 38% (164 missing)
- `spatial/analytics.py`: 441 lines, 15% (376 missing) — **HIGH IMPACT**
- `spatial/core.py`: 69 lines, 30% (48 missing)
- `spatial/visualization.py`: 250 lines, 20% (201 missing) — **HIGH IMPACT**
- `entity/blocking.py`: 193 lines, 36% (123 missing)
- `entity/relationships.py`: 159 lines, 52% (77 missing)
- `cdc/compliance.py`: 189 lines, 25% (141 missing)
- `engineering/ramp_analysis.py`: 108 lines, 30% (76 missing)

## Phased Approach to 80%

### Phase 1: Core Infrastructure (Weeks 1-2)
**Target: 55-60% coverage** by fixing high-impact low-coverage modules

1. **core/cli.py** (1874 lines, 37%)
   - Break into logical command groups
   - Target: Test all major CLI commands
   - Effort: 40-50 new tests (5-6 days)
   - Impact: +2-3% overall coverage

2. **spatial/analytics.py** (441 lines, 15%)
   - Test DBSCAN, TSP, clustering functions
   - Mock geographic operations
   - Effort: 30-35 new tests (3-4 days)
   - Impact: +1-1.5% overall coverage

3. **spatial/visualization.py** (250 lines, 20%)
   - Test plotting functions with mocks
   - Effort: 20-25 new tests (2-3 days)
   - Impact: +0.8-1% overall coverage

### Phase 2: Data & Analysis Modules (Weeks 3-4)
**Target: 65-70% coverage** by expanding mid-tier coverage

1. **analysis.py** (831 lines, 57%)
   - Fill gaps in complex analysis functions
   - Add edge case tests
   - Effort: 25-30 new tests (3-4 days)
   - Impact: +1-1.2% overall coverage

2. **governance/audit.py** (264 lines, 38%)
   - Test audit trail functions
   - Mock database operations
   - Effort: 20-25 new tests (2-3 days)
   - Impact: +0.8-1% overall coverage

3. **entity/blocking.py** (193 lines, 36%)
   - Test record blocking logic
   - Add integration tests
   - Effort: 20-25 new tests (2-3 days)
   - Impact: +0.7-0.9% overall coverage

### Phase 3: Specialized Modules (Weeks 5-6)
**Target: 70-75% coverage** by testing specialized functionality

1. **cdc/compliance.py** (189 lines, 25%)
   - Test compliance rules engine
   - Mock external services
   - Effort: 15-20 new tests (2 days)
   - Impact: +0.6-0.8% overall coverage

2. **engineering/ramp_analysis.py** (108 lines, 30%)
   - Test ramp completion calculations
   - Add statistical tests
   - Effort: 12-15 new tests (1-2 days)
   - Impact: +0.4-0.6% overall coverage

3. **entity/relationships.py** (159 lines, 52%)
   - Fill relationship logic gaps
   - Effort: 15-20 new tests (2 days)
   - Impact: +0.6-0.7% overall coverage

### Phase 4: Lineage & Advanced Features (Weeks 7-8)
**Target: 75-80% coverage** by testing new modules

1. **lineage/manager.py** (205 lines, 0%)
   - Test lineage tracking engine
   - Mock DAG operations
   - Effort: 20-25 new tests (3 days)
   - Impact: +0.8-1% overall coverage

2. **lineage/persistence.py** (196 lines, 0%)
   - Test persistence layer
   - Mock database operations
   - Effort: 18-22 new tests (2-3 days)
   - Impact: +0.7-0.9% overall coverage

3. **lineage/tracking.py** (132 lines, 0%)
   - Test tracking implementation
   - Effort: 15-18 new tests (2 days)
   - Impact: +0.5-0.7% overall coverage

### Phase 5: Optional Stretch Goals (Weeks 9+)
**Target: 80%+** by testing remaining modules

1. **spatial/database.py** (285 lines, 0%)
   - Test spatial database layer
   - Effort: 25-30 new tests (3-4 days)
   - Impact: +1-1.2% overall coverage

2. **spatial/queries.py** (220 lines, 0%)
   - Test query generation
   - Effort: 20-25 new tests (2-3 days)
   - Impact: +0.8-1% overall coverage

3. **llm/sql_engine.py** (175 lines, 0%)
   - Test SQL generation
   - Effort: 15-20 new tests (2 days)
   - Impact: +0.6-0.8% overall coverage

4. Minor modules to 85%+ coverage
   - material/compliance.py: 82% → 95% (5 new tests)
   - entity/reconciliation.py: 91% → 98% (3 new tests)
   - discovery/schema.py: 86% → 95% (8 new tests)

## Implementation Strategy

### Testing Approach by Module Type

**CLI Modules** (core/cli.py):
- Use pytest fixtures for setup
- Mock external API calls (Socrata, DuckDB)
- Test command parsing and output formatting
- Group tests by command category

**Spatial Modules** (analytics, visualization, core):
- Mock geospatial libraries (shapely, geopandas)
- Use synthetic test geometries
- Test edge cases (empty geometries, large datasets)
- Verify matplotlib/plotly output structures

**Lineage Modules** (manager, persistence, tracking):
- Mock graph operations
- Test DAG traversal logic
- Verify state transitions
- Test edge cases (cycles, orphans)

**Data Processing Modules** (analysis.py, entity/*):
- Create realistic test dataframes
- Test transformation pipelines
- Verify error handling
- Test performance with larger datasets

### Tools & Fixtures
- Use `@pytest.fixture` for reusable test data
- Mock external services with `unittest.mock`
- Use `tempfile` for file operations
- Create factory functions for complex objects

## Success Criteria

✓ **After Phase 1**: 55-60% overall coverage
✓ **After Phase 2**: 65-70% overall coverage
✓ **After Phase 3**: 70-75% overall coverage
✓ **After Phase 4**: 75-80% overall coverage
✓ **After Phase 5**: 80%+ overall coverage (GOAL)

## Estimated Effort
- **Total new tests**: 250-350 tests
- **Total time**: 8-10 weeks for full implementation
- **Parallel opportunity**: Phases can run concurrently on different modules

## Risk Mitigation
- Test high-impact modules first for quick wins
- Use incremental approach (test and commit frequently)
- Prioritize core CLI and analysis modules over UI/advanced features
- Verify no regressions in existing tests after each phase
