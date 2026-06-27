# Fuzzy Matching Weight Calibration Report
**Date:** 2026-06-20  
**Executed by:** Antigravity (Gemini 3.5 Flash)  
**Training dataset:** 1,372 labeled variants (309 KPIs)

## Executive Summary
Successfully calibrated the hybrid fuzzy matching algorithm for NYC DOT SIM analyst question routing. By introducing the KPI ID as part of the indexed target document, we achieved a baseline accuracy of 80.5% and optimized it to **82.1%** accuracy across 1,372 variants, matching 309 target KPIs.

## Metrics
- **Training set size:** 1,372 question variants
- **KPIs covered:** 309 (full catalog)
- **Baseline accuracy:** 80.5% (generic weights: 80% BM25 / 15% FastText / 5% Jaccard)
- **Optimized accuracy:** 82.1% (calibrated weights: 86% BM25 / 4% FastText / 10% Jaccard)
- **Improvement:** +1.6 percentage points (pp)

## Optimal Weights
- **BM25:** 0.86 (vs. 0.80 baseline)
- **FastText (TF-IDF proxy):** 0.04 (vs. 0.15 baseline)
- **Jaccard:** 0.10 (vs. 0.05 baseline)

## Accuracy by Variant Type (Optimized)
| Type | Accuracy | Count |
|------|----------|-------|
| Abbreviation | 97.8% | 228 |
| Synonym swap | 87.4% | 222 |
| Direct phrasing | 82.2% | 309 |
| Casual | 76.0% | 304 |
| Technical | 72.8% | 309 |

## Integration Status
- ✅ Embeddings cached to Desktop (`.embeddings_cache/`)
- ✅ Memora SQLite DB edges created (`calibrated_weight_for`)
- ✅ Claude Code memory updated (`fuzzy_matching_hybrid_algorithm_research.md` & `MEMORY.md`)
- ✅ Weights ready for production deployment in `QuestionKPIResolver`

## Next Steps
1. Deploy calibrated weights (`BM25=0.86, FastText=0.04, Jaccard=0.10`) to the production `QuestionKPIResolver` in `socrata_toolkit/core/question_resolver.py`.
2. Monitor production shadow traffic logs and retrain on new analyst formulations monthly.
