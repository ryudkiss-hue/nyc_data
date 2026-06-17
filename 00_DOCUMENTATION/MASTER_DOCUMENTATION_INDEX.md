# MASTER DOCUMENTATION INDEX & SOURCE OF TRUTH
## NYC DOT SIM Dashboard — Extended KPI & Chart Registry

**AUTHORITATIVE SOURCE:** `EXPANDED_KPI_CHART_REGISTRY.md`  
**Version:** 2.1  
**Effective Date:** 2026-06-17  
**Scope:** Complete specification for Phase 3 (Visualization) and beyond  
**Status:** ✅ ACTIVE - Supersedes all prior visualization & KPI mapping documents

---

## DOCUMENT AUTHORITY & HIERARCHY

### 1. AUTHORITATIVE REFERENCES (Source of Truth)
These documents define the complete system architecture and are binding:

| Document | Location | Purpose | Authority |
|----------|----------|---------|-----------|
| **EXPANDED_KPI_CHART_REGISTRY.md** | `C:\Users\ryudk\Desktop\nyc_data\` | Complete Plotly schema, KPI mappings, Dash patterns, theme configs | **PRIMARY** |
| **CLAUDE.md** | `C:\Users\ryudk\Desktop\nyc_data\` | Project mission, glossary, safety policies, analytical reasoning | **BINDING** |
| **plot-schema.json** | `C:\Users\ryudk\Desktop\nyc_data\` | Plotly 2.0 spec (98,670 lines) - raw schema source | **REFERENCE** |

### 2. SUPERSEDED DOCUMENTS (Legacy - Do Not Use)
These documents are now obsolete and contradicted by EXPANDED_KPI_CHART_REGISTRY.md:

| Document | Reason Superseded | Replacement Sections |
|----------|------------------|----------------------|
| `docs/KPI_METRICS_REFERENCE.md` | Covered by Registry Ch. 3-4 | KPI-to-Chart Mapping Matrix |
| `docs/PHASE1_KPI_MAPPINGS.md` | Covered by Registry Ch. 3 | All 51 KPI definitions |
| `UNIFIED_KPI_REGISTRY_MASTER_PLAN.md` | Covered by Registry Intro | Phase 3 deliverables |
| `app/components/kpi_cards.py` | Config examples in Registry Appendix B | Component templates |
| `app/visualization_engine/kpi_cards.py` | Replaced by Registry templates | Mantine integration |

### 3. SUPPORTING DOCUMENTS (Reference - Use Alongside Registry)
These remain valid for context but derive from the Registry:

| Document | Relationship | Usage |
|----------|-------------|-------|
| `SOCRATA_DATASETS_CONSOLIDATED.md` | Data sources for KPIs | Understand dataset structure |
| `app/dash_layouts.py` | Implementation detail | Code template structure |
| `tests/` | Validation artifacts | Testing guidance |

---

## HOW THIS DOCUMENT WORKS

### Structure & Content
The EXPANDED_KPI_CHART_REGISTRY.md is organized as follows:

**Chapters 1-4: Foundational Specifications**
- Ch. 1: Plotly trace types (45 types, all 98,670 schema lines analyzed)
- Ch. 2: KPI-to-chart mapping (51 KPIs × optimal + alternative charts)
- Ch. 3: Chart configurations (11 primary types with JSON/Python templates)
- Ch. 4: Dash component patterns (callback examples, state management)

**Chapters 5-6: Theme & UX**
- Ch. 5: NYC DOT Mantine theme (colors, responsive, accessibility)
- Ch. 6: Animation specs (38 easing functions, frame-based keyframes)

**Chapters 7-9: Implementation Details**
- Ch. 7: Interaction patterns (click, hover, selection, zoom)
- Ch. 8: Performance & accessibility (WebGL, caching, ARIA)
- Ch. 9: Appendices (50+ code examples, schema extracts)

---

## WORKFLOW: HOW TO USE THIS REGISTRY

### For Phase 3 Implementation (Visualization)

1. **Start with the KPI-to-Chart Mapping Matrix** (Chapter 3)
   - Find your KPI ID (e.g., `PRM-001`)
   - Note the primary chart type and alternatives
   - Check data shape requirements

2. **Look up chart configuration** (Chapter 4)
   - Find your chart type (e.g., "Bar Chart")
   - Copy the JSON/Python template
   - Customize colors using NYC DOT palette

3. **Implement as Dash component** (Chapter 5 + Appendix B)
   - Use KPICard template for scalar KPIs
   - Use callback patterns for interactivity
   - Integrate Mantine theming

4. **Add animations & transitions** (Chapter 6)
   - Choose easing function based on KPI volatility
   - Set transition duration (300-500ms)
   - Test on mobile/tablet/desktop

5. **Verify accessibility & performance** (Chapter 8)
   - Add ARIA labels from template
   - Use WebGL for large datasets
   - Test keyboard navigation

### For Code Review & Maintenance

**When updating visualization code:**
- Check Registry first for the canonical pattern
- Ensure consistency with color scheme (Chapter 5)
- Validate callback patterns against examples (Chapter 7)

**When adding new KPIs:**
1. Add row to Registry Chapter 3 mapping matrix
2. Create config from appropriate template (Chapter 4)
3. Wire callbacks using Registry patterns (Chapter 7)
4. Update this index with new KPI count

**When refactoring components:**
- Use Appendix B templates as baseline
- Do not deviate from NYC DOT theme colors
- Test animations match Registry easing specs

---

## SPECIFIC SECTION MAPPINGS

### If You Need To... → See Chapter/Appendix

| Task | Location | Section |
|------|----------|---------|
| Understand all 45 Plotly trace types | Chapter 2 | Plotly Trace Type Catalog |
| Map a KPI to optimal chart(s) | Chapter 3 | KPI-to-Chart Mapping Matrix |
| Configure a gauge chart | Chapter 4 | Gauge Chart (Primary) |
| Create a trend line with forecast | Chapter 4 + Appendix A | Line Chart + Complete JSON |
| Build a heatmap for 2D data | Chapter 4 | Heatmap (2D Matrix) |
| Implement drill-down interaction | Chapter 7 + Appendix B | Callback Pattern: Drill-Down |
| Apply NYC DOT colors correctly | Chapter 5 | NYC DOT Color Scheme |
| Make dashboard responsive | Chapter 5 | Responsive Design |
| Add keyboard navigation | Chapter 8 | Accessibility |
| Optimize for 100K+ rows | Chapter 8 | Performance Best Practices |
| Create KPI card component | Appendix B | KPI Card Component with Mantine |
| Write Dash callbacks | Appendix B | Callback Patterns (3 examples) |
| Use Plotly easing functions | Chapter 6 | Animation & Transitions |
| Handle hover tooltips | Chapter 7 + Appendix B | Hover Handler Pattern |

---

## IMPLEMENTATION CHECKLIST FOR PHASE 3

Use the Registry to complete Phase 3 deliverables:

### Week 1-2: Chart Configuration
- [ ] Extract all 45 Plotly trace types → Registry Chapter 2 ✓ (DONE)
- [ ] Create gauge templates for all 51 KPIs → Registry Chapter 4
- [ ] Build bar/heatmap/line templates → Registry Chapter 4
- [ ] Test all configs match Registry specs

### Week 3-4: Dash Integration
- [ ] Implement KPICard component → Appendix B template
- [ ] Build KPI dashboard grid → Appendix B example
- [ ] Wire callbacks for filtering → Appendix B callback
- [ ] Add drill-down modal → Appendix B drill-down pattern

### Week 5-6: Styling & Responsiveness
- [ ] Apply NYC DOT color palette → Chapter 5
- [ ] Implement responsive grid → Chapter 5 CSS
- [ ] Add Mantine theme integration → Chapter 5
- [ ] Test mobile/tablet/desktop

### Week 6: Animations & Accessibility
- [ ] Add Plotly transition configs → Chapter 6
- [ ] Implement ARIA labels → Chapter 8
- [ ] Add keyboard navigation → Chapter 8
- [ ] Test screen reader compatibility

### Week 7: Performance & Launch
- [ ] Optimize for large datasets → Chapter 8
- [ ] Implement caching → Chapter 8
- [ ] Load test all 51 KPIs → Chapter 8
- [ ] Deploy to production

---

## KEY DECISIONS & RATIONALES

### Why This Document Is Authoritative

1. **Completeness**: All 45 Plotly types × 51 KPIs × implementation patterns = single source
2. **Schema-Driven**: Built from raw `plot-schema.json` (98,670 lines), not assumptions
3. **Production-Ready**: Includes JSON/Python templates ready to copy-paste
4. **NYC DOT Specific**: Incorporates brand colors, Mantine theme, accessibility
5. **Maintainability**: Single doc = single point of update = no divergence

### Design Decisions

**Primary Chart Types (11):**
- Gauge (scalar KPIs) - single value display
- Trend line (time-series) - historical + forecast
- Bar (categories) - rankings, comparisons
- Heatmap (2D) - borough × metric matrices
- Box plot (distributions) - outlier detection
- Scatter (XY) - correlation analysis
- Waterfall (variance) - decomposition
- Funnel (pipeline) - stage progression
- Sankey (flow) - budget allocation
- Sunburst (hierarchy) - tree structure
- Choropleth (geographic) - borough-level metrics

*Rationale:* These 11 cover all 51 KPI use cases. Additional 34 types available as alternatives.

**Color Palette (3 primary):**
- Green (#2ecc71) - On target, success
- Yellow (#f39c12) - Caution, at risk
- Red (#e74c3c) - Alert, critical

*Rationale:* NYC DOT brand + accessibility (colorblind-friendly, high contrast)

**Animation Durations:**
- Gauge: 500ms cubic-in-out (deliberate, measured)
- Trend: 300ms quad-out (quick, responsive)
- Bar: 400ms elastic-out (playful, engaging)

*Rationale:* Match animation speed to KPI change velocity

---

## VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 2.1 | 2026-06-17 | Added Appendices A-D, extended examples, established as Source of Truth |
| 2.0 | 2026-06-17 | Initial comprehensive registry (all 51 KPIs, 45 chart types, Dash patterns) |
| 1.0 | 2026-06-10 | Baseline KPI mappings (PHASE1_KPI_MAPPINGS.md) |

---

## WHEN TO UPDATE THIS DOCUMENT

Update the Registry if any of these occur:

1. **New KPI added:** Add row to Chapter 3 mapping matrix
2. **Chart type changes:** Update Chapter 4 configuration
3. **Color scheme updates:** Revise Chapter 5 palette
4. **New animation patterns:** Add to Chapter 6
5. **Plotly version upgrade:** Re-extract from new plot-schema.json
6. **Mantine theme version:** Update Chapter 5 component examples

**Update frequency:** Quarterly (or as features added)  
**Reviewer:** NYC DOT Visualization Team Lead  
**Approval:** Must pass code review + user acceptance test

---

## INTEGRATION WITH OTHER SYSTEMS

### Database Layer
- KPI values fetched from MotherDuck (dives) → pass to Registry templates
- Data shapes must match "Required Data" in Chapter 3

### API Layer
- Dash callbacks defined in Chapter 7 → wire to backend KPI service
- Response schema must match data shape in Chapter 3

### Frontend Layer
- Components built from Appendix B templates → deploy to Dash app
- CSS from Chapter 5 → inject to Mantine theme
- Callbacks from Appendix B → register in `app/callbacks/`

### Testing Layer
- Test specs from Chapter 8 → pytest fixtures
- Performance targets: <1s per chart, <2s dashboard load
- Accessibility: WCAG 2.1 AA (automated + manual)

---

## CONTACT & ESCALATION

**For questions about:**
- Chart configuration → See Chapter 4, verify against plot-schema.json
- KPI mappings → See Chapter 3, cross-reference PHASE1_KPI_MAPPINGS.md
- Dash implementation → See Appendix B, run examples locally
- NYC DOT theme → See Chapter 5, consult brand guidelines
- Plotly schema details → See Chapter 2, consult plot-schema.json directly
- Performance issues → See Chapter 8, profile with React DevTools

**Escalation Path:**
1. Check Registry Chapter relevant to issue
2. Review Appendix code examples
3. Test against provided JSON configs
4. If still unclear, consult Plotly docs (https://plotly.com/python/)

---

## HOW THIS SUPERSEDES PRIOR DOCUMENTS

### Before (Fragmented)
```
KPI_METRICS_REFERENCE.md
PHASE1_KPI_MAPPINGS.md
UNIFIED_KPI_REGISTRY_MASTER_PLAN.md
kpi_cards.py (component code)
visualization_engine/ (scattered patterns)
```

**Problems:**
- Chart recommendations scattered across 5 files
- Dash patterns in code, not documented
- Theme colors hardcoded, not centralized
- Animation specs missing
- No single source of truth

### Now (Unified - EXPANDED_KPI_CHART_REGISTRY.md)
```
EXPANDED_KPI_CHART_REGISTRY.md
├── All 51 KPI definitions
├── 45 chart type specs
├── 11 primary + alternatives per KPI
├── 50+ code examples
├── Complete Mantine theme
├── Animation & interaction specs
├── Performance & accessibility guidelines
└── Appendices A-D with production code
```

**Benefits:**
- Single document = single truth
- JSON/Python ready to copy
- No ambiguity on color/animation/component patterns
- Derived from actual Plotly schema (not assumptions)
- NYC DOT branding built-in
- Maintained in version control

---

## QUICK START: IMPLEMENTING A NEW KPI

**Scenario:** Add new KPI `LAB-001: Lab Inspection Rate`

**Step 1:** Add to Registry Chapter 3
```markdown
| LAB-001 | lab_inspection_rate | Gauge | Scalar | Target: >90% |
```

**Step 2:** Reference Chapter 4 Gauge template
```python
gauge_config = {
    "type": "indicator",
    "value": 92,  # Your value
    "target": 90,
    "unit": "%",
    "gauge": {...}  # Copy from Chapter 4
}
```

**Step 3:** Build component from Appendix B
```python
kpi_card = KPICard(
    id="kpi-lab-001",
    title="Lab Inspection Rate",
    kpi_value=92,
    unit="%",
    target=90,
    status="on-target"
)
```

**Step 4:** Add callback from Appendix B
```python
@callback(Output("kpi-lab-001", "figure"), Input("refresh-interval", "n_intervals"))
def update_lab_kpi(n):
    # Fetch value, return updated figure
```

**Step 5:** Wire to dashboard from Ch. 5 grid example
```python
dashboard = create_kpi_dashboard(kpi_data + [lab_kpi_config])
```

**Done.** Your KPI is live, themed, animated, and accessible.

---

## APPENDIX: FILE MANIFEST

All files referenced in this Registry:

```
C:\Users\ryudk\Desktop\nyc_data\
├── EXPANDED_KPI_CHART_REGISTRY.md ..................... [THIS FILE] Source of Truth
├── plot-schema.json .................................... Raw Plotly 2.0 spec (98.6 KB)
├── CLAUDE.md ............................................. Project mission & policies
├── SOCRATA_DATASETS_CONSOLIDATED.md ................... Data source registry
├── docs/
│   ├── KPI_METRICS_REFERENCE.md ....................... [SUPERSEDED]
│   ├── PHASE1_KPI_MAPPINGS.md ......................... [SUPERSEDED]
│   └── KPI_MAPPINGS_37_DATASETS.md
├── app/
│   ├── dash_app.py ...................................... Main Dash application
│   ├── dash_layouts.py .................................. Layout definitions
│   ├── callbacks/ ........................................ Callback handlers
│   ├── components/
│   │   └── kpi_cards.py ................................ [REFERENCE for code structure]
│   └── assets/ ........................................... CSS, themes
├── src/socrata_toolkit/
│   ├── abstraction_layers/
│   │   └── kpi_engine.py ................................ KPI computation
│   ├── visualization_engine/ ............................ [REFERENCE]
│   └── motherduck/ ....................................... Data orchestration
└── tests/
    ├── test_kpi_*.py ..................................... Validation tests
    └── integration/ ....................................... E2E tests
```

---

**DOCUMENT AUTHORITY:** ✅ ACTIVE & BINDING  
**LAST UPDATED:** 2026-06-17  
**NEXT REVIEW:** 2026-07-01 (or upon new feature request)  
**OWNER:** NYC DOT Visualization Team  
**STATUS:** Ready for Phase 3 Implementation

---

## EXECUTIVE SUMMARY FOR LEADERSHIP

**What is this?**
A comprehensive, single-source-of-truth guide for implementing all 51 KPI visualizations in the NYC DOT Dashboard using Plotly and Dash.

**Why does it matter?**
- Eliminates ambiguity in chart selection, configuration, and styling
- Provides production-ready JSON and Python code
- Ensures consistency across all visualizations
- Reduces implementation time from weeks to days

**What's included?**
- 51 KPI definitions with optimal chart types
- 45 Plotly chart types analyzed and catalogued
- 11 primary chart templates + alternatives
- 50+ code examples (JSON, Python, callbacks, CSS)
- Complete NYC DOT theme (colors, fonts, responsive, accessible)
- Animation specs, interaction patterns, performance guidelines

**How to use it?**
- Find your KPI in Chapter 3
- Copy the chart template from Chapter 4
- Build component using Appendix B example
- Deploy and watch users love your visualizations

**Timeline to value:**
- Weeks 1-2: Chart configuration from templates
- Weeks 3-4: Dash integration using callback patterns
- Weeks 5-6: Styling, responsiveness, animations
- Week 7: Testing, optimization, deployment
- **Total: 7 weeks to production with all 51 KPIs live**

