---
title: ADR-0002: Deepened Question Resolver for SIM routing
status: ACCEPTED
date: 2026-06-19
decision_makers: Antigravity Agent + User
---

# ADR-0002: Deepened Question Resolver for SIM routing

## Problem
In `QuestionKPIResolver` and `QuestionMatcher`, the matching algorithms, tokenization, and composite weight scoring logic are split across multiple files. The resolver leaks internal matching details (such as Jaccard set calculations), making it a shallow module. Additionally, hardcoding KPI mappings in python prevents updates without redeploying code.

## Decision
1. **Unify Modules:** Merge `QuestionMatcher` into `QuestionKPIResolver`. The caller will only interact with `QuestionKPIResolver` (the external seam).
2. **Config-Driven Mappings:** Externalize the KPI mappings list into a structured config file (`config/kpi_mappings.json`). The resolver will load these mappings dynamically at startup.
3. **Private Strategies:** Implement matching algorithms as private strategies (`_bm25_score`, `_jaccard_score`, `_tfidf_score`) inside the resolver.

## Benefits
*   **Locality:** All scoring formulas, text normalizations, and SQLite Memora DB context enrichments reside in one module.
*   **Leverage:** Callers get single-method routing (`resolve_question`) without managing matches or scores.
*   **Test Surface:** Tests only need to assert inputs against `QuestionResolution` results.

## Alternatives Considered
*   **Keep Mappings Hardcoded:** Rejected because it makes scaling the KPI catalog hard for non-developers.
*   **Expose Matcher to Client:** Rejected to maintain module depth and hide indexing mechanics.

## Sign-Off
Approved by Antigravity Agent on behalf of the User.
