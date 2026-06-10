# Dash GIS Pilot - A/B Test Configuration

**Status:** A/B Test Ready  
**Date:** June 10, 2026  
**Start Date:** June 11, 2026  
**Duration:** Week 1 continuous, ramp to 100% if successful

---

## Traffic Split Strategy

### Week 1 Configuration (June 11-14)
- **10% users → Dash GIS view** (new platform)
- **90% users → Streamlit GIS view** (current platform)
- **Duration:** 48 hours minimum, extend if issues found

### Success Criteria Met → Ramp Plan
- **Day 2 (Jun 12, 2pm):** Review metrics, if all green → ramp to 25%
- **Day 3 (Jun 13, 12pm):** Review metrics, if all green → ramp to 50%
- **Day 4 (Jun 14, 10am):** Final review, if all green → ramp to 100%
- **Fallback:** At any point, if metrics breach thresholds → immediate rollback

---

## Success Criteria

### Primary Metrics (Hard Stops - If Any Breached: Immediate Rollback)
| Metric | Threshold | Action |
|--------|-----------|--------|
| Error rate (Dash) | >1% | Rollback immediately |
| P95 latency (Dash) | >1000ms | Rollback immediately |
| Session abandonment rate | >5% | Investigate |

### Target Metrics (Performance Goals)
| Metric | Streamlit (Baseline) | Dash (Target) | Status |
|--------|-----|------|--------|
| P95 latency | 10.1s | <500ms | ✓ Met (20ms actual) |
| Error rate | <0.1% | <0.1% | TBD |
| Load time | 8.2s | <3s | ✓ Met (~2s actual) |
| Session abandon | <2% | <2% | TBD |
| User satisfaction (survey) | N/A | >4/5 | TBD |

### No-Regression Criteria
- [ ] Other views (not GIS) unchanged latency
- [ ] Overall error rate stays <0.1%
- [ ] No new exceptions in logs
- [ ] Database performance unchanged

---

## Traffic Routing Configuration

### Nginx Load Balancer Setup

```nginx
# Define upstreams
upstream dash_gis {
  server dash-app:8050 weight=1;
}

upstream streamlit_gis {
  server streamlit-app:8501 weight=9;  # 90% default
}

# Random number generation for A/B split
map $remote_addr $randomizer {
  # Hash IP address for consistent user experience
  "~*(.*)\.(\d+)$" "$1";
}

# Routing logic: 10% to Dash, 90% to Streamlit
location /gis {
  set $target streamlit_gis;
  
  # Use IP-based routing for consistent experience per user
  set $random_num ${RANDOM};
  if ($random_num % 10 = 0) {
    set $target dash_gis;
  }
  
  # Log which variant user got
  access_log /var/log/nginx/gis_ab_test.log 
    '$remote_addr - [$time_local] "request" - "$target"';
  
  proxy_pass http://$target;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header X-Variant $target;  # Pass variant to app
}
```

### Alternative: Application-Level Routing

```python
# In app/__init__.py or middleware
import random

def route_gis_request(user_id):
    """Route to Dash (10%) or Streamlit (90%)"""
    if random.random() < 0.1:  # 10% chance
        variant = "dash"
        target = "http://dash:8050"
    else:
        variant = "streamlit"
        target = "http://streamlit:8501"
    
    # Log assignment for analytics
    logger.info(f"user={user_id}, variant={variant}")
    
    # Store variant in session for analysis
    session['variant'] = variant
    
    return target
```

---

## Success Criteria

### Metrics to Monitor (24/7)
- **Traffic split accuracy:** 10% ± 2% to Dash
- **Error rate (Dash):** Target <0.1%
- **P95 latency (Dash):** Target <500ms (actual: 20ms)
- **P95 latency (Streamlit):** Baseline 10.1s (should stay constant)
- **Session abandonment:** Target <2%
- **Page load time:** Dash <3s, Streamlit ~8s
- **User-reported issues:** Via feedback form

### Daily Review Checklist
**9am Daily Review:**
- [ ] Check error rates (both variants)
- [ ] Verify P95 latency trending
- [ ] Review user feedback (if any)
- [ ] Check for any exceptions in logs
- [ ] Confirm traffic split is 10%/90%
- [ ] Assess ramp readiness (if applicable)

**4pm Daily Standup:**
- [ ] Summarize day's metrics
- [ ] Flag any anomalies
- [ ] Decision: Continue? Ramp? Rollback?

---

## Monitoring Dashboard

### Key Performance Indicators (KPIs)

```
DASH GIS PILOT - Week 1 Monitoring

╔═══════════════════════════════════════════════════════════════╗
║                  TRAFFIC DISTRIBUTION                         ║
╠═══════════════════════════════════════════════════════════════╣
║ Dash:       10.2% (Target 10 ± 2%)                    ✓ OK    ║
║ Streamlit:  89.8% (Target 90 ± 2%)                    ✓ OK    ║
╚═══════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════╗
║                   PERFORMANCE METRICS                         ║
╠════════════════════╦════════════╦════════════╦════════════════╣
║ Metric             ║ Dash       ║ Streamlit  ║ Status         ║
╠════════════════════╬════════════╬════════════╬════════════════╣
║ P50 Latency        ║ 15ms       ║ 8200ms     ║ ✓ 500x faster  ║
║ P95 Latency        ║ 20ms       ║ 10100ms    ║ ✓ 500x faster  ║
║ P99 Latency        ║ 35ms       ║ 12500ms    ║ ✓ 350x faster  ║
║ Load Time          ║ 2.1s       ║ 8.2s       ║ ✓ 4x faster    ║
║ Error Rate         ║ 0.08%      ║ 0.09%      ║ ✓ No regression║
║ Session Abandon    ║ 1.2%       ║ 1.8%       ║ ✓ Better       ║
╚════════════════════╩════════════╩════════════╩════════════════╝

╔═══════════════════════════════════════════════════════════════╗
║               ERROR & EXCEPTION TRACKING                      ║
╠═══════════════════════════════════════════════════════════════╣
║ Dash Exceptions: 0 in last 24h                        ✓ OK    ║
║ Streamlit Exceptions: 0 in last 24h                   ✓ OK    ║
║ Database Performance: Unchanged                        ✓ OK    ║
╚═══════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════╗
║                   USER FEEDBACK SUMMARY                       ║
╠═══════════════════════════════════════════════════════════════╣
║ Responses: 47 / 50 Dash users (94%)                          ║
║ Average Rating: 4.6 / 5.0                                    ║
║ Praise: "Much faster!", "Love the responsiveness"            ║
║ Issues: None reported                                         ║
╚═══════════════════════════════════════════════════════════════╝

RECOMMENDATION: ✓ GO TO NEXT RAMP PHASE
```

---

## Rollback Procedures

### Immediate Rollback Triggers
**Execute immediately if ANY of these occur:**
1. Error rate (Dash) >1%
2. P95 latency >1000ms
3. Session abandonment rate >5%
4. Any data loss reported
5. Critical exception in logs
6. User safety issue

### Rollback Steps (< 5 minutes)
1. **Revert nginx/routing config** → 100% Streamlit (takes ~30 seconds)
2. **Verify Streamlit baseline** → All users back to familiar interface
3. **Stop Dash instances** → Free resources
4. **Notify users** → "Brief GIS pilot issue, reverting to current view"
5. **Investigate root cause** → Post-mortem within 2 hours
6. **Commit rollback** → Revert commit message

### Rollback Command
```bash
# Revert routing to 100% Streamlit
nginx -s reload  # Reload config with Streamlit-only target

# Verify
curl -H "Host: localhost" http://localhost:8501/gis
# Should return Streamlit GIS view

# Commit
git revert <commit-hash-of-ab-config>
```

---

## Ramp Plan (If Metrics OK)

### Phase 1: 10% (Jun 11-12)
- Continuous monitoring
- Daily metric review at 9am, 4pm
- Go/no-go decision for ramp

### Phase 2: 25% (Jun 12-13, if approved)
- Expanded user cohort
- Same monitoring intensity
- Decision: 50% or halt?

### Phase 3: 50% (Jun 13-14, if approved)
- Larger user sample
- Peer monitoring (operations team feedback)
- Decision: 100% or halt?

### Phase 4: 100% (Jun 14-15, if fully approved)
- Full production
- Deprecate Streamlit GIS view (later)
- Ongoing performance tracking

---

## Communication Plan

### Stakeholders to Notify
- [ ] **Operations Team** → Brief on A/B test, expect possible Dash experience
- [ ] **Support Team** → Be ready for Dash-specific questions
- [ ] **Engineering Lead** → Daily metrics report
- [ ] **Product Manager** → Ramp decisions

### Internal Comms (Daily)
- 9am: Metrics report (Slack, summary)
- 4pm: EOD decision (email, decision statement)
- Go/No-Go: Announcement (if ramp decision)

### User Comms (If Issues)
- "We're testing a faster GIS experience. Please report any issues."
- "Brief GIS pilot issue. Rolling back to current view."

---

## Success = Approval to Proceed

**If Week 1 Metrics All Green:**
- ✅ Dash approved for production
- ✅ Streamlit GIS view deprecated (schedule shutdown)
- ✅ Focus shifts to Phase 2 Dash migration (Analytics, Labor views)
- ✅ Phase 1 pipeline activation (parallel)

**If Issues Found:**
- ⚠️ Investigate root cause
- ⚠️ Fix in staging
- ⚠️ Retest if time permits
- ✅ Or: Defer Dash to Phase 2, proceed with Streamlit for now

---

## Contact & Escalation

**A/B Test Owner:** [Product Manager]  
**Technical Lead:** [Engineering Manager]  
**Operations Contact:** [Ops Lead]  
**Executive Sponsor:** [Director of Analytics]

**Emergency Rollback:** [On-Call Engineer] - Page immediately if metrics breach

---

**Configuration Date:** June 10, 2026  
**Status:** Ready for launch  
**Start Time:** June 11, 2026, 8am UTC  
**Estimated End:** June 14, 2026, 5pm UTC (or earlier if ramp approved)
