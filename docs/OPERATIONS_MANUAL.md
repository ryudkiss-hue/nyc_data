# NYC DOT Sidewalk Data Governance Toolkit
## Complete Operations Manual

**Version**: 0.3.0  
**Last Updated**: 2026-05-11  
**Classification**: Internal Use  
**Document Owner**: DevOps Team  

---

# TABLE OF CONTENTS

1. [Executive Overview](#executive-overview)
2. [System Architecture](#system-architecture)
3. [Organizational Structure](#organizational-structure)
4. [Daily Operations](#daily-operations)
5. [Emergency Procedures](#emergency-procedures)
6. [Maintenance Schedule](#maintenance-schedule)
7. [Monitoring & Alerting](#monitoring--alerting)
8. [Backup & Recovery](#backup--recovery)
9. [Performance Baselines](#performance-baselines)
10. [Contact Information](#contact-information)

---

# EXECUTIVE OVERVIEW

## System Purpose

The NYC DOT Sidewalk Data Governance Toolkit is an enterprise data platform serving the Department of Transportation's Sidewalk Inspection & Management unit. It provides:

- **Data Collection**: Field inspections, repairs, contracts
- **Data Governance**: Schema validation, change tracking, audit trails
- **Analytics**: Real-time dashboards, compliance reporting, KPI tracking
- **Automation**: Workflow triggers, notification routing, document generation

## Key Metrics

```
┌─────────────────────────────────────────┐
│     SYSTEM HEALTH SCORECARD             │
├─────────────────────────────────────────┤
│ Availability Target:    99.5% (4h/month)│
│ Response Time Target:   < 2 seconds      │
│ Error Rate Target:      < 1%             │
│ Data Loss Risk:         < 1 day (backup) │
│ Recovery Time (RTO):    < 1 hour         │
│ Recovery Point (RPO):   < 24 hours       │
└─────────────────────────────────────────┘
```

## Service Tiers

```
┌─────────────────────────────────────────────────────┐
│ CRITICAL SERVICES (99.5% SLA)                       │
├─────────────────────────────────────────────────────┤
│ • PostgreSQL Database (data persistence)            │
│ • Data Governance Engine (compliance)               │
│ • Backup System (disaster recovery)                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ PRIMARY SERVICES (95% SLA)                          │
├─────────────────────────────────────────────────────┤
│ • REST API (programmatic access)                    │
│ • Streamlit Dashboard (user interface)              │
│ • Monitoring System (alerts)                        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ SUPPORTING SERVICES (90% SLA)                       │
├─────────────────────────────────────────────────────┤
│ • Prometheus (metrics collection)                   │
│ • Grafana (dashboards)                              │
│ • Jaeger (request tracing)                          │
└─────────────────────────────────────────────────────┘
```

---

# SYSTEM ARCHITECTURE

## High-Level Architecture

```
┌────────────────────────────────────────────────────────┐
│                   USERS & CLIENTS                      │
├────────────────────────────────────────────────────────┤
│  Field Staff  │  Analysts  │  Managers  │  Systems    │
└────────────┬───────────────┬──────────────┬────────────┘
             │               │              │
     ┌───────▼────────────────▼──────────────▼─────────┐
     │         PRESENTATION LAYER                       │
     ├────────────────────────────────────────────────┤
     │ • Streamlit Dashboard (http://host:8501)      │
     │ • REST API (http://host:8000)                 │
     │ • Power BI (direct DB connection)             │
     │ • Power Apps (mobile)                          │
     └──────────────┬─────────────────────────────────┘
                    │
     ┌──────────────▼─────────────────────────────────┐
     │      APPLICATION LAYER                         │
     ├────────────────────────────────────────────────┤
     │ • FastAPI Server (api.py)                      │
     │ • Streamlit App (app.py)                       │
     │ • CLI Tools (cli.py)                           │
     │ • Business Logic (analysis, reporting)         │
     └──────────────┬─────────────────────────────────┘
                    │
     ┌──────────────▼─────────────────────────────────┐
     │      GOVERNANCE LAYER                          │
     ├────────────────────────────────────────────────┤
     │ • Schema Registry (version control)            │
     │ • CDC Engine (change tracking)                 │
     │ • Lineage Core (data provenance)               │
     │ • Compliance Checker (design rules)            │
     │ • Audit Logger (event tracking)                │
     └──────────────┬─────────────────────────────────┘
                    │
     ┌──────────────▼─────────────────────────────────┐
     │      DATA LAYER                                │
     ├────────────────────────────────────────────────┤
     │ • PostgreSQL + PostGIS (primary data)          │
     │ • Redis (caching)                              │
     │ • Backup Storage (disaster recovery)           │
     └────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│          OBSERVABILITY & SUPPORT LAYER                 │
├────────────────────────────────────────────────────────┤
│ Prometheus → Grafana   │   Jaeger   │   Logs         │
└────────────────────────────────────────────────────────┘
```

## Network Diagram

```
                    ┌─ INTERNET ─┐
                    │             │
         ┌──────────┼─────────────┼──────────┐
         │          │             │          │
      [Users]   [Analytics]   [External]  [API]
         │          │             │          │
         └──────────┼─────────────┼──────────┘
                    │             │
              ┌─────▼─────────────▼────────┐
              │   NGINX REVERSE PROXY      │
              │ (HTTPS, SSL Termination)   │
              └─────┬─────────────┬────────┘
                    │             │
        ┌───────────┼─────────────┼───────────┐
        │           │             │           │
    ┌───▼──┐   ┌───▼───┐   ┌────▼───┐   ┌──▼──┐
    │ API  │   │Stream │   │Prom    │   │Gra  │
    │:8000 │   │:8501  │   │:9090   │   │:3000│
    └───┬──┘   └───┬───┘   └────┬───┘   └──┬──┘
        │          │            │          │
    ┌───▼──────────▼─────────────▼──────────▼────┐
    │        Docker Network (nyc_data)            │
    ├──────────────────────────────────────────┤
    │  • PostgreSQL:5432                        │
    │  • Redis:6379                             │
    │  • Prometheus:9090                        │
    │  • Grafana:3000                           │
    │  • Jaeger:16686                           │
    └──────────────────────────────────────────┘
```

## Container Stack

```
┌─────────────────────────────────────────────────────┐
│  DOCKER CONTAINERS (docker-compose.yml)             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  DATABASE TIER                                      │
│  ┌──────────────────┐  ┌──────────────────┐       │
│  │  postgres:16     │  │  redis:7         │       │
│  │  Port: 5432      │  │  Port: 6379      │       │
│  │  Status: Critical│  │  Status: Primary │       │
│  └──────────────────┘  └──────────────────┘       │
│                                                     │
│  APPLICATION TIER                                   │
│  ┌──────────────────────┐                         │
│  │  api (FastAPI)       │                         │
│  │  Port: 8000          │                         │
│  │  Replicas: 1 (scale to 3+)                    │
│  └──────────────────────┘                         │
│                                                     │
│  ┌──────────────────────┐                         │
│  │  app (Streamlit)     │                         │
│  │  Port: 8501          │                         │
│  │  Status: Primary UI  │                         │
│  └──────────────────────┘                         │
│                                                     │
│  MONITORING TIER                                    │
│  ┌──────────────────┐  ┌──────────────────┐       │
│  │  prometheus:9090 │  │  grafana:3000    │       │
│  │  (metrics)       │  │  (dashboards)    │       │
│  └──────────────────┘  └──────────────────┘       │
│                                                     │
│  ┌──────────────────────┐                         │
│  │  jaeger:16686        │                         │
│  │  (distributed trace) │                         │
│  └──────────────────────┘                         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

# ORGANIZATIONAL STRUCTURE

## Operations Team

```
                    ┌─────────────────┐
                    │ Operations Lead │
                    │  (Responsible)  │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
     ┌────▼────┐      ┌─────▼─────┐    ┌──────▼──────┐
     │ DevOps   │      │  Database │    │  Security   │
     │  Lead    │      │    Lead   │    │    Lead     │
     │ (Builds) │      │ (Governs) │    │ (Secures)   │
     └────┬────┘      └─────┬─────┘    └──────┬──────┘
          │                 │                  │
      [On-Call]         [On-Call]          [On-Call]
      Engineers         DBAs               Engineers
```

## On-Call Rotation

```
WEEK 1       WEEK 2       WEEK 3       WEEK 4
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ Alice  │  │ Bob    │  │ Carol  │  │ David  │
│ DevOps │  │ DevOps │  │  DBA   │  │  Sec   │
└────────┘  └────────┘  └────────┘  └────────┘
   24h         24h         24h         24h
  rotation    rotation    rotation    rotation
```

---

# DAILY OPERATIONS

## Startup Sequence (Morning)

```
START HERE
    │
    ▼
┌─────────────────────────────────┐
│ 1. VERIFY INFRASTRUCTURE (5 min) │
│    • Check all containers       │
│    • Verify database            │
│    • Check disk space           │
└─────────┬───────────────────────┘
          │
          ▼
   ✓ All Running?
    │     │
   YES   NO → See Emergency Procedures
    │
    ▼
┌──────────────────────────────────┐
│ 2. HEALTH CHECK (3 min)          │
│    • API responding              │
│    • Dashboard accessible        │
│    • Database connections OK     │
└─────────┬────────────────────────┘
          │
          ▼
   ✓ All Green?
    │     │
   YES   NO → See Service Recovery
    │
    ▼
┌──────────────────────────────────┐
│ 3. REVIEW ALERTS (2 min)         │
│    • Check Grafana dashboard     │
│    • Review overnight logs       │
│    • Look for warnings           │
└─────────┬────────────────────────┘
          │
          ▼
   ✓ Any Alerts?
    │     │
   YES   NO → Continue
    │        └─► READY FOR OPERATIONS
    │
    ▼
  [Address Alert]
    │
    ▼
┌──────────────────────────────────┐
│ 4. DOCUMENT & NOTIFY (1 min)     │
│    • Log incident if any         │
│    • Notify team if needed       │
│    • Update status board         │
└──────────────────────────────────┘
    │
    ▼
✓ READY FOR OPERATIONS
```

## Health Check Command

```bash
# Quick health check (2 minutes)
python launcher.py doctor

# Expected output:
✓ Python 3.x installed
✓ Docker installed
✓ All containers running
✓ PostgreSQL responding
✓ API health check passed
✓ Disk space adequate
✓ Memory available
✓ Network connectivity OK
```

## Daily Checklist

```
DATE: ____________    OPERATOR: ________________

☐ 8:00 AM - Infrastructure check
  • docker-compose ps (all should be "Up")
  • Disk space: df -h
  • Memory: free -h

☐ 8:05 AM - Health check
  • python launcher.py doctor
  • curl http://localhost:8000/health
  • curl http://localhost:8501 (no errors)

☐ 8:10 AM - Alert review
  • Check Grafana: http://localhost:3000
  • Review alert rules
  • Any RED items?

☐ 12:00 PM - Mid-day check
  • API response times normal?
  • Error rate < 1%?
  • Database connections healthy?

☐ 4:00 PM - Load check
  • Peak usage hours
  • Monitor resource usage
  • Check for slowdowns

☐ 5:00 PM - End of day summary
  • Any issues today?
  • Document for next shift
  • Update status board

ISSUES TODAY:
_____________________________________________
_____________________________________________

ACTIONS TAKEN:
_____________________________________________
_____________________________________________

SIGNATURE: ________________  TIME: __________
```

---

# EMERGENCY PROCEDURES

## Incident Response Flow

```
        INCIDENT DETECTED
                │
                ▼
    ┌───────────────────────┐
    │ 1. ASSESS SEVERITY    │
    │ (< 30 seconds)        │
    └────────┬──────────────┘
             │
    ┌────────▼──────────┐
    │ CRITICAL?         │
    │ (Users affected)  │
    └────┬────────┬─────┘
         │        │
        YES      NO
         │        │
         ▼        ▼
    [PAGE ONCALL] [LOG]
         │        │
         └────┬───┘
              ▼
    ┌───────────────────────┐
    │ 2. CONTAINMENT        │
    │ (< 5 minutes)         │
    │ • Isolate issue       │
    │ • Prevent spread      │
    │ • Preserve evidence   │
    └────────┬──────────────┘
             │
             ▼
    ┌───────────────────────┐
    │ 3. INVESTIGATION      │
    │ (< 30 minutes)        │
    │ • Check logs          │
    │ • Review metrics      │
    │ • Identify root cause │
    └────────┬──────────────┘
             │
             ▼
    ┌───────────────────────┐
    │ 4. RESOLUTION         │
    │ (< 60 minutes)        │
    │ • Implement fix       │
    │ • Verify fix works    │
    │ • Monitor metrics     │
    └────────┬──────────────┘
             │
             ▼
    ┌───────────────────────┐
    │ 5. NOTIFICATION       │
    │ (Immediate)           │
    │ • Notify users        │
    │ • Document incident   │
    │ • Schedule postmortem │
    └───────────────────────┘
```

## Emergency Contacts

```
┌─────────────────────────────────────────┐
│  EMERGENCY CONTACT TREE                 │
├─────────────────────────────────────────┤
│                                         │
│  LEVEL 1 (On-Call Engineer)             │
│  ├─ Name: ________________              │
│  ├─ Phone: _______________              │
│  └─ Email: _______________              │
│                                         │
│  LEVEL 2 (DevOps Lead)                  │
│  ├─ Name: ________________              │
│  ├─ Phone: _______________              │
│  └─ Email: _______________              │
│                                         │
│  LEVEL 3 (Database Lead)                │
│  ├─ Name: ________________              │
│  ├─ Phone: _______________              │
│  └─ Email: _______________              │
│                                         │
│  LEVEL 4 (Manager)                      │
│  ├─ Name: ________________              │
│  ├─ Phone: _______________              │
│  └─ Email: _______________              │
│                                         │
└─────────────────────────────────────────┘

ESCALATION TIMING:
  • No response in 5 min → Escalate to Level 2
  • No response in 10 min → Escalate to Level 3
  • No response in 15 min → Escalate to Level 4
```

---

# MAINTENANCE SCHEDULE

## Weekly Maintenance

```
MONDAY
├─ Database optimization (off-peak)
├─ Log rotation
└─ Review metrics summary

WEDNESDAY
├─ Backup verification
├─ Security patches check
└─ Performance tuning review

FRIDAY
├─ Capacity planning review
├─ Documentation updates
└─ Team sync meeting

SUNDAY (Scheduled Maintenance Window)
├─ Time: 2:00 AM - 4:00 AM
├─ Database vacuum and analyze
├─ Index optimization
├─ Full system health check
├─ Communicate any issues to team
└─ Document all changes
```

## Monthly Maintenance

```
MONTHLY SCHEDULE
┌──────────────────────────────────────┐
│ Week 1: Security                     │
│ • Dependency updates                 │
│ • Vulnerability scanning             │
│ • Secrets rotation                   │
│ • Certificate expiry check           │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ Week 2: Performance                  │
│ • Query optimization                 │
│ • Index analysis                     │
│ • Connection pool review             │
│ • Cache hit ratio analysis           │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ Week 3: Compliance                   │
│ • Audit log review                   │
│ • Access control verification        │
│ • Backup testing                     │
│ • DR procedure test                  │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ Week 4: Planning                     │
│ • Capacity forecast                  │
│ • Incident review                    │
│ • Team training                      │
│ • Documentation updates              │
└──────────────────────────────────────┘
```

---

# MONITORING & ALERTING

## Dashboard Overview

```
MAIN MONITORING DASHBOARD (Grafana)
┌────────────────────────────────────────┐
│ SYSTEM HEALTH AT A GLANCE              │
├────────────────────────────────────────┤
│                                        │
│ Database Status: ● GREEN               │
│ API Availability: ● GREEN              │
│ Memory Usage: ■■■■□□□□□□ 42%          │
│ Disk Usage: ■■■■■□□□□□ 58%             │
│ Network I/O: ■■□□□□□□□□ 18%            │
│                                        │
├────────────────────────────────────────┤
│ RESPONSE TIME (95th percentile)        │
│ Last Hour: 1.2 seconds                 │
│ Last 24h: 1.4 seconds                  │
│ Trend: ↓ IMPROVING                     │
│                                        │
├────────────────────────────────────────┤
│ ERROR RATE (last hour)                 │
│ API Errors: 0.3%                       │
│ Database Errors: 0%                    │
│ Total: 0.3% ✓ (< 1% target)           │
│                                        │
├────────────────────────────────────────┤
│ ACTIVE ALERTS                          │
│ Critical: 0                            │
│ Warnings: 2 (see below)                │
│                                        │
├────────────────────────────────────────┤
│ RECENT WARNINGS                        │
│ ⚠ High memory (85%)                   │
│ ⚠ Slow queries detected               │
│                                        │
└────────────────────────────────────────┘
```

## Alert Rules Summary

```
CRITICAL ALERTS (Page On-Call)
┌────────────────────────────────────┐
│ Database Down                      │
│ API Server Down                    │
│ High Error Rate (> 5%)            │
│ Backup Failed                      │
│ Disk Space Critical (< 5%)         │
│ Memory Critical (> 95%)            │
└────────────────────────────────────┘

WARNING ALERTS (Log + Email)
┌────────────────────────────────────┐
│ High Response Time (> 2 sec)       │
│ Error Rate Elevated (1-5%)         │
│ Slow Queries                       │
│ High Memory (> 85%)                │
│ Disk Space Warning (< 20%)         │
│ Connection Pool Exhausted          │
└────────────────────────────────────┘

INFO ALERTS (Log Only)
┌────────────────────────────────────┐
│ Scheduled Backup Starting          │
│ Service Restart                    │
│ Configuration Change               │
│ Cache Hit Ratio Low                │
└────────────────────────────────────┘
```

---

# BACKUP & RECOVERY

## Backup Schedule

```
BACKUP CADENCE
┌────────────────────────────────────┐
│ DAILY (Automated)                  │
│ • Time: 2:00 AM                    │
│ • Type: Full PostgreSQL Dump       │
│ • Compression: gzip                │
│ • Retention: 30 days               │
│ • Location: ./backups/ + S3        │
│ • Verification: Automatic          │
│ • Notification: On failure only    │
└────────────────────────────────────┘

WEEKLY (Manual Verification)
┌────────────────────────────────────┐
│ • Every Sunday 3:00 AM             │
│ • Test restore on staging DB       │
│ • Verify S3 copies                 │
│ • Document results                 │
└────────────────────────────────────┘

MONTHLY (Full DR Test)
┌────────────────────────────────────┐
│ • First Sunday of month            │
│ • Restore to new database          │
│ • Verify all tables                │
│ • Check referential integrity      │
│ • Document findings                │
└────────────────────────────────────┘
```

## Recovery Procedure

```
DATA LOSS DETECTED
       │
       ▼
ASSESS IMPACT
├─ What data is missing?
├─ When did loss occur?
├─ How many users affected?
└─ What is the severity?

       ▼
SELECT BACKUP
├─ Daily backups: ./backups/
├─ S3 backups: s3://bucket/postgres/
└─ Find backup before data loss

       ▼
RESTORE PROCEDURE
├─ 1. Create test database
├─ 2. Restore from backup
├─ 3. Verify data integrity
├─ 4. Compare with current
├─ 5. If OK: Swap databases
└─ 6. Notify users

       ▼
COMMUNICATION
├─ Notify team immediately
├─ Update status page
├─ Send user notification
├─ Explain what happened
└─ Commit recovery documentation

       ▼
POST-RECOVERY
├─ Run integrity checks
├─ Monitor for issues
├─ Schedule postmortem
├─ Implement preventive measures
└─ Document lessons learned
```

---

# PERFORMANCE BASELINES

## Expected Performance

```
┌────────────────────────────────────────────┐
│ RESPONSE TIME TARGETS                      │
├────────────────────────────────────────────┤
│                                            │
│ API Endpoint Latency:                      │
│ • Simple queries: < 100ms                  │
│ • Complex queries: < 500ms                 │
│ • Report generation: < 2 sec               │
│ • P95 latency: < 2 sec                     │
│ • P99 latency: < 5 sec                     │
│                                            │
├────────────────────────────────────────────┤
│ Dashboard Load Times:                      │
│ • Initial load: < 3 sec                    │
│ • Page navigation: < 1 sec                 │
│ • Data refresh: < 5 sec                    │
│                                            │
├────────────────────────────────────────────┤
│ Database Performance:                      │
│ • Query execution: < 500ms (95th %)       │
│ • Connection acquisition: < 10ms           │
│ • CDC processing: < 1 sec per event        │
│                                            │
└────────────────────────────────────────────┘
```

## Capacity Planning

```
CURRENT CAPACITY
┌────────────────────────────────────┐
│ Daily Records Processed:            │
│ • Inspections: 500-1000             │
│ • Repairs: 200-400                  │
│ • Changes: 5000-10000               │
│                                     │
│ Storage Used:                       │
│ • Database: ~10 GB                  │
│ • Backups: ~20 GB                   │
│ • Logs: ~5 GB                       │
│ • Total: ~35 GB (capacity: 500 GB) │
│                                     │
│ Scaling Headroom: 93% Available     │
└────────────────────────────────────┘

GROWTH PROJECTION (Year 1)
┌────────────────────────────────────┐
│ Month   │ Inspections │ Storage    │
├─────────┼─────────────┼────────────┤
│ Current │ 500-1000    │ 35 GB      │
│ +3 mo   │ 750-1500    │ 45 GB      │
│ +6 mo   │ 1000-2000   │ 60 GB      │
│ +9 mo   │ 1250-2500   │ 80 GB      │
│ +12 mo  │ 1500-3000   │ 100 GB     │
│                                     │
│ Scaling Action: ~200 GB mark       │
│ Recommendation: Add storage/scale  │
└────────────────────────────────────┘
```

---

# CONTACT INFORMATION

## Team Directory

```
┌─────────────────────────────────────────────────────┐
│ OPERATIONS TEAM                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Operations Lead                                     │
│ Name: _________________________                      │
│ Email: ___________________@nycdot.gov               │
│ Phone: (212) ___-____                              │
│ Availability: Mon-Fri 8AM-6PM                       │
│                                                     │
│ DevOps Engineer (On-Call)                           │
│ Name: _________________________                      │
│ Email: ___________________@nycdot.gov               │
│ Phone: (212) ___-____                              │
│ Availability: 24/7 (rotation)                       │
│                                                     │
│ Database Administrator                              │
│ Name: _________________________                      │
│ Email: ___________________@nycdot.gov               │
│ Phone: (212) ___-____                              │
│ Availability: Mon-Fri 8AM-6PM                       │
│                                                     │
│ Security Engineer                                   │
│ Name: _________________________                      │
│ Email: ___________________@nycdot.gov               │
│ Phone: (212) ___-____                              │
│ Availability: Mon-Fri 8AM-5PM                       │
│                                                     │
│ Project Manager                                     │
│ Name: _________________________                      │
│ Email: ___________________@nycdot.gov               │
│ Phone: (212) ___-____                              │
│ Availability: Mon-Fri 9AM-5PM                       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## External Contacts

```
┌─────────────────────────────────────────────────────┐
│ VENDOR & EXTERNAL CONTACTS                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│ AWS Support (if cloud-hosted)                       │
│ • Account ID: __________________                    │
│ • Support Level: Business/Enterprise                │
│ • Phone: 1-800-XXX-XXXX                             │
│ • Portal: https://console.aws.amazon.com/support/   │
│                                                     │
│ Docker Support                                      │
│ • Account: ____________________                     │
│ • Portal: https://support.docker.com                │
│                                                     │
│ PostgreSQL Community                                │
│ • Forum: https://www.postgresql.org/support/        │
│ • Mailing List: pgsql-general@postgresql.org        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Escalation Procedure

```
INCIDENT ESCALATION MATRIX

SEVERITY: Critical (Users completely unable to work)
TIME: Immediate
ACTION: PAGE ON-CALL ENGINEER
         ├─ Call immediately
         ├─ Page via alerting system
         └─ Alert Operations Lead

SEVERITY: High (Major feature unavailable)
TIME: 5 minutes
ACTION: If no response from on-call
         ├─ Page DevOps Lead
         ├─ Alert Operations Manager
         └─ Prepare incident comms

SEVERITY: Medium (Degraded performance)
TIME: 15 minutes
ACTION: If no progress
         ├─ Escalate to database lead
         ├─ Consider maintenance window
         └─ Update status page

SEVERITY: Low (Minor issues, users working around it)
TIME: 1 hour
ACTION: Log for next review
         ├─ Schedule for maintenance window
         ├─ Plan fix
         └─ Monitor for escalation
```

---

# APPENDIX: QUICK REFERENCE

## Essential Commands

```bash
# Health Check
docker-compose ps
python launcher.py doctor

# Backup
scripts/backup_postgres.sh

# View Logs
docker-compose logs -f postgres
docker-compose logs -f api
docker-compose logs -f app

# Restart Services
docker-compose restart postgres
docker-compose restart api
docker-compose restart app

# Access Database
docker-compose exec postgres psql -U dot_user -d sidewalk_db

# Check Metrics
curl http://localhost:9090/api/v1/rules
curl http://localhost:3000/api/dashboards
```

## Important Endpoints

```
API:        http://localhost:8000/docs
Dashboard:  http://localhost:8501
Prometheus: http://localhost:9090
Grafana:    http://localhost:3000 (admin/admin)
Jaeger:     http://localhost:16686
```

## Key Files

```
Configuration: .env.socrata
Docker Stack:  docker-compose.yml
Backups:       ./backups/
Logs:          docker-compose logs
Metrics:       http://localhost:9090 (Prometheus)
Dashboards:    http://localhost:3000 (Grafana)
```

---

**END OF OPERATIONS MANUAL**

*Printed: ____________  By: ____________  Reviewed By: ____________*

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-11 | DevOps | Initial release |
| | | | |
| | | | |

---

**CONFIDENTIAL - INTERNAL USE ONLY**  
©2026 NYC Department of Transportation  
All Rights Reserved
