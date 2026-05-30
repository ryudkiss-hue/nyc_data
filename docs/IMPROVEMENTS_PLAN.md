# Manhattan Mission Control — 84 Optimization Initiatives

> Industry-disrupting upgrade program. Additive-only (protects CI + Render deploy).
> Targets: SPA (`mission_control_v2.html`), Electron shell, Python data/governance layer.
> Streamlit app frozen. A11y target: **WCAG 2.2 AAA where feasible**.
> Governance frameworks: **DAMA-DMBOK** (6 dimensions), **W3C PROV** lineage/provenance,
> **FAIR** (Findable/Accessible/Interoperable/Reusable), **PII safeguards**.

Evidence base: Nielsen Norman Group usability heuristics; WCAG 2.2 (W3C);
DAMA-DMBOK2 data-quality dimensions; Wilkinson et al. 2016 *Scientific Data*
"FAIR Guiding Principles"; W3C PROV-DM; Munzner *Visualization Analysis & Design*;
Few *Information Dashboard Design*; Google Web Vitals (LCP/INP/CLS).

Legend: ☐ todo · ☑ done · ◐ partial

---

## Wave 1 — Accessibility & UX Foundation (SPA)  [WCAG 2.2 AAA]
1. ☑ Semantic landmarks: `<header>`/`<nav>`/`<main>`/`<section>` with `role`/`aria-label`
2. ☑ ARIA tablist pattern on tab strip (`role=tablist/tab/tabpanel`, `aria-selected`, roving tabindex, arrow-key nav)
3. ☑ Modal focus-trap + focus restoration on close + `role=dialog`/`aria-modal`
4. ☑ `prefers-color-scheme` + `prefers-contrast` auto-detection on load
5. ☑ Error/status announcements routed through ARIA live region (not just results)
6. ☑ Skip-to-content link + visible focus rings audited to AAA contrast (≥7:1)
7. ☑ Explicit `<label for>` / `aria-label` on every form control
8. ☑ `aria-label` on all icon-only buttons; decorative icons `aria-hidden`
9. ☑ Respect reduced-motion in JS animation paths (not only CSS)
10. ◐ Accessible color palette audited to AAA contrast; document ratios

## Wave 2 — UX Polish & Interaction Design (SPA)
11. ☑ Command palette (Ctrl/Cmd+P) with fuzzy action search
12. ☑ Loading skeletons for profile / map / SOQL panels (not just search)
13. ☑ Toast notification center with history + severity levels
14. ☑ Robust error handling with retry + exponential backoff on Socrata fetches
15. ☑ Auto-save indicator ("saving… / saved ✓") for cart & workspaces
16. ☑ Empty-state redesign with primary CTA hierarchy per panel
17. ☑ Inline data-peek preview on result hover (first rows)
18. ☑ Bulk cart operations (tag, annotate, remove multiple)
19. ☑ Resize-safe tooltip/positioning engine
20. ☐ Onboarding product tour upgrade (spotlight + step state persistence)

## Wave 3 — Data Visualization (SPA)
21. ☑ Vendored charting lib (offline) — Trends tab (Observable Plot) + scatter plot + SVG sparklines
22. ☑ Histogram + KDE for numeric column distributions
23. ☑ Box-plot / five-number summary per numeric column
24. ☑ Correlation heatmap across numeric columns
25. ☑ Time-series viewer with range selector for date columns
26. ☑ Categorical top-N Pareto chart
27. ☑ Choropleth/heatmap layer option on the map
28. ☑ Color-blind-safe (Okabe-Ito) categorical palette across all charts
29. ☑ Chart→data-table a11y fallback (every chart has a tabular equivalent)
30. ☑ Sparkline column summaries in profile grid

## Wave 4 — Data Governance: FAIR Catalog (Python, NEW)
31. ☑ `fair/` package: FAIR-aligned metadata catalog model
32. ☑ Findable: persistent dataset IDs + rich indexed metadata
33. ☑ Accessible: standardized access protocol metadata (endpoint, auth, license)
34. ☑ Interoperable: schema.org / DCAT-style vocabulary export (JSON-LD)
35. ☑ Reusable: provenance + license + usage-rights metadata
36. ☑ FAIRness scoring rubric (0–100) per dataset with sub-scores
37. ☑ Catalog persistence (JSON) + loader
38. ☑ DCAT/JSON-LD export endpoint
39. ☑ Unit tests for FAIR catalog + scoring
40. ☑ CLI command to emit FAIR catalog for the registry

## Wave 5 — Data Governance: PII & Quality (Python, NEW)
41. ☑ Enhanced PII scanner: regex + heuristic + column-name + value-entropy signals
42. ☑ PII severity classification + recommended masking strategy
43. ☑ Reversible/irreversible masking utilities (hash, redact, tokenize, bucket)
44. ☑ DAMA-DMBOK 6-dimension scorer surfaced as a single report object
45. ☑ Privacy-preserving lineage option (mask PII column names in exports)
46. ☑ Data-contract validator (declare + assert schema/constraints)
47. ☑ Quality → governance integration: attach scores to catalog entries
48. ☑ Retention-policy evaluator (flag stale-beyond-policy datasets)
49. ☑ Unit tests for PII scanner + masking + DMBOK scorer
50. ☑ Audit-trail decorator applied to new governance ops

## Wave 6 — Sidecar API surfacing (Python + Electron)
51. ☑ `app/sidecar_api.py` (FastAPI): health + capability probe
52. ☑ Endpoint: Bayesian Beta-Binomial yield rate (PyMC ADVI + bootstrap fallback)
53. ☑ Endpoint: Prophet forecast
54. ☑ Endpoint: PII scan for posted rows
55. ☑ Endpoint: DMBOK quality score for posted rows
56. ☑ Endpoint: FAIRness score for a dataset descriptor
57. ☑ Endpoint: anomaly detection (z-score/seasonal)
58. ☑ CORS locked to localhost; graceful degradation when libs absent
59. ☑ Electron `main.js` spawns `app.sidecar_api:app`; capability badge in SPA
60. ☑ Sidecar integration tests (TestClient)

## Wave 7 — Governance surfaced in the SPA (NEW panels)
61. ☑ "Governance" tab: per-dataset DMBOK dimension scorecard (calls sidecar or client calc)
62. ☑ FAIRness scorecard panel with sub-score radar
63. ☑ PII inspector: scan current dataset, show flagged columns + masking preview
64. ☐ Lineage/provenance mini-graph for cart datasets (shared-column join graph)
65. ☑ Data-quality badge on each result card (completeness/freshness at a glance)
66. ☑ Export governance report (JSON + human-readable) per dataset
67. ☑ License + access metadata surfaced on dataset detail
68. ☑ Schema-diff visual highlighting in Compare modal

## Wave 8 — Performance & Scope (SPA + data layer)
69. ☑ Virtualized table rendering for large result/preview sets
70. ☑ Web Worker for heavy JSON parse / sort / profiling
71. ☑ Client-side LRU cache (sessionStorage) for fetched datasets w/ TTL
72. ☑ Debounce tuning + request cancellation hardening
73. ☑ Lazy-init heavy panels (map/Mermaid) only when first shown
74. ☑ Infinite-scroll option for result list
75. ☑ Rate-limit-aware multi-domain fetch (concurrency cap + 429 backoff)
76. ☐ Expand dataset registry coverage / discovery breadth
77. ☑ Parquet cache stats + cache-control surfaced in settings
78. ☑ Performance budget doc (LCP/INP/CLS targets) + lightweight runtime timing

## Wave 9 — Quality, Docs & Hardening
79. ☑ Vendor all CDN libs locally for fully-offline SPA (Electron)
80. ☑ Branded app icons (ico/icns/png) for Electron
81. ☑ Update /docs + in-app help/FAQ for all new features
82. ☑ New tests green; ruff + lint clean; no regressions to CI
83. ☑ Security pass: no secrets committed; CORS/localhost-only; input validation
84. ☑ CHANGELOG entry + this plan marked complete

---

_This plan is itself a governance artifact: an auditable record of intent,
scope, and evidence base for the upgrade program._
