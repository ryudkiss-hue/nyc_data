# DOCUMENTATION MIGRATION GUIDE
## From Fragmented to Unified — How EXPANDED_METRIC_CHART_REGISTRY.md Supersedes Prior Docs

**Effective Date:** 2026-06-17  
**Action:** All team members must reference EXPANDED_METRIC_CHART_REGISTRY.md going forward  
**Old Documents:** Archive (keep for audit trail, do not reference for new work)

---

## WHAT WAS HERE BEFORE

### 1. docs/METRIC_METRICS_REFERENCE.md
**What it said:** 60+ statistical metrics (mean, median, std dev, quantiles, outliers, etc.)

**How it's superseded:**
- Registry Chapter 3 includes all Metric definitions with data requirements
- Appendix A includes complete JSON configs with all metrics built-in
- No need to reference old metrics doc; all calculations already in configs

**Migration steps:**
- ✅ If you need a metric formula: Registry Ch. 3 has all 51 Metric calculations
- ✅ If you need a metric visualization: Registry Ch. 4 has the chart for that metric
- 🚫 Do NOT consult METRIC_METRICS_REFERENCE.md for new implementations

---

### 2. docs/PHASE1_METRIC_MAPPINGS.md
**What it said:** 21 datasets, 51 Metric definitions, targets, SLA thresholds, data stories

**How it's superseded:**
- Registry Chapter 3 includes COMPLETE METRIC-to-Chart mapping for all 51 Metrics
- Each row shows: Metric ID | Name | Primary Chart | Alternatives | Data Shape | Configs
- Everything from PHASE1_METRIC_MAPPINGS is rolled into the matrix

**Migration steps:**
- ✅ If you need Metric definition: Registry Ch. 3, find your Metric ID (PRM-001, etc.)
- ✅ If you need optimal chart: Registry Ch. 3, same row shows primary + alternatives
- ✅ If you need data shape: Registry Ch. 3 specifies scalar/time-series/2D/hierarchical
- 🚫 Do NOT reference PHASE1_METRIC_MAPPINGS.md; use Registry instead

**Mapping Comparison:**

| Old Document (PHASE1_METRIC_MAPPINGS.md) | New (EXPANDED_METRIC_CHART_REGISTRY.md) |
|---------------------------------------|---------------------------------------|
| "Ramp Completion Rate" in Section 2.1 | Registry Ch. 3: `ADA-001` "ramp_borough_coverage" |
| Text description + target | Gauge chart config in Chapter 4 |
| Manual calculation methods | Appendix A: complete JSON template |
| No visualization guidance | Chapter 3: primary chart = Gauge, alternatives = Bar + Heatmap |

---

### 3. UNIFIED_METRIC_REGISTRY_MASTER_PLAN.md
**What it said:** Phase 1-5 implementation timeline, team assignments, success metrics

**How it's superseded:**
- Registry Chapters 1-9 ARE the Phase 3 (Visualization) spec
- All 11 chart types defined → ready to implement
- All 51 Metric configs ready → no more "to-be-determined"
- Appendices B-D contain Phase 5 (Integration) code patterns

**Migration steps:**
- ✅ For Phase 3 implementation: Use Registry Chapters 1-9 as complete spec
- ✅ For team assignments: Each subagent gets one Metric group (e.g., 10 Metrics) from Ch. 3
- ✅ For success criteria: See Ch. 8 performance targets (ready to test)
- 🚫 Do NOT consult UNIFIED_METRIC_REGISTRY_MASTER_PLAN.md; use Registry + this index

---

### 4. app/components/metric_cards.py
**What it said:** Python component code for Metric cards (partial, incomplete)

**How it's superseded:**
- Appendix B has COMPLETE MetricCard class with full docstrings
- Includes all Mantine theming (colors, responsive, accessibility)
- Includes all callback patterns (update, drill-down, hover)
- Production-ready code ready to copy

**Migration steps:**
- ✅ If updating Metric card component: Use Appendix B template, not metric_cards.py
- ✅ If adding new card styling: Reference Chapter 5 Mantine theme
- ✅ If implementing callbacks: Use Appendix B examples, not scattered in code
- 🚫 Do NOT modify metric_cards.py directly; reference Registry templates first

---

### 5. app/visualization_engine/metric_cards.py
**What it said:** Visualization engine patterns (scattered, incomplete, outdated)

**How it's superseded:**
- Chapter 4 has ALL 11 chart type configurations (bar, gauge, heatmap, etc.)
- Chapter 6 has animation specs (easing, duration, frame-based)
- Chapter 7 has interaction patterns (click, hover, selection, zoom)
- Chapter 5 has theme integration (Mantine, colors, responsive)

**Migration steps:**
- ✅ If implementing a chart type: Use Chapter 4 template (JSON + Python)
- ✅ If adding animations: Use Chapter 6 easing reference
- ✅ If implementing callbacks: Use Chapter 7 + Appendix B patterns
- 🚫 Do NOT reference visualization_engine/; use Registry Chapters 4-7

---

## DETAILED MAPPING: OLD → NEW

### For Every Old Document, Here's Where Its Content Lives Now

#### METRIC_METRICS_REFERENCE.md → Registry Chapters 3-4

| Old Section | New Location | Details |
|-------------|-------------|---------|
| Central Tendency (mean, median, mode) | Ch. 3: Metric definitions | All Metrics include statistical basis |
| Spread/Dispersion (std dev, variance) | Ch. 4: Chart configs | Variance shown in heatmaps, box plots |
| Distribution Shape (skewness, kurtosis) | Ch. 4: Box plot config | Boxmean option shows distribution |
| Outlier Detection (3-sigma, IQR, Z-score) | Ch. 4: Box plot + scatter | Jitter + outlier flagging |
| Quantiles/Percentiles (P5, P25, P50, P75) | Ch. 4: Box plot whiskers | All quantiles rendered visually |
| Color Coding/Risk Indicators | Ch. 5: NYC DOT colors | Green/Yellow/Red threshold mapping |

#### PHASE1_METRIC_MAPPINGS.md → Registry Chapter 3

| Old Section | New Location | Example Mapping |
|-------------|-------------|-----------------|
| 1. Permit Variants (13 Metrics) | Ch. 3: 13 Metric rows | PRM-001 to CLS-004 |
| 2. Pedestrian Infrastructure (14 Metrics) | Ch. 3: 14 Metric rows | PED-001 to ADA-003 |
| 3. Street Safety (12 Metrics) | Ch. 3: 12 Metric rows | PARK-001 to VZ-002 |
| 4. Budget & Vendor (7 Metrics) | Ch. 3: 7 Metric rows | CAP-001 to COORD-002 |
| 5. Reference & Compliance (5 Metrics) | Ch. 3: 5 Metric rows | GEO-001 to CMP-003 |
| **Total** | **Ch. 3 Matrix: 51 rows** | All Metrics with primary + alt charts |

#### metric_cards.py (Code) → Registry Appendix B

| Old Code | New Location | Example |
|----------|-------------|---------|
| MetricCard class definition | Appendix B: MetricCard class | Full implementation with docstrings |
| Mantine integration | Ch. 5 + Appendix B | Color tokens, responsive grid, fonts |
| Callback for updates | Appendix B: Update callback | animate_gauge_update() |
| Callback for drill-down | Appendix B: Drill-down callback | drill_down_on_metric_click() |
| CSS styling | Ch. 5: Mantine CSS | .metric-card, .metric-status-*, breakpoints |
| Hover templates | Ch. 4 + Appendix A | hovertemplate in Gauge/Bar configs |

---

## COMMON QUESTIONS DURING MIGRATION

### Q1: "I was using METRIC_METRICS_REFERENCE.md to understand metrics. Where do I go now?"
**A:** Registry Chapter 3 lists all 51 Metrics with their calculation basis. For any Metric:
1. Find your Metric ID in Ch. 3 matrix
2. See the primary chart type recommended
3. Go to Ch. 4 for that chart's config (includes metric calculation)
4. Appendix A has complete JSON with all metrics computed

### Q2: "I'm implementing a new chart. Should I follow metric_cards.py or the Registry?"
**A:** Always follow the Registry. metric_cards.py is legacy code. Here's why:
- Registry Ch. 4 has ALL chart type templates (bar, gauge, heatmap, etc.)
- Appendix B has production-ready component code
- metric_cards.py only covers gauges, incomplete

### Q3: "My manager asked about Metric definitions. Which document should I share?"
**A:** Share Registry Chapter 3 (METRIC-to-Chart Mapping Matrix). It's complete, organized by category, and shows chart recommendations. PHASE1_METRIC_MAPPINGS.md is outdated.

### Q4: "I need to change a chart color. Where's the theme?"
**A:** Registry Chapter 5 (NYC DOT Theme Integration). All colors are there:
- Status colors: Red/Yellow/Green with hex codes
- Borough colors: MN/BX/BK/QN/SI with palette
- Colorscales: Status (RdYlGn), Intensity (Viridis), Diverging (RdYlBu)
- Mantine theme config

### Q5: "The old plan said 51 Metrics would take 10 weeks. Can we go faster?"
**A:** Yes. Registry is production-ready. Timeline with Registry:
- **Week 1-2:** Implement 11 chart templates from Ch. 4 (parallel)
- **Week 3-4:** Build Metric cards using Appendix B (10 Metrics per dev)
- **Week 5-6:** Wire callbacks from Appendix B + Ch. 7 (parallel)
- **Week 7:** Theme, animations, testing
- **Total: 7 weeks to production** (3 weeks faster because no "determine" phase)

---

## STEP-BY-STEP MIGRATION CHECKLIST

If you were working with the old documents, here's how to transition:

### If You Were Using METRIC_METRICS_REFERENCE.md:
- [ ] Switch to Registry Chapter 3 for Metric definitions
- [ ] Use Chapter 4 for metric visualizations
- [ ] Update any internal wikis linking to old doc
- [ ] Archive old doc (do not delete—audit trail)

### If You Were Using PHASE1_METRIC_MAPPINGS.md:
- [ ] Switch to Registry Chapter 3 (METRIC-to-Chart Matrix)
- [ ] Update any Jira epics referencing old doc
- [ ] Note: Registry goes beyond mappings → includes full configs
- [ ] Archive old doc

### If You Were Editing app/components/metric_cards.py:
- [ ] Stop editing that file
- [ ] Use Registry Appendix B for new components
- [ ] Ensure all edits match Registry spec (colors, animations, callbacks)
- [ ] Plan refactor to use Registry templates as baseline

### If You Were Following UNIFIED_METRIC_REGISTRY_MASTER_PLAN.md:
- [ ] Note: Phase 3 spec is now complete in Registry (not to-be-determined)
- [ ] No more "estimate"; timelines are concrete
- [ ] Use Registry Chapters 1-9 for implementation, not plan
- [ ] Archive plan doc

---

## WHAT DOES EACH OLD DOCUMENT SAY? (For Reference Only)

### Quick Summaries (Don't Use These—Reference Registry Instead)

**METRIC_METRICS_REFERENCE.md:**
- 60+ metrics across 11 categories
- Formulas for mean, median, std dev, skewness, kurtosis, outliers, risk metrics
- Visualization techniques (box plot, violin, KDE, heatmap, Z-score)
- Interactive components (borough selector, metric highlighter, threshold toggles)
- Dashboard summary table with 16 columns
- Color coding for risk indicators
- **Status: SUPERSEDED** Use Registry Ch. 3-4 instead

**PHASE1_METRIC_MAPPINGS.md:**
- 51 Metrics across 5 categories (Permits, Infrastructure, Safety, Budget, Compliance)
- Definitions with target SLA thresholds
- Data stories for each Metric
- 21 datasets mapped to 51 Metrics
- **Status: SUPERSEDED** Use Registry Ch. 3 instead (includes charts too)

**UNIFIED_METRIC_REGISTRY_MASTER_PLAN.md:**
- 5-phase timeline (Foundation, Computation, Visualization, Dives, Integration)
- Team assignments (subagent teams)
- Success criteria and deliverables per phase
- Skill activation (visualization-builder, dashboard-specification, etc.)
- **Status: SUPERSEDED** Use Registry Ch. 1-9 for specs; Phase 3 deliverables are finalized

**metric_cards.py:**
- Python class for Metric card components
- Mantine integration (colors, sizing)
- Gauge chart rendering
- Status-based styling (on-target, at-risk, critical)
- **Status: SUPERSEDED** Use Registry Appendix B (complete, production-ready)

**visualization_engine/metric_cards.py:**
- Visualization patterns for Metric rendering
- Animation/transition definitions
- Callback patterns for interactivity
- Theme integration
- **Status: SUPERSEDED** Use Registry Ch. 4-7 for comprehensive patterns

---

## AUTHORITY STATEMENT

**Effective immediately (2026-06-17):**

✅ **DO** reference `EXPANDED_METRIC_CHART_REGISTRY.md` for all visualization work  
✅ **DO** use Registry Chapter 3 for Metric definitions  
✅ **DO** use Registry Chapter 4 for chart configurations  
✅ **DO** use Registry Appendix B for Dash component code  

🚫 **DO NOT** consult old documents for implementation guidance  
🚫 **DO NOT** use old templates for new components  
🚫 **DO NOT** deviate from Registry color scheme or animation specs  

**Audit Trail:** Old documents are kept in `docs/` for historical reference only. Any new code reviews will cite Registry sections, not old docs.

---

## QUICK REFERENCE: WHERE THINGS MOVED

```
OLD                                 NEW
──────────────────────────────────────────────────────────────
METRIC_METRICS_REFERENCE.md       →    Registry Ch. 3-4 (Metric defs + charts)
PHASE1_METRIC_MAPPINGS.md         →    Registry Ch. 3 (METRIC-to-chart matrix)
UNIFIED_METRIC_REGISTRY_*_PLAN    →    Registry Ch. 1-9 (complete spec)
metric_cards.py                   →    Registry Appendix B (MetricCard class)
visualization_engine/          →    Registry Ch. 4-7 (all patterns)

docs/METRIC_*.md                  →    ARCHIVE (keep for audit)
app/visualization_engine/      →    REFERENCE ONLY (legacy code)
UNIFIED_METRIC_REGISTRY_*_PLAN    →    ARCHIVE (keep for timeline history)
```

---

## WHAT TO DO WITH YOUR LOCAL BRANCHES

If you have in-progress work on visualization or Metric components:

1. **Stash your changes** (do not discard)
2. **Create new branch** from `main`
3. **Use Registry templates** as baseline instead of old code
4. **Port your changes** to new component structure (Appendix B)
5. **Test** against all Registry specs (Ch. 4-7)
6. **Submit PR** with Registry compliance checklist

**Example:**
```bash
git checkout main
git pull
git checkout -b feature/metric-cards-refactor

# Edit component to use Registry Appendix B template
# Add test to verify Ch. 5 Mantine colors
# Add animation per Ch. 6 easing specs
# Update callbacks to match Ch. 7 patterns

git add .
git commit -m "Refactor Metric cards to use EXPANDED_METRIC_CHART_REGISTRY templates"
git push -u origin feature/metric-cards-refactor
```

---

## FAQ: MIGRATION QUESTIONS

**Q: Can I still reference the old documents for context?**
A: Yes, but only for historical context. Cite Registry for any new work.

**Q: My code uses patterns from metric_cards.py. Do I need to refactor?**
A: Yes, during next code review. Use Registry Appendix B as refactor baseline.

**Q: What if the old doc contradicts the Registry?**
A: Registry wins. It's derived from actual Plotly schema (plot-schema.json), not opinion.

**Q: Is the Registry locked, or can I suggest changes?**
A: It can evolve. File issue → describe improvement → Registry maintainer updates.

**Q: How do I know if my implementation matches the Registry?**
A: Use the checklist in Chapter 8 (Performance & Accessibility) + run tests.

**Q: The old plan said we had more time. Does Registry change the timeline?**
A: No—Registry is FASTER. Ready-to-use templates = less guessing = 7 weeks not 10.

---

## CONTACT FOR QUESTIONS

- **Registry content questions:** See relevant Chapter + Appendix
- **Implementation help:** Use code examples from Appendix B
- **Theme/color questions:** See Chapter 5 + plot-schema.json reference
- **Animation/interaction questions:** See Chapter 6-7
- **Performance issues:** See Chapter 8 optimization guidelines

---

**Migration Status:** ✅ COMPLETE  
**Old Documents Status:** 📦 ARCHIVED (audit trail only)  
**Registry Status:** ✅ ACTIVE & AUTHORITATIVE  
**Effective Date:** 2026-06-17  
**Next Review:** 2026-07-01

