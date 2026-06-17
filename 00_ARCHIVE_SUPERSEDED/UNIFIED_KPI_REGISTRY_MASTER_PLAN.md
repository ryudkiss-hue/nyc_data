# Unified KPI Registry: Master Implementation Plan
## NYC DOT SIM Dashboard — Full Execution Plan

**Status:** Ready for parallel phase execution
**Total Effort:** 10 weeks (accelerated)
**Schema Integration:** plot-schema.json (Plotly animation/transition configs)
**Skills Activated:** visualization-builder, dashboard-specification, data-narrative-builder, analysis-documentation

---

## PARALLEL EXECUTION STRUCTURE

Each phase will be handled by an autonomous subagent team with clear deliverables and success criteria.

```
PHASE 1                PHASE 2                PHASE 3                PHASE 4                PHASE 5
(Foundation)  →        (Computation)  →       (Visualization)  →     (Dives)        →       (NLP+Integration)
Weeks 1-2             Weeks 3-4               Weeks 5-6              Week 7                 Weeks 8-10

KPIRegistry          Materialization        ChartFactory           MotherDuck            Dashboard
KPIDefinition        Orchestrator           ChartSelector          Dives                 Testing
YAML Loading         Forecasting            Plotly Templates       Parameterized         Deployment
Unit Tests           Anomalies              Dash Callbacks         Queries
```

---

## PHASE 1: FOUNDATION (Weeks 1-2)

**Subagent Team:** Foundation Architect

**Deliverables:**
1. ✅ Enhanced KPIDefinition dataclass with all metadata
2. ✅ KPIRegistry class that loads DATASET_REGISTRY.yaml
3. ✅ Consolidate all 51 KPI definitions into registry
4. ✅ Unit tests (100% coverage)
5. ✅ Documentation

**Key Outputs:**
- `src/socrata_toolkit/kpi/registry.py` (600 lines)
- `src/socrata_toolkit/kpi/models.py` (400 lines)
- `tests/test_kpi_registry.py` (300 lines)

**Success Criteria:**
- All 51 KPIs loaded from DATASET_REGISTRY.yaml
- No duplicate KPI definitions
- Type-safe dataclasses
- Tests >95% pass rate

---

## PHASE 2: COMPUTATION & MATERIALIZATION (Weeks 3-4)

**Subagent Team:** Analytics Engine Builders

**Deliverables:**
1. ✅ OperationalMetricsService enhancements
2. ✅ Time-series forecasting (linear + exponential + ARIMA)
3. ✅ Anomaly detection (z-score + isolation forest)
4. ✅ Materialization orchestrator
5. ✅ KPIResult contract with forecasts/trends/dimensions

**Key Outputs:**
- `src/socrata_toolkit/kpi/computation.py` (800 lines)
- `src/socrata_toolkit/kpi/forecasting.py` (400 lines)
- `src/socrata_toolkit/kpi/anomalies.py` (300 lines)
- `tests/test_kpi_computation.py` (600 lines)

**Success Criteria:**
- Forecasting accuracy >85% on validation set
- Anomaly detection catches >80% of true outliers
- Materialization < 5s for full refresh
- All KPIs compute without errors

---

## PHASE 3: VISUALIZATION (Weeks 5-6)

**Subagent Team:** Visualization Engineers

**Deliverables:**
1. ✅ ChartFactory with 11 chart types
2. ✅ ChartSelector for intelligent chart recommendation
3. ✅ Plotly schema integration (animation/transition config)
4. ✅ Responsive Dash callbacks
5. ✅ Mantine theme integration

**Key Outputs:**
- `src/socrata_toolkit/viz/chart_factory.py` (1200 lines)
- `src/socrata_toolkit/viz/chart_selector.py` (400 lines)
- `app/callbacks/drill_down.py` (600 lines)
- `tests/test_chart_factory.py` (800 lines)

**Chart Types Implemented:**
1. Gauge (with multi-level thresholds)
2. Trend Line (+ 3-month forecast + CI band)
3. Bar Comparison (by dimension)
4. Heatmap (2D matrix)
5. Box Plot (distribution + outliers)
6. Scatter (correlation)
7. Waterfall (variance decomposition)
8. Sunburst (hierarchical)
9. Candlestick (volatility)
10. Funnel (stage progression)
11. Sankey (flow/allocation)

**Success Criteria:**
- All 11 chart types render without errors
- Charts interactive (hover, click, zoom)
- Performance <1s load time per chart
- Tests >90% pass rate

---

## PHASE 4: MOTHERDUCK DIVES (Week 7)

**Subagent Team:** MotherDuck Dive Engineers

**Deliverables:**
1. ✅ 5 parameterized dive templates
2. ✅ Dive orchestrator (publishes to MotherDuck workspace)
3. ✅ Interactive query builder
4. ✅ Documentation

**Key Outputs:**
- `scripts/create_motherduck_dives.py` (500 lines)
- `src/socrata_toolkit/motherduck/dive_templates.sql` (5 templates)
- `docs/MOTHERDUCK_DIVE_GUIDE.md`

**Dives Published:**
1. Status Overview (current value + threshold + trend)
2. Historical Averages & MoM (12-month breakdown)
3. Dimension Breakdown (by borough/contractor/material)
4. Anomaly Detection (z-score + outliers)
5. Forecast Validation (actual vs predicted accuracy)

**Success Criteria:**
- All 5 dives execute without errors
- Dives accessible in MotherDuck workspace
- Queries parameterized with @kpi_id, @dimension filters
- Execution time <10s per dive

---

## PHASE 5: NLP & INTEGRATION (Weeks 8-10)

**Subagent Team:** Integration & Insights Team

**Deliverables:**
1. ✅ NLPInsightGenerator (auto-generates insights)
2. ✅ Dashboard integration (all 4 tabs, drill-downs)
3. ✅ End-to-end testing (all 51 KPIs)
4. ✅ Performance optimization
5. ✅ Production deployment

**Key Outputs:**
- `src/socrata_toolkit/kpi/insights.py` (500 lines)
- `app/components/kpi_drill_down.py` (1000 lines)
- `tests/test_integration.py` (1000 lines)
- `docs/DEPLOYMENT_GUIDE.md`

**Insights Generated:**
- Period-over-period change ("UP 12%")
- Dimensional outliers ("Manhattan leads...")
- Forecast summary ("Next month: 135 ± 8")
- Anomaly flags ("⚠️ 3σ deviation")

**Success Criteria:**
- Dashboard loads in <2s
- All 51 KPIs available for drill-down
- Insights accurate & actionable
- 100% uptime in staging
- Ready for production

---

## INTEGRATION POINTS: plot-schema.json

The Plotly schema (plot-schema.json) will be integrated into:

1. **ChartFactory.py**: Use schema to dynamically generate animation configs
   ```python
   # Example: Generate smooth transitions for gauge updates
   chart.layout.transition = plotly_schema['animation']['transition']
   chart.layout.transition.duration = 500  # ms
   chart.layout.transition.easing = 'cubic-in-out'
   ```

2. **Chart Selector**: Match KPI change velocity to easing functions
   ```python
   # Slow changes → 'linear', Fast changes → 'elastic'
   easing = selector.choose_easing(kpi_trend.volatility)
   ```

3. **Drill-Down Callbacks**: Smooth transitions between detail views
   ```python
   # Animates when user clicks to drill down
   chart.frames = [f1, f2, f3]  # Keyframes for animation
   chart.layout.sliders = [slider]  # Timeline control
   ```

---

## SKILLS INTEGRATION

| Skill | Phase | Purpose |
|-------|-------|---------|
| `visualization-builder` | Phase 3 | Chart type selection, layout optimization |
| `dashboard-specification` | Phase 5 | Dashboard layout & interaction design |
| `data-narrative-builder` | Phase 5 | Insight generation & storytelling |
| `analysis-documentation` | All | Comprehensive docs & guides |
| `time-series-analysis` | Phase 2 | Forecasting method selection |
| `semantic-model-builder` | Phase 1 | KPI taxonomy & domain modeling |

---

## SUCCESS METRICS

### Code Quality
- ✅ 100% type hints
- ✅ >90% test coverage
- ✅ Zero linting errors (ruff)
- ✅ Black formatting compliance

### Performance
- ✅ KPI refresh: <5s for all 51
- ✅ Chart render: <1s per chart
- ✅ Dashboard load: <2s initial
- ✅ Drill-down transition: <500ms

### Functionality
- ✅ All 51 KPIs available
- ✅ All 11 chart types working
- ✅ All 5 dives published
- ✅ All insights generating
- ✅ All drill-downs interactive

### Data Quality
- ✅ Zero missing KPIs
- ✅ Forecast accuracy >85%
- ✅ Anomaly detection sensitivity >80%
- ✅ Historical data consistency

---

## TIMELINE SUMMARY

| Week | Phase | Deliverables | Team |
|------|-------|--------------|------|
| 1-2 | Foundation | KPIRegistry + dataclasses + tests | Foundation Arch |
| 3-4 | Computation | Materialization + forecasting + anomalies | Analytics Engines |
| 5-6 | Visualization | ChartFactory + selector + callbacks | Viz Engineers |
| 7 | Dives | 5 MotherDuck dives + orchestrator | Dive Engineers |
| 8-10 | Integration | NLP + dashboard + testing + deploy | Integration Team |

---

## HANDOFF CHECKLIST

**For each phase:**
- [ ] Code written & linted
- [ ] Tests >90% passing
- [ ] Documentation complete
- [ ] Integration points verified
- [ ] Performance benchmarked
- [ ] Ready for next phase

**Final deployment:**
- [ ] All phases complete
- [ ] Integration tests >95% passing
- [ ] Staging environment stable
- [ ] Performance targets met
- [ ] Documentation finalized
- [ ] Ready for production

---

## NEXT STEPS

1. **Immediate:** Dispatch Phase 1 team (Foundation Architect)
2. **Wait 2 weeks:** Dispatch Phase 2 team (Analytics Engines)
3. **Wait 4 weeks:** Dispatch Phase 3 team (Viz Engineers)
4. **Wait 6 weeks:** Dispatch Phase 4 team (Dive Engineers)
5. **Wait 8 weeks:** Dispatch Phase 5 team (Integration Team)

**Parallel work:** All teams can work independently on their phases.

---

## CONTACT & QUESTIONS

For architecture questions → See KPI_REGISTRY_COMPREHENSIVE_DESIGN.md
For Plotly schema details → See plot-schema.json + Plotly documentation
For implementation questions → Check phase-specific docs

