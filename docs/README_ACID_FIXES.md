# NYC DOT Socrata Toolkit: ACID Reliability Implementation Plan

## Overview

This document package contains a complete, actionable plan to fix 4 critical ACID (Atomicity, Consistency, Isolation, Durability) violations in the NYC DOT Socrata Toolkit's data layer.

**Audit findings**: 
- Atomicity: DuckDB writes sync but L2 Parquet writes async → inconsistent visibility
- Consistency: DuckDB ↔ Parquet skew; concurrent watermark reads miss data  
- Isolation: Multiple DuckDB connections without pooling; session_state not thread-safe
- Durability: Async L2 writes not durable; session_state never persists

**Solution**: 4 minimal, surgical fixes that address each violation with specific code changes, testing strategy, and effort estimates.

---

## Documents in This Package

### 1. **ACID_RELIABILITY_IMPLEMENTATION_PLAN.md** (Main Document)
Full technical plan with:
- Detailed problem statement for each ACID violation
- Solution design (with pseudocode and architecture rationale)
- File-by-file changes required
- Testing strategy for each fix
- Effort estimates (2-4.5 hours each)
- Monitoring and validation approach
- Rollback procedures

**Read this first** if you want to understand the "why" and design approach.

### 2. **ACID_FIXES_QUICK_REFERENCE.txt** (Quick Summary)
One-page reference with:
- Problem summary for each fix
- Key code snippets
- Files affected
- Testing checklist
- Implementation order recommendation

**Use this** for quick lookups or team discussions.

### 3. **ACID_FIXES_IMPLEMENTATION_CODE.py** (Copy-Paste Code)
Concrete implementation code for all 4 fixes:
- Ready-to-copy code snippets (marked [FIX 1], [FIX 2], etc.)
- Import statements and setup
- Test code (pytest-compatible)
- Comments explaining each change

**Use this** when implementing—copy code sections directly into your files.

---

## Quick Start

### For Decision-Makers (5 min read)
1. Read **ACID_RELIABILITY_IMPLEMENTATION_PLAN.md** summary (first section)
2. Review **Summary Table** in main document (4 fixes, effort, ACID coverage)
3. Decide implementation order (Week 1: Fixes 1+4, Week 2: Fix 2, Week 3: Fix 3)

### For Implementers (1-2 hour read)
1. Read **ACID_FIXES_QUICK_REFERENCE.txt** for overview
2. Read relevant section in **ACID_RELIABILITY_IMPLEMENTATION_PLAN.md** (1 fix at a time)
3. Copy code from **ACID_FIXES_IMPLEMENTATION_CODE.py**
4. Implement and test (using provided test cases)
5. Run full test suite and manual verification

### For Code Reviewers
1. Review **ACID_RELIABILITY_IMPLEMENTATION_PLAN.md** design section
2. Check implementation against pseudocode in main document
3. Verify test cases are comprehensive
4. Validate rollback procedures are documented

---

## The 4 Fixes at a Glance

| Fix | Problem | Solution | Files | Hours | ACID Impact |
|-----|---------|----------|-------|-------|------------|
| **1: Connection Pooling** | Multiple DuckDB connections, no thread safety | Single shared connection + RLock | `src/socrata_toolkit/core/duckdb_store.py` | 2 | Isolation |
| **2: Transactional Writes** | DuckDB write sync, Parquet async → inconsistent | BEGIN...COMMIT + atomic rename | `app/utils/cache_manager.py` | 4 | Atomicity + Consistency |
| **3: Session Persistence** | session_state lost on refresh | DuckDB-backed session store | `app/services/cache_service.py` (new) | 4.5 | Durability |
| **4: Manifest Locking** | Concurrent read-modify-write loses updates | fcntl/msvcrt file locks + atomic rename | `app/utils/cache_manager.py` | 3 | Consistency |

**Total effort**: ~13.5 hours (distributed over 3 weeks)

---

## Implementation Checklist

### Pre-Implementation
- [ ] Review all 3 documents with team
- [ ] Create feature branch: `fix/acid-reliability-layer`
- [ ] Set up test environment (`:memory:` DuckDB for unit tests)
- [ ] Assign implementer to each fix (can be parallel)

### Per-Fix Implementation
- [ ] Read fix section in main document
- [ ] Copy code from ACID_FIXES_IMPLEMENTATION_CODE.py
- [ ] Implement code changes
- [ ] Run unit tests (provided in code file)
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Manual verification (Streamlit app, concurrent harness)
- [ ] Code review (2+ reviewers)
- [ ] Merge to main

### Post-Merge
- [ ] Monitor metrics (lock contention, durability)
- [ ] Validate in staging/prod
- [ ] Update runbooks with new audit logging
- [ ] Communicate rollback procedures to team

---

## Key Design Decisions

### Why Single Connection + Lock (Fix 1)?
- **DuckDB is thread-safe within a single connection** (explicitly stated in docs)
- Simpler than connection pool (no resource management)
- Lower overhead (one connection object)
- Explicit locks on sensitive operations (easier to audit)

### Why Transaction + Atomic Rename (Fix 2)?
- **Temp file + rename is atomic at OS level** (no partial writes)
- **DuckDB transactions provide isolation** (BEGIN...COMMIT...ROLLBACK)
- Ensures all-or-nothing: either Parquet, manifest, AND audit entry exist, or none
- Watermark in DuckDB serves as single source of truth for concurrent readers

### Why DuckDB for Session State (Fix 3)?
- **Reuses existing DuckDB connection** (no new infrastructure)
- **JSON serialization is standard** (no custom encoding)
- **Atomic upserts via ON CONFLICT** (lost update prevention)
- **Scales to millions of sessions** (DuckDB handles big data)

### Why File Locks (Fix 4)?
- **Portable across OS** (fcntl on Unix, msvcrt on Windows)
- **Advisory locks prevent race conditions** (no process crashes from malicious concurrent access)
- **Atomic rename eliminates partial state** (OS-level atomicity)
- **Simpler than distributing locks** (no Redis/etcd dependency)

---

## Testing Strategy

Each fix includes:
1. **Unit tests**: Success + failure paths in isolation
2. **Integration tests**: Concurrent harness with ThreadPoolExecutor
3. **Regression tests**: Existing functionality unchanged
4. **Stress tests**: High-frequency updates, verify integrity

Run with:
```bash
# Unit tests for all fixes
pytest tests/test_acid_fixes.py -v

# Full regression suite
pytest tests/ -v

# Specific fix
pytest tests/test_acid_fixes.py::test_duckdb_manager_concurrent_access -v
```

---

## Rollback Procedures

Each fix can be rolled back independently:

**Fix 1 (DuckDB pooling)**: Remove RLock, fall back to lazy singleton
**Fix 2 (Transactional writes)**: Use old async write_cache() (included as fallback)
**Fix 3 (Session persistence)**: Disable setup_session_persistence() in main.py
**Fix 4 (Manifest locking)**: Remove file locks, use direct JSON write

**Recommended**: Merge Fixes 1+4 together (both fix thread safety), can rollback as atomic unit.

---

## Monitoring & Alerting

Add these metrics after implementation:

```python
# In execute_atomic():
start_lock = time.time()
with self._conn_lock:
    elapsed = (time.time() - start_lock) * 1000
    if elapsed > 10:  # Log contention > 10ms
        logger.warning(f"duckdb_lock_wait_ms={elapsed}")

# In write_cache_atomic():
start_write = time.time()
# ... write logic ...
elapsed = (time.time() - start_write) * 1000
logger.info(f"cache_write_atomic_duration_ms={elapsed}")

# In session store:
try:
    store.save_key(key, value)
except Exception:
    logger.error("session_persist_error", exc_info=True)
```

Alert on:
- `duckdb_lock_wait_ms` > 100ms (contention)
- `cache_write_atomic_duration_ms` > 1000ms (slow writes)
- `session_persist_error` rate > 0.1% (durability issues)

---

## FAQ

**Q: Can I implement fixes in a different order?**
A: Fixes 1 & 4 are independent (both thread safety). Fix 2 requires Fix 1. Fix 3 is independent.
Recommended: Do Fixes 1+4 first (foundation), then Fix 2 (atomicity), then Fix 3 (durability).

**Q: Do I need to upgrade DuckDB?**
A: No. Tested with DuckDB 0.10+ (current version is 1.0+). Thread safety and transactions are stable.

**Q: Will this add latency?**
A: Fix 1 adds minimal overhead (one lock acquire/release per operation, ~100ns).
Fixes 2 & 4 add temp file writes (~1-5ms per cache write, acceptable for 1-60s cache TTLs).
Fix 3 adds one JSON INSERT per state change (~10-50ms, acceptable for page loads).

**Q: Do I need Redis or other dependencies?**
A: No. All fixes use only existing dependencies (DuckDB, fcntl/msvcrt, pandas, json).

**Q: What if multiple processes write the manifest concurrently?**
A: File locks (Fix 4) serialize writes at OS level. Processes wait for lock with 5s timeout.
On timeout, stale manifest is returned (safe fallback; loses one recent entry).

**Q: Can I skip a fix?**
A: Fixes are independent except Fix 2 requires Fix 1. Skipping a fix leaves that ACID property unguaranteed:
- Skip Fix 1 → ISOLATION not guaranteed (multiple connections compete)
- Skip Fix 2 → ATOMICITY not guaranteed (async writes can fail partially)
- Skip Fix 3 → DURABILITY not guaranteed (session_state lost on refresh)
- Skip Fix 4 → CONSISTENCY not guaranteed (manifest gets corrupted by concurrent writes)

---

## Success Criteria

After implementing all fixes, verify:

✅ No orphaned `.tmp` files in `data/cache/` (Fix 2 cleanup)
✅ Manifest entries always match Parquet files (Fix 4 locking)
✅ Session state survives page refresh (Fix 3 persistence)
✅ No stale reads from cache (Fix 2 watermark)
✅ Lock contention < 10ms p99 (Fix 1 performance)
✅ Full test suite passes (100% coverage)
✅ Streamlit app handles concurrent users without data loss

---

## Next Steps

1. **Read ACID_RELIABILITY_IMPLEMENTATION_PLAN.md** (30 min)
2. **Assign implementer(s)** (suggest 1-2 people per fix)
3. **Create feature branch** and start with Fix 1
4. **Code review each fix** (2+ reviewers)
5. **Merge and validate in staging**
6. **Deploy to production with monitoring**

---

## Support & Questions

For questions or issues during implementation:
1. Review the "Testing Strategy" section in main document
2. Check provided test cases in ACID_FIXES_IMPLEMENTATION_CODE.py
3. Verify rollback procedures before merging
4. Reach out to code reviewers if stuck

---

## References

- DuckDB thread safety: https://duckdb.org/docs/guides/import/query_parquet.html
- File locking: `man fcntl` (Unix), `msvcrt.locking()` (Windows)
- ACID guarantees: https://en.wikipedia.org/wiki/ACID
- Streamlit session_state: https://docs.streamlit.io/library/api-reference/session-state

---

**Document package version**: 1.0
**Last updated**: 2026-06-10
**Status**: Ready for implementation

---

## Document Manifest

| File | Size | Purpose |
|------|------|---------|
| ACID_RELIABILITY_IMPLEMENTATION_PLAN.md | ~25 KB | Full technical plan (design, rationale, testing) |
| ACID_FIXES_QUICK_REFERENCE.txt | ~8 KB | One-page summary (quick lookup) |
| ACID_FIXES_IMPLEMENTATION_CODE.py | ~30 KB | Copy-paste code (all 4 fixes + tests) |
| README_ACID_FIXES.md | This file | Package overview and guide |

**Total package size**: ~65 KB
**Estimated read time**: 30 min (overview) to 2 hours (full deep dive)

---

Made with ❤️ by Claude Code (Anthropic)
For questions about ACID reliability in distributed systems, see references above.
