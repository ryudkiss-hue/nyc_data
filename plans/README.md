# Implementation Plans

This directory contains self-contained implementation plans produced by two
`/improve` audit passes:
- First pass (2026-06-12, commit `4343044`): Plans 001–007 — security, perf, tech-debt, DX
- Second pass (2026-06-14, commit `1e84782`): Plans 008–013 — UX/UI/accessibility

Each plan is designed to be executed independently by an agent or engineer
without requiring context from the audit session.

## Execution order

| # | Plan | Priority | Effort | Risk | Depends on | Status |
|---|------|----------|--------|------|------------|--------|
| 001 | [security-env-credentials](001-security-env-credentials.md) | P1 | S | LOW | — | TODO |
| 002 | [security-motherduck-token](002-security-motherduck-token.md) | P1 | S | LOW | — | TODO |
| 003 | [perf-callback-memoization](003-perf-callback-memoization.md) | P2 | S | LOW | — | TODO |
| 004 | [analysis-init-refactor](004-analysis-init-refactor.md) | P1 | M | MED | — | TODO |
| 005 | [deps-cleanup](005-deps-cleanup.md) | P2 | S | LOW | — | TODO |
| 006 | [skill-md-doc-fixes](006-skill-md-doc-fixes.md) | P2 | S | LOW | — | DONE |
| 007 | [skill-demo-modes](007-skill-demo-modes.md) | P2 | M | LOW | — | DONE |
| 008 | [dash-startup-crashes](008-dash-startup-crashes.md) | P0 | S | LOW | — | TODO |
| 009 | [filter-system-integration](009-filter-system-integration.md) | P1 | M | LOW | 008 | TODO |
| 010 | [kpi-cards-activation](010-kpi-cards-activation.md) | P1 | M | LOW | 008, 009 | TODO |
| 011 | [register-analytics-callbacks](011-register-analytics-callbacks.md) | P1 | M | LOW | 008 | TODO |
| 012 | [accessibility-fixes](012-accessibility-fixes.md) | P2 | S | LOW | — | TODO |
| 013 | [navigation-cleanup](013-navigation-cleanup.md) | P2 | S | LOW | — | TODO |

## Dependency graph

```
001 (security-env-credentials)   ──┐
002 (security-motherduck-token)  ──┤
003 (perf-callback-memoization)  ──┤── independent, all can run in parallel
004 (analysis-init-refactor)     ──┤
005 (deps-cleanup)               ──┤
006 (skill-md-doc-fixes)         ──┤ (DONE)
007 (skill-demo-modes)           ──┘ (DONE)

008 (dash-startup-crashes)       ──┬── must run first among UX plans
                                   ├── 009 (filter-system-integration)
                                   │     └── 010 (kpi-cards-activation)
                                   └── 011 (register-analytics-callbacks)

012 (accessibility-fixes)        ──┐── independent of 008–011
013 (navigation-cleanup)         ──┘
```

## Recommended execution order

### Prior audit (001–007)
1. **001 + 002** simultaneously — security issues; burned credentials and SQL
   token injection are the highest risk items.
2. **004** — P1 tech-debt; eliminates the `_legacy_import` junk-drawer that
   has caused four consecutive CI-fixing commits.
3. **003 + 005** simultaneously — P2 polish; memoization perf win and dependency cleanup.

### UX audit (008–013)
1. **008** — P0; fixes startup crashes. App cannot start without this.
2. **009 + 011 + 012 + 013** simultaneously — filter wiring, analytics registration,
   accessibility, and navigation cleanup are all independent once 008 lands.
3. **010** — after 009 lands (KPI cards depend on the filter store schema being correct).

## Categories

| Category | Plans |
|----------|-------|
| security | 001, 002 |
| perf | 003 |
| tech-debt | 004 |
| migration | 005 |
| docs | 006 |
| dx | 007 |
| correctness/UX | 008, 009, 010, 011 |
| accessibility | 012 |
| UX/DX | 013 |

## Considered and rejected

- Adding `--demo` to all 30 skill scripts — most already have demo/summary modes
  or are designed as composable library tools; only `run_audit.py` and
  `chart_builder.py` had genuine blocking DX issues (API-required or no data path).
- Adding sklearn to the base skill requirements — all clustering falls back to
  rule-based segmentation; keeping it optional is the right call.
- Rewriting the `visualization_asset()` component — the multi-tab wrapper (Visual /
  Insights / Raw Data / Export) is sound UX; only the missing callback wiring needed
  fixing (Plan 011), not the component structure itself.
- Removing export buttons from `visualization_asset()` — 9 buttons exist but only
  CSV/Markdown/Python are implemented in `export_callbacks.py`. Left as-is; the
  unimplemented buttons degrade gracefully (no action). Addressing this is a
  separate feature effort, not a UX bug.
- Replacing the glassmorphism visual style — the backdrop-filter / blur CSS is
  intentional design; only the missing `prefers-reduced-motion` guard was a bug
  (fixed in Plan 012).

## Status values

- `TODO` — not started
- `IN PROGRESS` — executor has branched and is working
- `DONE` — merged to main, done criteria verified
- `BLOCKED` — waiting on a STOP condition to be resolved
