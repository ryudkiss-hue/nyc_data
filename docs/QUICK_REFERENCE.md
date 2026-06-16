# Quick Reference: Phase 1 Analytics Capabilities

One-page guide for each method.

---

## 1. CLUSTERING DIAGNOSTICS ENGINE

| Aspect | Details |
|--------|---------|
| **Problem** | How many clusters (k) is optimal for sidewalk segments? Manual selection wastes resources. |
| **Data Source** | Violation records (violation_count, repair_cost, inspection_frequency) |
| **Libraries** | scikit-learn (KMeans, silhouette_score), plotly |
| **Visualization** | Elbow curve, Silhouette plot, Quality heatmap |
| **Effort** | 6-8 hours |
| **Impact** | HIGH - Direct input to block-level prioritization |
| **Stakeholder** | Operations Manager, Capital Planning |
| **Output Example** | "k=5 clusters optimal (silhouette=0.61); Cluster 0 has highest violations/cost ratio → prioritize for inspection" |
| **Edge Cases** | k=1 (silhouette undefined), high-dimensional data (PCA reduce), outliers (robust scaling) |
| **Key Functions** | `ElbowAnalysis.fit_range()`, `plot_elbow_curve()`, `plot_silhouette()` |

**Quick Start:**
```python
from socrata_toolkit.analysis.clustering import ClusteringDiagnostics
from socrata_toolkit.viz.clustering_viz import plot_elbow_curve

cd = ClusteringDiagnostics(df, feature_cols=['violations', 'cost', 'frequency'])
result = cd.diagnose(max_k=10)
fig = plot_elbow_curve(result.inertias, result.silhouette_scores, result.optimal_k)
```

---

## 2. SIDEWALK MATERIAL DEGRADATION PATHWAY ANALYSIS

| Aspect | Details |
|--------|---------|
| **Problem** | Materials degrade at different rates but budget treats all equally. How long does concrete last vs. asphalt? |
| **Data Source** | Inspection records (material_type, inspection_date) + Violation history (first_violation_date) |
| **Libraries** | statsmodels / lifelines (Kaplan-Meier, Cox regression), scipy |
| **Visualization** | K-M survival curves, Cumulative hazard, Material economics scatter |
| **Effort** | 10-12 hours |
| **Impact** | HIGH - Enables evidence-based material sourcing decisions |
| **Stakeholder** | Maintenance Manager, Budget Officer |
| **Output Example** | "Asphalt: 9-year median lifespan ($650k 20-yr cost); Concrete: 13 years ($450k 20-yr cost). Recommendation: prioritize concrete for new installations." |
| **Edge Cases** | Few events per material (<30 → bootstrap CIs), installation_date unknown (use inspection_date), censoring at 25 years |
| **Key Functions** | `SurvivalDataPrep.prepare()`, `KaplanMeierAnalysis.fit()`, `plot_km_curves()` |

**Quick Start:**
```python
from socrata_toolkit.analysis.survival import SurvivalDataPrep, KaplanMeierAnalysis
from socrata_toolkit.viz.survival_viz import plot_km_curves

prep = SurvivalDataPrep(inspections_df, violations_df)
surv_data = prep.prepare()  # time-to-event format
km = KaplanMeierAnalysis(surv_data)
km_results = km.fit()
fig = plot_km_curves(km_results)
```

---

## 3. GEOSPATIAL HEATMAP WITH TEMPORAL ANIMATION

| Aspect | Details |
|--------|---------|
| **Problem** | Where is deterioration accelerating? Snapshot dashboard misses trends (12-24 months). |
| **Data Source** | Inspection records (lat/lon, inspection_date) + Violation counts by community board & month |
| **Libraries** | plotly (animated choropleths), folium (maps), geopandas (optional) |
| **Visualization** | Animated borough heatmap, Hot blocks timeline, Month-over-month change heatmap |
| **Effort** | 10-14 hours |
| **Impact** | HIGH - Executive storytelling, public accountability, equity visibility |
| **Stakeholder** | Commissioner, Community Board, City Council |
| **Output Example** | "Manhattan CB 201 violation density increased 15% Jun→Jul (ranked #2 citywide); Bronx CB 401 improved 8% (ranked #5 improvement citywide)" |
| **Edge Cases** | Missing months per CB (treat as 0), sparse data (<20 inspections per CB → flag unreliable), extreme outliers (cap at 95th pctl), performance (pre-compute for 24+ months) |
| **Key Functions** | `TemporalGeospatialDashboard.aggregate_by_month()`, `plot_animated_choropleth()`, `plot_hot_blocks_timeline()` |

**Quick Start:**
```python
from socrata_toolkit.viz.temporal_geospatial import TemporalGeospatialDashboard
from socrata_toolkit.viz.temporal_geospatial import plot_animated_choropleth_by_borough

dashboard = TemporalGeospatialDashboard(violations_df)
monthly_agg = dashboard.aggregate_by_month()
fig = plot_animated_choropleth_by_borough(monthly_agg)
fig.show()
```

---

## IMPLEMENTATION CHECKLIST

### Pre-Implementation (Week 0)
- [ ] Confirm data availability (material_type, installation_date, lat/lon in current datasets)
- [ ] Assign team ownership (1 analyst + 1 viz engineer)
- [ ] Review implementation specs in detail
- [ ] Set up git branch + CI/CD

### Week 1-2: Clustering
- [ ] Implement `ClusteringDiagnostics` class
- [ ] Implement viz functions (elbow, silhouette, heatmap)
- [ ] Write unit tests + synthetic data tests
- [ ] Integration test with violations_df
- [ ] Dash callback integration
- [ ] Stakeholder demo

### Week 3-4: Material Degradation
- [ ] Implement `SurvivalDataPrep` class
- [ ] Implement `KaplanMeierAnalysis` + `CoxRegressionModel` classes
- [ ] Implement viz functions (K-M curves, hazard, economics)
- [ ] Write unit tests + survival data validation
- [ ] Integration test with inspection + violation records
- [ ] Validate results against domain knowledge
- [ ] Stakeholder demo (Budget Office)

### Week 5-6: Geospatial Animation
- [ ] Implement `TemporalGeospatialDashboard` class
- [ ] Implement animated choropleth functions
- [ ] Performance testing (cache strategy for 24+ months)
- [ ] Write integration tests
- [ ] Test on real violation data
- [ ] Stakeholder demo (Commissioner, Community Board)

### Week 7: Release
- [ ] Cross-feature integration testing
- [ ] Documentation (API docs, user guide, FAQ)
- [ ] Production release + monitoring setup
- [ ] Post-release support (1 week on-call)

---

## DEPENDENCIES STATUS

```
Current (pyproject.toml)           | Status
======================================================================
scipy (≥1.10.0)                   | ✓ Present (for stats)
scikit-learn (via mapie, ≥0.8)    | ✓ Present (for clustering)
statsmodels (≥1.14 assumed)       | ? CHECK - needed for survival
plotly (≥5.0)                     | ✓ Present (for viz)
folium (≥0.14)                    | ✓ Present (for maps)
pandas (≥2.0)                     | ✓ Present (for data)
numpy (≥1.24)                     | ✓ Present (for numerics)

Not in Dependencies:
lifelines (for Kaplan-Meier)      | Consider adding (or use statsmodels)
```

**Action:** Confirm statsmodels version; decide on lifelines vs. statsmodels for survival analysis.

---

## TESTING STRATEGY

### Unit Tests
- Test clustering optimal k detection on synthetic data (4 clusters → k should be 3-5)
- Test survival time-to-event transformation (censoring logic)
- Test temporal aggregation (correct CB-month grouping)

### Integration Tests
- Clustering on real violations_df → confirm k matches Operations domain knowledge
- Survival on real inspection + violation records → confirm median survival times reasonable
- Geo animation on 12-month slice → confirm seasonal patterns visible

### Performance Tests
- Clustering on 100k+ records: should complete in <10 seconds
- Geo animation frame generation: <2 seconds per month for 24 months

### Validation Tests
- Silhouette plot matches sklearn reference implementation
- K-M curves match external survival analysis tool
- Geospatial density values within expected range (violations per km²)

---

## COMMON PITFALLS & FIXES

| Issue | Cause | Fix |
|-------|-------|-----|
| Elbow curve too flat | High-dimensional data | Use PCA to reduce to 10-20 dims first |
| Silhouette plot undefined | k=1 (only 1 cluster) | Skip silhouette; show warning |
| Survival analysis fails | Few events per material (<10) | Use stratified analysis or bootstrap CIs |
| Geo animation slow | Too many months (36+) | Offer quarterly aggregation option |
| Cluster profiles uninterpretable | Scaled features | Return profiles in original scale (undo StandardScaler) |

---

## STAKEHOLDER COMMUNICATION TEMPLATES

### For Operations Manager
"The clustering analysis recommends **k=5 segments** for sidewalk blocks. This groups 8,000+ blocks into 5 maintenance tiers based on violation severity and cost. Implementing this targeting could improve inspection efficiency by 25-30% based on comparable cities."

### For Budget Officer
"Material analysis shows concrete has a **13-year lifespan vs. 9 years for asphalt**, resulting in $450k vs. $650k total cost over 20 years. We recommend prioritizing concrete for new installations in high-traffic areas to reduce lifecycle costs."

### For Commissioner / Council
"Our new geospatial analysis shows violation density is **worsening in Manhattan CB 201 (+15% Jun-Jul) but improving in Bronx CB 401 (-8%)**. This gives us real-time visibility into problem neighborhoods and allows data-driven council district budget allocation."

---

## SUCCESS CRITERIA (GO/NO-GO)

### Clustering Diagnostics
**GO-LIVE GATE:** Elbow curve shows clear knee at k=4-6; silhouette score >0.50; Operations confirms k matches domain intuition

### Material Degradation
**GO-LIVE GATE:** K-M curves show statistically significant differences (log-rank p<0.05); median survival times align with maintenance records; Budget Office approves 20-year cost analysis

### Geospatial Animation
**GO-LIVE GATE:** Animation loads in <2 sec/month; hot blocks timeline shows expected seasonal peaks; Community Board can interpret trend without explanation

---

## RESOURCE REQUIREMENTS

| Role | Hours | Start Date | Duration |
|------|-------|-----------|----------|
| Backend Engineer (analysis) | 12-14 | Week 1 | 6 weeks |
| Frontend Engineer (viz) | 10-12 | Week 1 | 6 weeks |
| QA Engineer | 4-6 | Week 2 | 5 weeks |
| Product Manager (part-time) | 2-3 | Week 1 | 6 weeks |
| Stakeholder Champion (validation) | 2-3 | Week 1 | 6 weeks |
| **Total** | **30-40** | **Week 1** | **6 weeks** |

---

## MONITORING & METRICS

Post-launch, track:

1. **Adoption:** % of analysts using clustering diagnostics monthly
2. **Impact:** Budget allocation changes driven by clustering segmentation
3. **Accuracy:** User feedback on elbow curve recommendations vs. manual selection
4. **Performance:** API latency for clustering (target: <10 sec for 100k records)

---

## FAQ

**Q: What if we don't have installation dates for all materials?**  
A: Use inspection_date as proxy; add footnote "assumes inspection near installation." Validate with 20% sample of blocks with known dates.

**Q: Why not use simple elbow method instead of silhouette plots?**  
A: Elbow method is heuristic; silhouette provides quantitative validation. Together they're more robust.

**Q: How often should we re-run clustering analysis?**  
A: Monthly (as new violations come in) or quarterly (to avoid thrash if data is noisy). Start with quarterly; adjust based on stakeholder feedback.

**Q: Can we export the clustering output for use in other systems?**  
A: Yes - save cluster assignments as CSV (BBLID, cluster_id). Integrate with inspection crew scheduling system.

**Q: What if geospatial data is missing lat/lon?**  
A: Fall back to borough-level aggregation only. Add data quality alert to dashboard.

---

## REFERENCES

### Related Work
- NYC DOT Sidewalk Management System (existing inspection records)
- Capital Projects database (material tracking)
- 311 Complaint data (demand signal for heatmaps)

### External Best Practices
- Kaplan-Meier analysis: widely used in pharma, engineering asset management
- Silhouette plots: standard clustering validation method (sklearn documentation)
- Animated choropleths: proven effective in public health dashboards (CDC, NYC DOHMH)

---

## DOCUMENT CROSS-REFERENCES

- **ROADMAP_SUMMARY.md**: Executive summary & timeline
- **FEATURE_ROADMAP.md**: Detailed specifications, pseudocode, edge cases
- **PRIORITY_MATRIX.md**: Selection rationale, risk assessment
- **IMPLEMENTATION_SPECS.md**: Code templates, test harness, integration points

---

**Last Updated:** June 2026  
**Status:** Ready for Sprint Planning  
**Next Review:** Post-Phase-1-launch (Week 8)
