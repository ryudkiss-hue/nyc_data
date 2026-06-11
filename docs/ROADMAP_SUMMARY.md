# NYC DOT Advanced Analytics Roadmap: Executive Summary

**Date:** June 2026  
**Status:** Recommended for Q3 2026 Implementation  
**Effort:** 26-34 FTE hours  
**Expected Timeline:** 6 weeks (with 1-week QA buffer)

---

## WHAT'S MISSING

Current toolkit gap analysis identified **6 high-value visualization/analysis capabilities** not in existing codebase:

1. Clustering quality metrics (elbow curves, silhouette plots)
2. Survival analysis for material degradation forecasting
3. Temporal geospatial heatmaps with animation
4. Conformal prediction intervals for uncertainty quantification
5. Bayesian construction permit risk scoring
6. Causal inference for accessibility equity analysis

---

## WHAT WE'RE PROPOSING

**Phase 1 (Q3 2026): 3 High-Impact / Medium-Effort Methods**

| # | Method | Impact | Effort | Use Case | Timeline |
|---|--------|--------|--------|----------|----------|
| **1** | **Clustering Diagnostics** | HIGH | 6-8h | Block-level resource allocation | Wks 1-2 |
| **2** | **Material Degradation Analysis** | HIGH | 10-12h | Maintenance budget optimization | Wks 3-4 |
| **3** | **Geospatial Heatmap Animation** | HIGH | 10-14h | Executive storytelling + equity | Wks 5-6 |

---

## HOW IT WORKS

### 1. Clustering Diagnostics Engine
**Problem:** No visibility into whether K-means divisions are meaningful or arbitrary.

**Solution:** Interactive elbow curve + silhouette plots to validate cluster count (k).

**Stakeholders:** Operations Manager (block prioritization), Capital Planning (funding allocation)

**Visualization:**
- Elbow curve (inertia vs. k) with knee detection
- Silhouette plot (per-sample quality by cluster)
- Quality metrics heatmap (Davies-Bouldin, Calinski-Harabasz)
- Cluster profiles table (mean feature values per cluster)

**Output:** "Recommendation: k=5 clusters is optimal with silhouette score 0.61"

**Data:** Existing violation + inspection records (no new data sources needed)

---

### 2. Sidewalk Material Degradation Pathway Analysis
**Problem:** Some materials (concrete vs. asphalt) fail faster but budget allocation treats all equally.

**Solution:** Kaplan-Meier survival curves quantify material-specific failure rates.

**Stakeholders:** Maintenance Manager (material sourcing), Budget Officer (multi-year planning)

**Visualization:**
- K-M survival curves by material (time to first violation)
- Cumulative hazard function (failure rate over time)
- Cost vs. lifespan scatter (material economics)
- Log-rank test results (statistical significance of differences)

**Output:** "Asphalt has 9-year median lifespan vs. 13 years for concrete; 20-year cost: $650k vs. $450k"

**Data:** Existing inspection records (material_type + dates) + violation history

---

### 3. Geospatial Heatmap with Temporal Animation
**Problem:** Dashboard shows current snapshot; missing trend visualization ("where is deterioration accelerating?").

**Solution:** Animated month-by-month heatmap of violation density by community board.

**Stakeholders:** Commissioner (strategy + PR), Community Board (neighborhood equity), City Council (public accountability)

**Visualization:**
- Animated borough choropleths (month-by-month slider)
- Hot blocks timeline (top-10 deteriorating blocks over 24 months)
- Month-over-month change heatmap (% change by CB-month)
- Trend detection per CB (worsening vs. improving)

**Output:** "Manhattan CB 201 violation density increased 15% Jun→Jul; ranks #2 citywide"

**Data:** Existing inspection records (lat/lon + date) + violation counts

---

## WHY THESE 3?

### Selection Criteria: Pareto Zone (High Impact / Medium Effort)

```
Effort vs. Impact Matrix:

                    EFFORT (hours)
              Low    | Medium | High
       ======================================
IMPACT HIGH  [1]    | [2,3]  | [4,5]
MEDIUM       -      | -      | [6]
======================================

Phase 1 Focus: [1], [2], [3] = 26-34 total hours, immediate ROI
Phase 2 Future: [4], [5], [6] = requires subject matter expertise
```

### Business Case
- **Clustering:** $0 incremental effort; eliminates manual block ranking → $50k+ budget reallocation savings
- **Material:** Informs material sourcing decisions → 10-20% maintenance cost savings (multi-year)
- **Geo Animation:** Executive + public-facing → stakeholder engagement + accountability (PR value)

### Technical Feasibility
- All libraries **already in pyproject.toml** (scipy, scikit-learn, statsmodels, plotly, folium)
- No new data sources required (works with existing inspection/violation records)
- Follows established patterns (existing analysis modules, Dash/Streamlit viz components)

---

## IMPLEMENTATION TIMELINE

### Week 1-2: Clustering Diagnostics
**Deliverable:** Elbow curve + silhouette plot UI component

**Dev Tasks:**
- Implement `ClusteringDiagnostics` class (sklearn K-means wrapper)
- Plotly viz functions (elbow, silhouette, quality heatmap)
- Unit tests + integration test with violations dataset
- Dash callback integration

**QA:** Validate k=4-5 on synthetic data; confirm matches domain expertise on real violations

---

### Week 3-4: Material Degradation Analysis
**Deliverable:** Kaplan-Meier curves for top 4 materials

**Dev Tasks:**
- Implement `SurvivalDataPrep` (time-to-event transformation)
- `KaplanMeierAnalysis` + Cox regression classes (statsmodels/lifelines)
- Survival viz functions (K-M curves, hazard, economics scatter)
- Unit tests + integration with inspections/violations

**QA:** Validate median survival times against field knowledge; log-rank tests show significant differences

---

### Week 5-6: Geospatial Heatmap Animation
**Deliverable:** Animated borough heatmap (12-month slider)

**Dev Tasks:**
- Temporal aggregation (violations by CB-month)
- Animated choropleth (Plotly or Folium)
- Hot blocks timeline (animated bar chart)
- Month-over-month heatmap (% change visualization)
- Performance optimization (caching, 24+ months)

**QA:** Load time <2s per month; hot blocks timeline shows seasonal patterns

---

### Week 7: Integration + Documentation
- Cross-feature testing (e.g., clustering output feeds into geo viz)
- Stakeholder demo / feedback
- Documentation (API docs, user guide, edge case handling)
- Release to production

---

## DEPENDENCIES

### New Libraries Needed
None! All required libraries already in `pyproject.toml`:
- scipy (≥1.10.0) ✓ for stats
- scikit-learn (via mapie) ✓ for K-means
- statsmodels (≥1.14) ✓ for survival analysis
- plotly (≥5.0) ✓ for visualizations
- folium (≥0.14) ✓ for maps
- pandas (≥2.0) ✓ for data manipulation
- numpy (≥1.24) ✓ for numerics

**Optional addition:** `lifelines` (for Kaplan-Meier), if not using statsmodels alternative. Cost: ~5 min to add to pyproject.toml.

---

## SUCCESS METRICS

### Clustering Diagnostics
- ✓ Silhouette plot matches sklearn reference implementation
- ✓ Elbow curve correctly identifies optimal k on test data
- ✓ Operations team confirms k=5 matches domain expertise
- ✓ Delivered as standalone Plotly figures + Dash integration

### Material Degradation
- ✓ K-M curves by material are statistically distinct (log-rank p<0.05)
- ✓ Median survival times align with field knowledge
- ✓ 20-year cost estimates approved by Budget Office
- ✓ Delivered with Cox regression hazard ratios + interpretation guide

### Geospatial Animation
- ✓ Hot blocks timeline shows expected seasonal patterns
- ✓ Month-over-month heatmap flags 5-10 "watch" CBs
- ✓ Animation load time <2 seconds per month
- ✓ Community board leadership can describe trend from map

---

## STAKEHOLDER VALUE

### Commissioner's Office
**Wants:** Public-facing narratives, equity optics, federal compliance  
**Gets:** Geospatial animation (where is problem worsening?), clustering (transparent allocation), material analysis (budget story)

### Operations Manager
**Wants:** Block-level targeting, resource optimization  
**Gets:** Clustering (which blocks first?), material analysis (maintain ROI), conformal prediction (SLA forecasting)

### Capital Planning
**Wants:** Multi-year budgets, material selection  
**Gets:** Material degradation analysis (20-year cost), construction risk scores (timeline confidence)

### Community Board
**Wants:** Visibility, fairness, progress tracking  
**Gets:** Geospatial animation (is our neighborhood getting worse?), clustering (fair allocation audit trail)

### City Council / Public
**Wants:** Accountability, equity  
**Gets:** Animated heatmaps (data-driven storytelling), equity analysis (disparity metrics)

---

## RISKS & MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Insufficient data for survival analysis | LOW | MED | Pre-validate installation_date availability |
| Elbow detection misses true optimal k | MED | LOW | Show top-3 candidates; let user override |
| Animation performance degrades (24+ months) | MED | MED | Pre-compute cached figures; quarterly aggregation option |
| Misinterpretation of causal results | LOW | HIGH | Add interpretation guide + disclaimer ("correlation ≠ causation") |
| Stakeholder skepticism of new methods | MED | MED | Pair with domain expert validation; pilot with 1 borough first |

---

## PHASE 2 (Q4 2026 & Beyond)

### If Phase 1 is successful:
- **Conformal Prediction** (8-10h): SLA enforcement, budget forecasting
- **Construction Risk Scoring** (14-18h): Permit delay quantification, contractor scorecards
- **Accessibility Gap Analysis** (12-16h): Policy-facing equity analysis, ADA compliance

### Technical Debt & Follow-ups
- Add UMAP/t-SNE for high-dimensional clustering visualization
- Extend material analysis to include weather/climate covariates
- Implement incremental updates (new data → fast re-analysis)
- Real-time streaming dashboard (if inspection data becomes event-driven)

---

## RECOMMENDED DECISION

**Approve Phase 1** for Q3 2026 implementation:
- **3 high-impact capabilities** (clustering, material degradation, geo animation)
- **26-34 FTE hours** (3-4 weeks for 1 analyst + 1 viz engineer)
- **Immediate ROI** (budget optimization, executive visibility, stakeholder engagement)
- **Technical readiness** (all dependencies available, no blockers)
- **Phased rollout** (weekly milestones, stakeholder feedback loops)

---

## NEXT STEPS

1. **Data Validation** (1-2 days)
   - Confirm material_type, inspection_date availability
   - Check installation_date coverage for survival analysis
   - Validate lat/lon for geospatial visualization

2. **Team Kickoff** (1 week)
   - Assign ownership (backend: analysis modules, frontend: viz components, QA: tests)
   - Review detailed implementation specs
   - Set sprint ceremonies (daily standup, weekly review)

3. **Stakeholder Alignment** (1-2 weeks)
   - Socialize designs with Operations, Planning, Council staff
   - Confirm success metrics
   - Identify pilot users for early feedback

4. **Development Starts** (Week 1 of 6-week implementation window)
   - Sprint 1: Clustering Diagnostics
   - Sprint 2: Material Degradation
   - Sprint 3: Geospatial Animation
   - Sprint 4: Integration + QA + Release

---

## SUPPORTING DOCUMENTATION

Three detailed documents provided:

1. **FEATURE_ROADMAP.md** (~1,500 lines)
   - Full problem statements, data sources, libraries, visualization specs
   - Edge case handling for each method
   - Detailed pseudocode for analysis steps
   - Input/output format specifications

2. **PRIORITY_MATRIX.md** (~800 lines)
   - Impact vs. Effort matrix visualization
   - Quadrant positioning & rationale
   - Risk mitigation table
   - Technical debt & follow-up items

3. **IMPLEMENTATION_SPECS.md** (~1,200 lines)
   - Module architecture & function signatures
   - Complete Python code skeletons
   - Test harness templates
   - Integration checkpoints

---

## APPENDIX: FEATURE DEPENDENCY GRAPH

```
Clustering Diagnostics
  → enables: Block-level prioritization, Geo viz filtering

Material Degradation
  → enables: Budget forecasting, Material sourcing decisions

Geospatial Animation
  → enables: Community board dashboards, Equity analysis

Conformal Prediction (Phase 2)
  → depends on: Time-series data quality
  → enables: SLA enforcement, Contingency budgeting

Construction Risk (Phase 2)
  → depends on: Permit historical data
  → enables: Permit approval workflows, Contractor scorecards

Accessibility Gap (Phase 3)
  → depends on: Demographic/socioeconomic data
  → enables: ADA compliance reporting, Equity prioritization
```

---

## CONTACT & QUESTIONS

**Project Lead:** [TBD - assign from team]  
**Data Owner:** [TBD - confirm data availability]  
**Stakeholder Champion:** [TBD - ops/planning leadership]

For detailed questions, refer to:
- FEATURE_ROADMAP.md (what & why)
- PRIORITY_MATRIX.md (when & where)
- IMPLEMENTATION_SPECS.md (how)

---

**RECOMMENDATION: Proceed with Phase 1 planning and team assignment.**
