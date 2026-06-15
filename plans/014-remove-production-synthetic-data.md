# Plan 014: Remove All Production Synthetic/Hardcoded Data

**Commit base:** 41df6aa
**Status:** TODO
**Priority:** CRITICAL — blocks analytics integrity

## Problem
Production code in `app/` returns hardcoded fake data to users:
1. `app/services/analytics_service.py:279-286` — `_get_mock_kpis()` returns static fake KPIs
2. `app/services/analytics_service.py:199-206` — hardcoded time series `[85,86,84,87,85]*8`
3. `app/insight_engine.py:62-65` — `np.random.rand()` / `np.random.randint()` for MCMC diagnostics
4. `app/sidecar_api.py:207-226` — fake Beta samples returned as "bootstrap" Bayesian analysis

## Fix
- Replace `_get_mock_kpis()` fallback with `{"_unavailable": True}` sentinel and update callers to show "Data unavailable" instead of fake numbers
- Replace hardcoded time series with empty DataFrame + error log
- Remove `r_hat`/`ess` random generation; omit those fields when PyMC not available
- In sidecar_api.py Beta fallback: return `{"method": "conjugate_beta", "warning": "PyMC unavailable — frequentist conjugate only"}` instead of mislabeling as bootstrap

## Verification
```bash
python -m pytest tests/ -q --tb=short
grep -rn "mock_kpis\|r_hat.*random\|ess.*randint\|85, 86, 84" app/ src/ --include="*.py"
# must return 0 matches
```
