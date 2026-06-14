# Implementation Plans

This directory contains self-contained implementation plans produced by the
`/improve` audit (2026-06-12, commit `4343044`). Each plan is designed to be
executed independently by an agent or engineer without requiring context from
the audit session.

## Execution order

| # | Plan | Priority | Effort | Risk | Depends on | Status |
|---|------|----------|--------|------|------------|--------|
| 001 | [security-env-credentials](001-security-env-credentials.md) | P1 | S | LOW | — | TODO |
| 002 | [security-motherduck-token](002-security-motherduck-token.md) | P1 | S | LOW | — | TODO |
| 003 | [perf-callback-memoization](003-perf-callback-memoization.md) | P2 | S | LOW | — | TODO |
| 004 | [analysis-init-refactor](004-analysis-init-refactor.md) | P1 | M | MED | — | TODO |
| 005 | [deps-cleanup](005-deps-cleanup.md) | P2 | S | LOW | — | TODO |

## Dependency graph

```
001 (security-env-credentials)   ──┐
002 (security-motherduck-token)  ──┤── independent, all can run in parallel
003 (perf-callback-memoization)  ──┤
004 (analysis-init-refactor)     ──┤
005 (deps-cleanup)               ──┘
```

No plan depends on another. Plans 001 and 002 are both P1 security fixes and
should be executed first, in either order or in parallel. Plan 004 is also P1
and addresses the root cause of recurring CI collection failures.

## Recommended execution order

1. **001 + 002** simultaneously — security issues; burned credentials and SQL
   token injection are the highest risk items.
2. **004** — P1 tech-debt; eliminates the `_legacy_import` junk-drawer that
   has caused four consecutive CI-fixing commits.
3. **003 + 005** simultaneously — P2 polish; memoization perf win and
   dependency manifest cleanup.

## Categories

| Category | Plans |
|----------|-------|
| security | 001, 002 |
| perf | 003 |
| tech-debt | 004 |
| migration | 005 |

## Status values

- `TODO` — not started
- `IN PROGRESS` — executor has branched and is working
- `DONE` — merged to main, done criteria verified
- `BLOCKED` — waiting on a STOP condition to be resolved
