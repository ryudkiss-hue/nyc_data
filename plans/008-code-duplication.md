# Plan 008: Code Duplication — Tech Debt (DEFERRED)

**Finding:** ConnectionManager duplicates MotherDuckClient logic  
**File:** `src/socrata_toolkit/platform/connection.py` vs `src/socrata_toolkit/motherduck/client.py`  
**Severity:** LOW  
**Effort:** LARGE (2–3h refactor)  
**Risk:** HIGH (architectural change, multiple callers affected)  
**Status:** DEFERRED — Suitable for future refactor cycle, not for this iteration

## Problem

ConnectionManager re-implements connection pooling, token auth, and fallback logic that already exists in MotherDuckClient:
- `motherduck/client.py` has: `MotherDuckClient` class with `connect()`, connection pooling, timeout handling
- `platform/connection.py` has: `ConnectionManager` class with similar fallback, token auth, caching

Result:
- Bug fixes applied to one aren't applied to the other
- Two separate code paths to maintain
- Inconsistent error handling, logging, and timeout behavior
- Future improvements (e.g., connection pooling) need to be done twice

## Why Deferred

This fix requires:
1. **Refactoring** — Remove ConnectionManager, create thin wrapper around MotherDuckClient
2. **Testing** — Update all callers (app/cloud_run.py, tests, CLI) to use MotherDuckClient API
3. **Risk** — High: touches core connection layer used across multiple modules
4. **Scope** — Out of scope for "minimal surgical fixes"

Current user request: "Make minimal, surgical fixes. No refactoring beyond what's needed."

This finding is a **design improvement**, not a production bug, so it's appropriate to defer to a future maintenance cycle.

## Recommended Approach (Future)

When scheduling a larger refactor:

### Option A: Consolidate with MotherDuckClient
1. Review `MotherDuckClient` API and extend if needed
2. Update `get_connection()` module function to wrap MotherDuckClient directly
3. Remove `ConnectionManager` class entirely
4. Update all imports in `app/cloud_run.py` and elsewhere
5. Add integration tests for the wrapper

### Option B: Formalize Connection Layer
1. Keep both but establish clear boundaries:
   - `MotherDuckClient` = cloud platform client (Socrata uses this)
   - `ConnectionManager` = cloud/local fallback abstraction (Cloud Run deployment uses this)
2. Ensure all platform-detection logic in one place
3. Document the division of responsibility

### Option C: Create ConnectionPool Interface
1. Define a `ConnectionPool` protocol/interface
2. Implement for MotherDuck and DuckDB separately
3. Use dependency injection in cloud_run.py

## Action Items

- [ ] Add to backlog / project board for future refactor cycle
- [ ] Tag as "tech-debt" in code review / issue tracker
- [ ] Document decision not to refactor in current PR comments
- [ ] Revisit when planning next major infrastructure change

## Related Code

**MotherDuckClient (should be source of truth):**
```
src/socrata_toolkit/motherduck/client.py
├── MotherDuckClient class
├── token auth (line 42–44)
├── connection pooling (line 50)
├── database init (line 75–95)
└── query execution (line 97–115)
```

**ConnectionManager (duplicate logic):**
```
src/socrata_toolkit/platform/connection.py
├── ConnectionManager class (lines 28–137)
├── token auth (line 80–87)
├── fallback logic (line 68–76)
└── connection caching (line 93–94, 112–113)
```

**Callers:**
- `app/cloud_run.py` — currently uses `from socrata_toolkit.platform import get_connection`
- `scripts/daily_refresh.py` — if it uses connection layer
- Tests in `tests/` directory

## Maintenance Notes Until Refactored

- When fixing bugs in either ConnectionManager or MotherDuckClient, apply to both
- Document any behavioral differences in code comments
- Consider adding a wrapper function that explicitly logs which implementation is being used
- During code reviews, flag any divergence between the two implementations

## Success Criteria (When Ready to Execute)

- [ ] MotherDuckClient review confirms it's suitable as base
- [ ] All callers identified and transition plan written
- [ ] Integration tests updated to use new single implementation
- [ ] No behavioral change to public API (get_connection() still works)
- [ ] All three connection manager tests pass (motherduck, duckdb, fallback)
- [ ] Performance metrics (latency, connections/sec) remain stable
- [ ] Code duplication eliminated
