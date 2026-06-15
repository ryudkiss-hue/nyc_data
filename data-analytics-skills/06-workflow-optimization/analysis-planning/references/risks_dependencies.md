# Risks and Dependencies Reference

Log every risk and external dependency before starting work. Unlogged risks are the #1 cause of missed deadlines in SIM analytics.

## Risk categories

### Data risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Dataset is stale beyond SLA | Medium | High | Run `dataset health` first; substitute dataset if available |
| API token missing for >2K row fetch | Medium | High | Confirm `SOCRATA_APP_TOKEN` is set before planning full-corpus work |
| Schema changed since last run | Low | High | Run `socrata schema-drift` at start of each session |
| Known empty / erroring dataset used | Low | Critical | Check known issues table in CLAUDE.md before any fetch |
| Null rate invalidates metric | Medium | High | Profile nulls with `quality_score` before calculating rates |
| Duplicate rows inflate counts | Medium | Medium | Check `score.consistency` component; deduplicate on `objectid` |

### Methodology risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Normal approximation CI used for small n | Medium | Medium | Use Wilson Score when n < 1000 (always) |
| Borough codes inconsistent (e.g. "MN" vs "Manhattan") | High | Medium | Normalize with `upper(borough)` in SOQL |
| Time zone misalignment in date filters | Medium | Medium | Use ISO 8601 UTC in `$where` clauses |
| Joining on non-unique key (fan-out) | Low | High | Verify key uniqueness before joining; add DISTINCT if needed |

### External dependencies

| Dependency | Owner | Status to confirm | Fallback |
|---|---|---|---|
| Socrata API availability | NYC Open Data | Check status.data.cityofnewyork.us | Use DuckDB cache (`query_parquet_cache()`) |
| ANTHROPIC_API_KEY for NL query | Analyst env | Confirm key is set | Write SOQL manually |
| DuckDB cache freshness | Cache scheduler | Check cache timestamp vs SLA | Force refresh with `socrata cache refresh <key>` |
| Stakeholder data dictionary | PM / data owner | Confirm column definitions before interpreting | Use CLAUDE.md glossary as fallback |
| PostgreSQL DSN for upsert | Infra team | Required only for `socrata sync` | Write to local Parquet instead |

## Dependency log template

Copy this block into your analysis plan for each external dependency:

```
DEPENDENCY: <name>
Owner:       <team or person>
Needed by:   <step number that requires it>
Status:      CONFIRMED / PENDING / BLOCKED
Fallback:    <what to do if unavailable>
```

## Known recurring blockers in SIM workflows

1. **`ramp_locations` stale since 2021** — always substitute `ramp_progress` (e7gc-ub6z) for current ramp status.
2. **`permit_stipulations` API 403** — no workaround; exclude from conflict-detect workflows until resolved.
3. **Full-corpus fetch without token** — Socrata returns max 2,000 rows without `SOCRATA_APP_TOKEN`. Plans calling `--full-corpus` must confirm token is set first.
4. **`weekly_construction` stale since 2017** — use `street_construction_inspections` (ydkf-mpxb) or `street_permits` (tqtj-sjs8) instead.
5. **`capital_blocks` empty** — use `capital_intersections` (97nd-ff3i) with ~7.8K rows.
