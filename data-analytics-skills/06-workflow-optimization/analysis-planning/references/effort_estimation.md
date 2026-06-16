# Effort Estimation Reference

Use this guide to assign time estimates per analysis step, then sum to a total and compare against your deadline.

## Calibration table — NYC DOT analysis tasks

| Task type | Typical effort | Notes |
|---|---|---|
| Dataset health check (one dataset) | 5 min | `socrata dataset health --key <key>` |
| Dataset health check (all 26 datasets) | 10 min | `socrata dataset health --all --sort-by staleness` |
| Fetch + profile (< 50K rows, filtered) | 15 min | Add 10 min if schema is unfamiliar |
| Fetch + profile (full corpus, > 50K rows) | 30–60 min | Requires SOCRATA_APP_TOKEN; confirm before running |
| Single-metric calculation (count, rate, mean) | 15 min | |
| Borough-level breakdown with Wilson CI | 30 min | Use `compute_borough_completion_rates()` |
| Time-series trend (monthly, 12 months) | 45 min | |
| Spatial join (two geo datasets) | 60 min | Add 30 min for DBSCAN clustering |
| Quality scorecard (composite 0–100) | 20 min | `compute_quality_score()` |
| Schema drift detection | 10 min | `socrata schema-drift` |
| NL → SoQL translation + validation | 10 min | `socrata nl-query` |
| Outlier detection (IQR) | 20 min | `socrata outliers --method iqr` |
| Write-up / findings narrative | 30–60 min | Per borough = +10 min each |
| Stakeholder presentation prep | 60 min | |
| PDF / Excel / PPTX export | 15 min | `socrata report` |

## Estimation rules of thumb

1. **Add 30% buffer** to your raw estimate total for data surprises (nulls, schema changes, stale tokens).
2. **Flag if total > 4 hours**: break into phases with a checkpoint after Phase 1.
3. **Parallel steps save wall-clock time** but not effort. Mark steps that can run concurrently.
4. **Data access latency**: Socrata API cold calls average 2–8 seconds per 1K rows. DuckDB cache reads are <100ms. Prefer cache where fresh enough.

## Worked example — Violation trend investigation

| Step | Task | Estimate |
|---|---|---|
| 1 | Dataset health check for violations (6kbp-uz6m) | 5 min |
| 2 | Fetch violations last 6 months, Manhattan only | 20 min |
| 3 | Monthly count by violation_type | 15 min |
| 4 | MoM change calculation | 15 min |
| 5 | Flag outlier months (IQR) | 20 min |
| 6 | Write-up with borough comparison table | 45 min |
| | **Raw total** | **120 min** |
| | **+30% buffer** | **156 min (~2.5 hrs)** |

## Estimation anti-patterns

- **Anchoring to a round number**: "This should take 2 hours" without breaking it down. Always decompose first.
- **Ignoring data access blockers**: If `SOCRATA_APP_TOKEN` is unset and you need >2K rows, add 30 min for token setup.
- **Forgetting the write-up**: Analysis without narrative delivery is never done. Always budget 30+ min for findings.
- **Not accounting for review cycles**: If peer review is required, add 60 min for reviewer turnaround and fixes.
