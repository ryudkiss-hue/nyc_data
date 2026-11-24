# Streamlit → Dash Migration: Complete Documentation Index

**Project:** Manhattan Mission Control - Scalability Transformation  
**Date:** 2026-06-10  
**Status:** Planning, Ready for Phase 1 Execution

---

## Quick Start

**New to this migration?** Start here:

1. Read **MIGRATION_SUMMARY.txt** (5 min) — High-level overview
2. Skim **MIGRATION_PLAN.md** sections 1-3 (15 min) — Architecture & phases
3. Jump to **PHASE1_GIS_PILOT_TEMPLATE.md** (30 min) — Implementation guide

**Want specifics?** Jump to the relevant document below.

---

## Document Roadmap

### 1. MIGRATION_SUMMARY.txt
**Duration:** 5 minutes to read  
**Audience:** Team leads, stakeholders, anyone needing overview  
**Contains:**
- Problem statement (Streamlit latency, capacity limits)
- Solution architecture (hybrid Streamlit + Dash)
- Phased timeline (8 weeks, 137-160 hours)
- Effort estimates per view
- Success criteria & go/no-go gates
- Why Dash wins (comparative analysis)
- Next steps

**When to use:**
- Pitching to management
- Initial team alignment
- Budget/resource planning

---

### 2. MIGRATION_PLAN.md (PRIMARY DOCUMENT)
**Duration:** 45 minutes to read, reference ongoing  
**Audience:** Technical leads, architects, project managers  
**Contains:**
- Comprehensive 2000+ line migration strategy
- Hybrid architecture design (Section 1)
- Views to keep in Streamlit vs migrate to Dash (Section 1.1-1.2)
- Data bridge strategy (DuckDB + Redis)
- Phased rollout with detailed timelines (Section 2)
- Implementation approach (Section 3)
  - Callback organization
  - Session management patterns
  - Client-side vs server-side caching
- Testing strategy (Section 4)
  - Before/after performance comparison
  - Unit tests
  - Integration tests
- ACID + state management solutions (Section 5)
  - Session persistence
  - Multi-user concurrency
  - State mapping (Streamlit → Dash)
- Effort breakdown (Section 7)
- Risk assessment & rollback strategy (Section 8)
- Success criteria (Section 9)
- Implementation checklist (Section 10)
- Documentation & runbooks (Section 11)
- Future roadmap: 50 → 100+ charts (Section 12)

**When to use:**
- Architecture discussions
- Detailed project planning
- Risk mitigation planning
- Reference during development

---

### 3. DASH_ARCHITECTURE.md
**Duration:** 30 minutes to read, reference constantly  
**Audience:** Developers implementing callbacks  
**Contains:**
- Callback execution model (Streamlit vs Dash)
- Callback dependency graph with timing
- Pattern matching for flexible component IDs
- Session state persistence (3-tier model)
- Session ID lifecycle
- State sync: Streamlit ↔ Dash bridge
- What to store where (best practices table)
- Performance optimization patterns
  - Memoization with TTL
  - Lazy loading
  - Pre-computed aggregations
  - Debouncing
  - Async callbacks
- Code organization & naming conventions
- Multi-user concurrency guarantees
- Load testing (100 concurrent users)
- Troubleshooting guide
  - Callback timeout fixes
  - Redis connection exhaustion
  - Session data inconsistency
  - Memory bloat solutions
  - CSRF protection
- Performance metrics dashboard (Prometheus)
- Callback design principles

**When to use:**
- Understanding Dash callback model
- Implementing callbacks
- Performance troubleshooting
- Architecture decisions

---

### 4. PHASE1_GIS_PILOT_TEMPLATE.md
**Duration:** 30 minutes to read, 1-2 weeks to execute  
**Audience:** Developers implementing Phase 1 (GIS pilot)  
**Contains:**
- Week 1: Foundation & layout extraction
  - Task 1.1: Create GIS layout module (code template)
  - Task 1.2: Create GIS service layer (DBSCAN, TSP, etc.)
- Week 2: Callback implementation
  - Task 2.1: Create GIS callbacks (code templates for all 10 charts)
  - Task 2.2: Register callbacks in main app
- Week 3: Testing & performance baseline
  - Task 3.1: Unit tests for callbacks
  - Task 3.2: Performance baseline measurement (Selenium)
  - Task 3.3: Performance baseline report
- Final checklist (week 3 completion)
- Go/no-go decision criteria
- Deployment checklist

**When to use:**
- Starting Phase 1 implementation
- Week-by-week execution guide
- Copy-paste code templates
- Testing procedures

---

### 5. DASH_QUICK_REFERENCE.md
**Duration:** 10 minutes for overview, reference as needed  
**Audience:** Developers during implementation  
**Contains:**
- Callback patterns cheat sheet (6 patterns with code)
  - Single input → output
  - Multiple inputs → output
  - Pattern matching (50 charts)
  - State (don't trigger on change)
  - Prevent duplicate updates
  - Data store (browser-level state)
- Optimization patterns
  - Memoization
  - Lazy loading
  - Debouncing
- Session state management
  - Store filter in Redis
  - Load session on page load
- Common errors & fixes (table)
- Testing checklist
- Performance monitoring (instrumentation code)
- Deployment checklist
- Key files to know
- Quick commands (bash)
- Architecture decision records
- Getting help (troubleshooting)

**When to use:**
- Quick lookup of callback pattern
- Stuck on error? Check errors table
- Running deployment? Use checklist
- Need to monitor? Use commands

---

## Architecture Decision Records (ADRs)

### ADR 1: Why Dash instead of Streamlit?
**Decision:** Migrate visualization-heavy views to Dash  
**Rationale:**
- Streamlit: Full script rerun (5-15s) on every interaction
- Dash: Callback-based updates (<500ms)
- Result: 30x faster interactions, better UX
- Trade-off: More code, steeper learning curve

### ADR 2: Why Redis for session state?
**Decision:** Use Redis as session bridge between Streamlit + Dash  
**Rationale:**
- Both frameworks are separate apps
- Redis provides shared session store
- Filters set in Streamlit persist in Dash
- Alternative rejected: Cookies (too small, not secure)

### ADR 3: Why @memoize_with_ttl instead of Streamlit @st.cache?
**Decision:** Custom memoization for Dash callbacks  
**Rationale:**
- Streamlit cache tied to script execution
- Dash cache independent of page load
- Custom TTL control (5 min for fast data, 24h for slow data)
- Alternative rejected: Redis-only (overhead for small results)

### ADR 4: Why lazy load 50 charts?
**Decision:** Render only visible charts on initial load  
**Rationale:**
- All 50 charts: 20+ seconds to render
- Visible 3-5 charts: 2 seconds
- Lazy load remaining on scroll
- Result: 10x faster initial load

---

## Key Metrics & Targets

### Performance Targets

| Metric | Streamlit Baseline | Dash Target | Improvement |
|--------|-------------------|-------------|-------------|
| Initial page load | 8.2s | <2.5s | 97% faster |
| Borough filter | 12.1s | <0.5s | 96% faster |
| 3D toggle | 9.8s | <0.5s | 95% faster |
| Average interaction | 10.1s | <0.6s | 94% faster |
| P95 latency | 15.3s | 0.8s | 95% faster |

### Capacity Targets

| Metric | Current | Target | Headroom |
|--------|---------|--------|----------|
| Safe chart count | 64 | 50+ | 10-20 more |
| Max charts (with optimization) | ~100 | 200+ | Future proof |
| Concurrent users | ~50 | 100+ | 2x capacity |
| Charts per view | 2-10 | 8-15 | Flexible |

### Quality Targets

| Metric | Target | Method |
|--------|--------|--------|
| Unit test pass rate | 100% | pytest |
| Callback success rate | 95% | @timer_callback |
| Load test (100 users) | >95% success, <500ms P95 | Locust |
| Uptime | 99% during business hours | APM monitoring |
| Security | 0 vulnerabilities | Pen test |

---

## Implementation Timeline

```
Week 1 (Foundation)
├─ Extract GIS layout
├─ Create GIS service layer
├─ Build Redis session store
└─ 25 hours

Week 2 (Callbacks)
├─ Implement 10 GIS chart callbacks
├─ Add 3D + isochrone optimizations
├─ Sync session state
└─ 25 hours

Week 3 (Testing)
├─ Unit tests (15+ cases)
├─ Performance baseline
├─ Code review + merge
└─ 15 hours

Phase 1 Complete: GIS pilot live
Success Criteria: <500ms latency, 30x faster than Streamlit

Week 4-5 (Analytics Views)
├─ Migrate 8 chart Analytics view
└─ 30-35 hours

Week 6 (Contracts/Labor)
├─ Migrate 3 chart Labor view
└─ 22-25 hours

Phase 2 Complete: 2 more views live
Cumulative: 25 charts migrated

Week 7-8 (Optimization)
├─ Performance profiling
├─ A/B testing
├─ Security audit
├─ Load testing
└─ 20-25 hours

Phase 3 Complete: Full migration ready
Total: 137-160 hours, 8 weeks, 1-2 FTE
```

---

## Go/No-Go Decision Gates

### Phase 1 Completion (Week 3)

**GO Criteria (all must be true):**
- All 10 GIS charts render in <2 seconds ✓
- Filter interactions <500ms (P95) ✓
- 3D toggle memory increase <10% ✓
- 100 concurrent users: <500ms P95, >95% success ✓
- Zero data corruption / state inconsistency ✓
- 95% callback success rate (no timeouts) ✓
- Session sync works (Streamlit ↔ Dash) ✓
- 100% unit test pass rate ✓
- Code review approved ✓

**NO-GO Action:** Iterate on bottleneck, optimize, retest

**→ Proceed to Phase 2**

---

## How to Use This Documentation

### Scenario 1: Project Lead Asking "What's the Plan?"
1. Share **MIGRATION_SUMMARY.txt**
2. Point to effort estimate (137-160 hours, 8 weeks)
3. Highlight success criteria
4. Discuss resource needs (1-2 FTE)

### Scenario 2: Developer Starting Phase 1
1. Read **PHASE1_GIS_PILOT_TEMPLATE.md** end-to-end
2. Follow Week 1 checklist
3. Copy code templates from Task 1.1, 1.2
4. Refer to **DASH_ARCHITECTURE.md** for patterns
5. Use **DASH_QUICK_REFERENCE.md** for quick lookups

### Scenario 3: Callback Implementation Stuck
1. Check **DASH_QUICK_REFERENCE.md** errors table
2. Search **DASH_ARCHITECTURE.md** troubleshooting
3. Review **MIGRATION_PLAN.md** section 3 (code structure)
4. Copy pattern from **PHASE1_GIS_PILOT_TEMPLATE.md** Task 2.1

### Scenario 4: Performance Slow (>500ms)
1. Run `@timer_callback` (check logs)
2. Review **DASH_ARCHITECTURE.md** optimization patterns
3. Try `@memoize_with_ttl`
4. Check **DASH_QUICK_REFERENCE.md** commands
5. Run performance test: `pytest tests/test_gis_performance.py -v -s`

### Scenario 5: Deployment Time
1. Use **DASH_QUICK_REFERENCE.md** deployment checklist
2. Run smoke tests (basic functionality)
3. A/B test: 10% Dash, 90% Streamlit
4. Monitor error rates for 24h
5. Gradual ramp: 10% → 25% → 50% → 100%

---

## File Organization

```
C:\Users\ryudk\nyc_data\
├── MIGRATION_SUMMARY.txt                    (5 min, overview)
├── MIGRATION_PLAN.md                        (45 min, comprehensive)
├── MIGRATION_INDEX.md                       (this file, navigation)
├── DASH_ARCHITECTURE.md                     (30 min, deep dive)
├── DASH_QUICK_REFERENCE.md                  (10 min, cheat sheet)
├── PHASE1_GIS_PILOT_TEMPLATE.md             (30 min, implementation)
│
├── app/
│   ├── dash_app.py                          (existing, modify)
│   ├── dash_layouts.py                      (existing, extract GIS)
│   ├── dash_layouts_gis.py                  (NEW, Phase 1)
│   ├── callbacks/
│   │   ├── gis_spatial.py                   (NEW, Phase 1)
│   │   ├── gis_3d.py                        (NEW, Phase 1)
│   │   ├── base.py                          (NEW, decorators)
│   │   ├── analytics_stats.py               (NEW, Phase 2)
│   │   ├── contracts_labor.py               (NEW, Phase 2)
│   │   └── __init__.py                      (NEW, registry)
│   ├── services/
│   │   ├── gis_service.py                   (NEW, Phase 1)
│   │   ├── session_service.py               (NEW, Phase 1B)
│   │   └── analytics_service.py             (existing, expand)
│   ├── middleware/
│   │   ├── redis_session.py                 (NEW, Phase 1B)
│   │   ├── session_sync.py                  (NEW, Phase 1B)
│   │   └── timing.py                        (NEW, monitoring)
│   └── cache/
│       ├── callback_cache.py                (NEW, Phase 1B)
│       └── data_cache.py                    (NEW, Phase 1B)
│
├── tests/
│   ├── test_gis_callbacks.py                (NEW, Phase 1)
│   ├── test_gis_performance.py              (NEW, Phase 1)
│   └── test_concurrent_load.py              (NEW, Phase 3)
│
└── docs/
    ├── GIS_PILOT_PERFORMANCE_BASELINE.md    (NEW, Phase 1)
    ├── DASH_OPERATIONS_RUNBOOK.md           (NEW, Phase 2)
    └── DASH_MIGRATION_GUIDE.md              (NEW, Phase 2)
```

---

## Key Takeaways

### The Problem
Streamlit reruns entire script (5-15s) on every user interaction, limiting to ~64 charts safely.

### The Solution
Hybrid architecture: Keep Streamlit for forms/exports, migrate dashboards to Dash (callback-based, <500ms interactions).

### The Result
- 30x faster interactions (10s → 0.3s)
- 50+ charts (vs 64 currently)
- Better UX, scalable architecture
- Same data backend (DuckDB + Redis)

### The Effort
137-160 hours over 8 weeks (1-2 full-time developers)

### The Timeline
- Week 1-3: GIS pilot (40-45h) → <500ms latency target
- Week 4-6: Core views (52-60h) → 5 views total, 25 charts
- Week 7-8: Optimization (20-25h) → Load test, A/B test, hardening
- Go/no-go gates at phase boundaries

### Next Steps
1. Share plan with team
2. Assign resources
3. Create Jira epic
4. Start Phase 1 Week 1

---

## Contact & Questions

**Questions about the plan?**
→ Review relevant section in **MIGRATION_PLAN.md**

**Questions about implementation?**
→ Check **PHASE1_GIS_PILOT_TEMPLATE.md** or **DASH_ARCHITECTURE.md**

**Need a quick answer?**
→ Use **DASH_QUICK_REFERENCE.md** or search docs

**Ready to start?**
→ Begin with Week 1 checklist in **PHASE1_GIS_PILOT_TEMPLATE.md**

---

**Plan Created:** 2026-06-10  
**Status:** Ready for Review & Execution  
**Next Review:** After Phase 1 Completion (Week 3)

