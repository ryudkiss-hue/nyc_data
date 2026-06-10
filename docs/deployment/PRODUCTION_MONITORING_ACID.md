# ACID Reliability Monitoring (Week 1)

**Status:** Production Monitoring Configuration  
**Date:** June 10, 2026  
**Duration:** 24-hour continuous watch

---

## Metrics to Watch (24h)

| Metric | Target | Alert Threshold | Notes |
|--------|--------|-----------------|-------|
| DuckDB connection pool utilization | <50% | >50% | Investigate pool exhaustion |
| Transaction success rate | >99.9% | <99.9% | Page on-call immediately |
| Transaction rollback count | 0 (intentional only) | >0 unplanned | Investigate rollback causes |
| Lock wait times | <5ms typical | >10ms avg | Investigate contention |
| Session state persistence uptime | 100% | <100% | Immediate escalation |
| Error rate (all operations) | <0.1% | >0.1% | Investigate error sources |

---

## Alerting Thresholds

### CRITICAL (Immediate Escalation)
- **Transaction failures >0.1%** → Page on-call immediately
- **Session persistence failures >0** → Immediate escalation (data loss risk)
- **Error rate >1%** → Critical alert

### HIGH (Investigate)
- **Connection pool >50%** → Investigate pool exhaustion
- **Lock timeouts >10ms average** → Investigate lock contention
- **P99 latency >500ms** → Investigate performance degradation

### MEDIUM (Monitor)
- **Connection pool >40%** → Monitor trend
- **Lock wait times >5ms** → Monitor for escalation
- **Error rate >0.05%** → Monitor sources

---

## Dashboard Configuration

**Create monitoring dashboard with:**
- Real-time connection pool utilization graph
- Transaction success rate (%) with alert zones
- Lock wait time histogram (ms)
- Rollback count per hour
- Session persistence uptime percentage
- Error rate trend
- P50/P95/P99 latency for critical operations

**Data Sources:**
- DuckDB connection pool metrics (from `duckdb_store.py` monitoring)
- Transaction logs (app logs)
- Session persistence table (check audit trail)
- Application error logs

---

## Manual Verification Procedures

### Verify Connection Pooling (Every 2 hours)
```bash
# Check DuckDB connection status
sqlite3 data/local_db/nyc_mission_control.duckdb ".tables"
# Expected: Shows all tables, no connection errors
```

### Verify Session Persistence (Every 4 hours)
```sql
-- Check session state table exists and has data
SELECT COUNT(*) as session_count FROM session_state;
-- Expected: >0 rows, recent timestamps in staged_at column
```

### Verify Transaction Logs (Every 4 hours)
```bash
# Check application logs for transaction errors
tail -100 logs/app.log | grep -i "transaction\|rollback"
# Expected: Mostly COMMIT messages, no ROLLBACK unless intentional
```

### Verify No Data Inconsistencies (Every 6 hours)
```sql
-- Spot check for data integrity
SELECT COUNT(*) FROM staging.inspections;
SELECT COUNT(*) FROM staging.permits;
SELECT COUNT(*) FROM staging.ramps;
-- Expected: Row counts stable, no sudden drops
```

---

## Escalation Procedures

**If Alert Triggered:**

1. **Check alert details:** Metric, threshold, current value, time
2. **Log incident:** Note time, metric, value, actions taken
3. **Investigate:** Check logs, connection status, recent changes
4. **Mitigate:** Follow action plan below

**If Transaction Failures Spike:**
- Check DuckDB connection pool status
- Review transaction logs for errors
- Check for concurrent access issues
- Verify ACID fixes deployment is active
- If persists: Possible rollback (see below)

**If Session Persistence Fails:**
- Check DuckDB connectivity immediately
- Verify session_state table accessible
- Check file system for disk space issues
- Data loss risk - escalate immediately

**If Connection Pool Exhausted:**
- Check active connections
- Identify long-running queries
- Kill stale connections if necessary
- Monitor for recovery

---

## Rollback Procedures

**If deployment needs to rollback (estimated <5 minutes):**

```bash
# Step 1: Identify current commit
git log --oneline -1
# Should show: ACID reliability fixes commit

# Step 2: Revert to previous version
git revert HEAD  # OR git reset --hard HEAD~1

# Step 3: Restart application
systemctl restart nyc-socrata-app  # Or equivalent restart command

# Step 4: Verify rollback successful
# - Check connection pool works
# - Check session persistence available
# - Monitor error rate returns to baseline
```

**Verification after rollback:**
- Error rate <0.1% within 2 minutes
- No new escalations
- Connection pool <50%
- Session persistence working

---

## Daily Reporting

**9am Review (Overnight Metrics):**
- Peak connection pool utilization
- Transaction success rate overnight
- Any alerts triggered
- Rollback count
- Incident summary if any

**4pm Review (End of Day):**
- 24-hour aggregate metrics
- Trend analysis
- Any escalations
- Recommendation for next steps

**Final Report (Friday 6pm):**
- Full 24-hour summary
- Go/no-go for production
- Recommendation for next phase

---

## Success Criteria

✅ **Week 1 Monitoring Complete:**
- Zero critical incidents
- Error rate <0.1% throughout
- Connection pool <50% utilization
- Session persistence 100% uptime
- Transaction success >99.9%
- No rollbacks required

**If All Targets Met:** Approved to proceed with remaining Phase 1 deployments

**If Any Target Missed:** Investigate root cause before proceeding

---

## Contact & Escalation

**On-Call:** [Engineering Lead]  
**Escalation:** [VP Engineering]  
**Resolution SLA:** 1 hour for critical alerts

---

**Configuration Date:** June 10, 2026  
**Status:** Ready for 24-hour production watch  
**Last Updated:** 2026-06-10 14:45 UTC
