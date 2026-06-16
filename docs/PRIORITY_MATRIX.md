# NYC DOT Analytics Roadmap: Priority Matrix & Selection Rationale

---

## PRIORITY MATRIX (Impact vs. Effort)

```
                                    EFFORT (Implementation Hours)
                        Low (4-8h)    | Medium (8-16h)  | High (16-24h)
                        =============|=================|===============
Impact      HIGH        |  [1]        |  [2] [3] [6]    |  [4] [5]
(Org Value) MEDIUM      |             |                 |
            LOW         |             |                 |
                        =============|=================|===============

[1] = Clustering Diagnostics (6-8h)
[2] = Conformal Prediction (8-10h)
[3] = Geospatial Heatmap Animation (10-14h)
[4] = Construction Risk Scoring (14-18h)
[5] = Accessibility Gap Analysis (12-16h)
[6] = Sidewalk Material Degradation (10-12h)
```

---

## DETAILED POSITIONING

### Pareto Zone (High Impact / Medium Effort) ← **RECOMMEND FOR Q3 2026**

#### 1. CLUSTERING DIAGNOSTICS ENGINE
- **Effort:** 6-8 hours
- **Impact:** HIGH
- **Why High Impact?**
  - Enables data-driven segmentation of sidewalk blocks for targeted maintenance
  - Eliminates arbitrary cluster decisions (k=3 vs k=5 guess-work)
  - Directly inputs to resource allocation ($M decisions)
  - Actionable within weeks of implementation
  
- **Why Low-Medium Effort?**
  - scikit-learn has all needed algorithms (KMeans, silhouette_score, etc.)
  - Visualization is straightforward Plotly (elbow curve is one line chart)
  - No complex data engineering; works on existing violation/inspection records
  
- **Direct Stakeholder:** Operations Manager (block prioritization), Capital Planning (funding allocation)
- **Implementation Timeline:** 1-2 weeks (Weeks 1-2)

---

#### 2. SIDEWALK MATERIAL DEGRADATION PATHWAY ANALYSIS
- **Effort:** 10-12 hours
- **Impact:** HIGH
- **Why High Impact?**
  - Quantifies material-specific failure rates (concrete vs. asphalt maintenance ROI)
  - Enables cost-benefit analysis for material selection in future repairs
  - Produces defensible economics for budget justification
  - Aligns with asset management best practices
  
- **Why Medium Effort?**
  - Survival analysis (Kaplan-Meier) is well-established, statsmodels has complete implementation
  - Data preparation is moderate (time-to-event data transformation)
  - Visualization (K-M curves) is standard practice in pharma/engineering
  - Cox regression adds sophistication but is optional
  
- **Direct Stakeholder:** Maintenance Manager (material sourcing), Budget Officer (multi-year planning)
- **Implementation Timeline:** 2-3 weeks (Weeks 3-4)

---

#### 3. GEOSPATIAL HEATMAP WITH TEMPORAL ANIMATION
- **Effort:** 10-14 hours
- **Impact:** HIGH
- **Why High Impact?**
  - Executive & community board visibility into spatial trends (where is problem worsening?)
  - Public-facing storytelling (City Council presentations, neighborhood engagement)
  - Enables equity analysis (disparities across boroughs/demographics)
  - Drives policy conversations (which neighborhoods get funding first?)
  
- **Why Medium-High Effort?**
  - Plotly animated choro pleths require moderate complexity (subplots + animation state)
  - Folium alternative is simpler but less polished
  - Temporal aggregation + trend detection adds algorithmic complexity
  - Performance caching needed for 24+ months of data
  
- **Direct Stakeholder:** Commissioner (strategy + PR), Community Board leadership, City Council staff
- **Implementation Timeline:** 2-3 weeks (Weeks 5-6)

---

### High-Impact / High-Effort (Consider for Phase 2)

#### 4. CONSTRUCTION PERMIT RISK SCORING (Bayesian Hierarchical Model)
- **Effort:** 14-18 hours
- **Impact:** MEDIUM-HIGH
- **Why Lower Priority for Phase 1?**
  - Requires deep Bayesian statistical expertise (not just data engineering)
  - Stakeholder validation needed: how to operationalize "risk score" into permit approvals?
  - Narrower audience (permit planners, not operations-wide)
  - Longer time-to-value (needs model validation + calibration)
  
- **Why Still Valuable?**
  - Quantifies permit delay uncertainty (credible intervals vs. point estimates)
  - Contractor-level risk scoring could influence vendor management
  - Seasonal effects + contractor learning curves are captured
  
- **Implementation Timeline:** Phase 2 (Weeks 8-10, after core features stabilize)

---

#### 5. ACCESSIBILITY GAP ANALYSIS (Propensity Score Matching)
- **Effort:** 12-16 hours
- **Impact:** MEDIUM
- **Why Lower Priority for Phase 1?**
  - Complex causal inference (propensity scores) requires economist/epidemiologist consultation
  - Requires demographic data (income, disability rates) not in current dataset
  - High risk of misinterpretation (correlation ≠ causation; matching can hide confounding)
  - Longer change management cycle for policy teams
  
- **Why Valuable Long-term?**
  - ADA compliance audits will eventually require equity analysis
  - Defensible against allegations of geographic/demographic bias
  - Could inform future ramp installation prioritization
  
- **Implementation Timeline:** Phase 2-3 (after accessibility stakeholder engagement)

---

## COMPARISON TABLE

| Method | Effort (h) | Impact | Audience | Timeline | Pre-Req Skills | Priority |
|--------|-----------|--------|----------|----------|----------------|----------|
| **Clustering** | 6-8 | HIGH | Ops Mgr | Wks 1-2 | ML basics | **P1** ⭐⭐⭐ |
| **Material Degradation** | 10-12 | HIGH | Budget Off. | Wks 3-4 | Stats (survival) | **P1** ⭐⭐⭐ |
| **Geo Animation** | 10-14 | HIGH | Exec/Council | Wks 5-6 | Data viz + geo | **P1** ⭐⭐⭐ |
| **Conformal Prediction** | 8-10 | HIGH | Analyst | Wks 7-8 | Causal ML | **P2** ⭐⭐ |
| **Construction Risk** | 14-18 | MEDIUM | Planning | Wks 9-11 | Bayesian stats | **P2** ⭐⭐ |
| **Accessibility Gap** | 12-16 | MEDIUM | Policy | TBD | Epi/causal | **P3** ⭐ |

---

## RECOMMENDATION SUMMARY

### Phase 1 (Q3 2026, Weeks 1-6): **Focus on Pareto Zone**
**Objective:** Deliver 3 high-impact features that drive immediate operational value

1. **Week 1-2:** Clustering Diagnostics
   - Smallest effort → quick win
   - Direct input to Q4 block prioritization
   - Build team confidence in new analysis pipeline

2. **Week 3-4:** Sidewalk Material Degradation
   - Medium effort, clear economics
   - Support FY2027 budget submissions
   - Establish survival analysis pattern (reusable for other assets)

3. **Week 5-6:** Geospatial Animation
   - Highest effort but highest visibility
   - Ready for mid-year council briefing
   - Foundation for future temporal analysis

**Expected ROI:** 
- Clustering: 1.0 (operational decisions)
- Material: 1.2 (budget savings)
- Geo: 1.1 (stakeholder engagement)
- **Average: 1.1 → strong business case**

---

### Phase 2 (Q4 2026, Weeks 8-11): **Expand to Complex Methods**
**Objective:** Add sophisticated capabilities for niche users (permit planners, statistical models)

4. **Conformal Prediction** (if SLA enforcement becomes priority)
5. **Construction Risk Scoring** (if permit system integration is greenlit)

---

### Phase 3 (2027): **Policy-Facing Analysis**
**Objective:** Address equity/fairness questions proactively

6. **Accessibility Gap Analysis** (post-stakeholder alignment on causal inference methodology)

---

## SELECTION RATIONALE BY STAKEHOLDER

### Commissioner's Office
**Wants:** Public-facing narratives, equity optics, federal compliance
**Get from Phase 1:**
- Geospatial animation (where is problem worsening?)
- Clustering (transparent resource allocation)
- Material analysis (ROI story for budget requests)

### Operations Manager
**Wants:** Block-level targeting, resource optimization, maintenance ROI
**Get from Phase 1:**
- Clustering (which blocks to inspect first?)
- Material analysis (maintain concrete vs. asphalt budget?)
- Conformal prediction (when will violations spike?)

### Capital Planning
**Wants:** Multi-year budgets, material selection guidance, contractor performance
**Get from Phase 1:**
- Material analysis (20-year cost per material type)
- Construction risk (permit delays → project timeline risk)

### Community Board
**Wants:** Visibility, fairness, progress tracking
**Get from Phase 1:**
- Geospatial animation (is our neighborhood getting worse?)
- Clustering (are resources allocated fairly?)

### Data Science Team
**Wants:** Reusable components, best-practice implementations, extensibility
**Get from Phase 1:**
- Modular analysis classes (ClusteringDiagnostics, KaplanMeierAnalysis)
- Viz components (elbow curves, K-M plots → other assets)
- Established patterns (time-to-event, ensemble forecasting)

---

## RISK MITIGATION

### Clustering Diagnostics
| Risk | Mitigation |
|------|-----------|
| K=1 or K=n silhouette undefined | Skip visualization, show warning + fallback to Davies-Bouldin |
| High-dimensional data (p>50) | Auto-reduce to 10 dims via PCA before K-means |
| Outliers dominate clustering | Use robust scaling (IQR) + detect/flag extreme points |

### Material Degradation
| Risk | Mitigation |
|------|-----------|
| Few events per material (<30) | Use bootstrap CI instead of Greenwood formula |
| Installation date unknown | Use inspection_date as proxy, document assumption |
| Proportional hazards violated | Fit stratified Cox model (material strata) |
| Competing risks (multiple violations) | Flag as limitation; full competing-risks model out of scope |

### Geospatial Animation
| Risk | Mitigation |
|------|-----------|
| Missing months for some CBs | Treat as 0 violations; note in legend "no data ≠ no violations" |
| Small CB populations (<20 inspections) | Flag as "unreliable estimate" in tooltip |
| Extreme outliers (1 CB >> others) | Cap color scale at 95th percentile |
| Performance (24+ months slow) | Pre-compute cached figures; offer quarterly aggregation |

---

## SUCCESS METRICS (Phase 1)

### Clustering Diagnostics
- [ ] Silhouette plot matches sklearn reference implementation (visual validation)
- [ ] Elbow curve correctly identifies k=4-5 on synthetic violation data
- [ ] Integration test with real violations dataset passes
- [ ] Operations team confirms k=5 matches domain expertise

### Material Degradation
- [ ] K-M curves by material are statistically distinct (log-rank p<0.05)
- [ ] Median survival times align with field knowledge (concrete ~13 yrs, asphalt ~9 yrs)
- [ ] Cox regression hazard ratios are intuitive (high-traffic areas → higher hazard)
- [ ] 20-year cost estimates approved by Budget Office

### Geospatial Animation
- [ ] Hot blocks timeline shows expected seasonal patterns (summer peaks)
- [ ] Month-over-month change heatmap flags 5-10 "watch" CBs
- [ ] Animation load time <2 seconds per month (performance gate)
- [ ] Community board stakeholders can verbally describe trend from map (usability)

---

## TECHNICAL DEBT & FOLLOW-UP

After Phase 1 delivery, plan these enhancements:

1. **Clustering:** Add UMAP/t-SNE 2D visualization for high-dimensional data
2. **Material:** Extend to include weather/climate covariates (freeze-thaw cycles)
3. **Geo:** Add competing-heatmaps (violations vs. repairs) side-by-side
4. **General:** Implement incremental updates (new data → fast re-analysis without full recompute)

---

## APPENDIX: FEATURE DEPENDENCY GRAPH

```
Clustering Diagnostics
  └─ Input: violations + inspections
  └─ Output: k_optimal, cluster_assignments
  └─ Downstream: (none yet)

Sidewalk Material Degradation
  └─ Input: inspections (material_type) + violations (dates)
  └─ Output: km_curves, material_economics
  └─ Downstream: budget forecasting, material selection logic

Geospatial Heatmap
  └─ Input: inspections (lat/lon + date) + violations
  └─ Output: monthly aggregates, hot_blocks, trend_per_cb
  └─ Downstream: community board dashboards, equity analysis

Conformal Prediction (Phase 2)
  └─ Input: violation timeseries + exogenous features
  └─ Output: prediction_intervals
  └─ Downstream: SLA enforcement, budget contingency planning

Construction Risk (Phase 2)
  └─ Input: permits + HIQA inspections + completion dates
  └─ Output: risk_scores_by_permit, contractor_risk_cards
  └─ Downstream: permit approval workflows, contractor scorecards

Accessibility Gap (Phase 3)
  └─ Input: ramp_locations + complaints + demographics
  └─ Output: gap_map, equity_metrics
  └─ Downstream: ADA compliance reporting, ramp prioritization
```

---

## CONCLUSION

**Recommended Phase 1 (Q3 2026):** Clustering Diagnostics + Material Degradation + Geospatial Animation

**Expected Business Outcomes:**
- Segment-level (block-by-block) prioritization for maintenance crews
- Evidence-based material sourcing decisions (20-year ROI)
- Public-facing storytelling (equity + accountability) for executive leadership
- Reusable analytical patterns for future asset management enhancements

**Total Development Effort:** 26-34 hours (3-4 weeks FTE for 1 analyst + 1 viz engineer)
**Estimated Timeline to Production:** 6 weeks (with 1 week buffer for QA/iteration)
