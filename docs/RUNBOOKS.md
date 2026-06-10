# NYC DOT Toolkit - Operational Runbooks

Critical procedures for operating the toolkit in production. All runbooks assume Docker Compose deployment.

## Table of Contents

1. [Daily Health Check](#daily-health-check)
2. [Emergency Restart](#emergency-restart)
3. [Backup Verification](#backup-verification)
4. [Restore from Backup](#restore-from-backup)
5. [Service Recovery](#service-recovery)
6. [Performance Investigation](#performance-investigation)
7. [Security Incident](#security-incident-response)
8. [Database Failover](#database-failover)
9. [Scaling Operations](#scaling-operations)

---

## Daily Health Check

**Frequency**: Once daily (8 AM recommended)  
**Duration**: 5 minutes  
**Owner**: DevOps / On-Call Engineer

### Procedure

#### Step 1: Check Container Status
```bash
# SSH to production server
ssh nycdot@prod-server.com

# Change to toolkit directory
cd /app/nyc_data

# Check all services are running
docker-compose ps

# Expected output:
# postgres          up (healthy)
# redis            up
# prometheus       up
# grafana          up
# api              up
# app              up (streamlit)
```

**✓ SUCCESS**: All containers show "Up"  
**✗ FAILURE**: Any container not running → See [Emergency Restart](#emergency-restart)

#### Step 2: Check Database Connectivity
```bash
# Test PostgreSQL connection
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "SELECT version();"

# Expected output:
# PostgreSQL 16.x ...
```

**✓ SUCCESS**: Version info displayed  
**✗ FAILURE**: Connection refused → See [Service Recovery](#service-recovery)

#### Step 3: Check API Health
```bash
# Test API endpoint
curl http://localhost:8000/health

# Expected output:
# {"status":"ok","timestamp":"2024-..."}
```

**✓ SUCCESS**: HTTP 200 with status ok  
**✗ FAILURE**: Connection refused or error → See [Service Recovery](#service-recovery)

#### Step 4: Check Dashboard Access
```bash
# Test Streamlit dashboard
curl -s http://localhost:8501 | grep -q "StreamlitPage" && echo "✓ Dashboard OK" || echo "✗ Dashboard failed"
```

**✓ SUCCESS**: Dashboard responds  
**✗ FAILURE**: No response → See [Service Recovery](#service-recovery)

#### Step 5: Verify Backup
```bash
# Check if backup ran in last 24 hours
LATEST_BACKUP=$(ls -t backups/sidewalk_db_*.sql.gz 2>/dev/null | head -1)
if [ -n "$LATEST_BACKUP" ]; then
    BACKUP_TIME=$(stat -c %y "$LATEST_BACKUP" | awk '{print $1}')
    echo "✓ Latest backup: $BACKUP_TIME"
else
    echo "✗ No backups found"
fi
```

**✓ SUCCESS**: Backup from today  
**✗ FAILURE**: Backup missing or old → See [Backup Verification](#backup-verification)

#### Step 6: Check Disk Space
```bash
# Check disk usage
df -h /

# Check backup directory size
du -sh backups/
```

**✓ SUCCESS**: Disk > 20% free  
**✗ FAILURE**: Disk < 10% free → Delete old backups or expand disk

#### Step 7: Check Grafana Dashboards
```bash
# Open browser (or check from office)
# Go to http://prod-server.com:3000
# Login: admin / (password from .env.socrata)
# Check dashboards for red alerts
```

**✓ SUCCESS**: No red alerts  
**✗ FAILURE**: Red alerts present → Investigate and page on-call engineer

### Summary Report

Create a daily checklist:
```
Daily Health Check - [DATE]
================================
☐ All containers running
☐ Database connectivity OK
☐ API responding
☐ Dashboard accessible
☐ Backup completed
☐ Disk space adequate
☐ No critical alerts
☐ Team notified of status

Time: _____ minutes
Issues: _____________
Actions taken: _____________
On-call engineer contacted: Y/N
```

---

## Emergency Restart

**Frequency**: As needed (unplanned service outages)  
**Duration**: 10-15 minutes  
**Owner**: DevOps / On-Call Engineer

### CRITICAL: Before restarting

⚠️ **DO NOT restart without**:
- Notifying team in Slack
- Checking if it's scheduled maintenance window
- Having backup completed in last 24 hours

### Procedure

#### Step 1: Assess the Situation
```bash
# What's the problem?
docker-compose logs -f --tail 50

# Which service is failing?
docker-compose ps

# How long has it been down?
# (Check timestamps in logs)
```

**Document**: Service name, error message, how long down

#### Step 2: Notify Stakeholders
```bash
# Post in Slack #nyc-dot-devops channel:
# "🚨 ALERT: [Service] is down
# Cause: [Brief description]
# ETA: 10 minutes to restart
# Will notify when restored
# Incident ID: [TIMESTAMP]"
```

#### Step 3: Perform Restart

**Option A: Restart specific service (if problem is isolated)**
```bash
# Example: Restart API only
docker-compose restart api

# Wait for it to start
docker-compose logs -f api &
sleep 10

# Test it
curl http://localhost:8000/health
```

**Option B: Restart all services (if widespread issue)**
```bash
# Full restart sequence
docker-compose down

# Wait for graceful shutdown
sleep 5

# Start all services
docker-compose up -d

# Monitor startup
docker-compose logs -f --tail 100 &
sleep 30

# Verify all are up
docker-compose ps
```

**Option C: Force restart (if service is hung)**
```bash
# Force kill service
docker-compose kill postgres  # Replace with service name

# Remove zombie container
docker rm nyc_data_postgres_1  # Replace with container name

# Restart
docker-compose up -d postgres

# Monitor
docker-compose logs -f postgres &
```

#### Step 4: Verify Service Recovery
```bash
# Run health check (see Daily Health Check above)
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "SELECT 1"
curl http://localhost:8000/health
curl -s http://localhost:8501 | grep -q "StreamlitPage" && echo "OK"
```

**✓ SUCCESS**: All tests pass

**✗ FAILURE**: Service still down → Continue to Step 5

#### Step 5: Check Logs for Root Cause
```bash
# View error logs
docker-compose logs postgres | tail -50
docker-compose logs api | tail -50
docker-compose logs app | tail -50

# Look for:
# - Out of disk space
# - Out of memory
# - Port conflicts
# - Permission denied
# - Database corruption
```

#### Step 6: If Still Failing

**Escalation path**:
1. Post detailed error in Slack #nyc-dot-devops
2. Page on-call engineer
3. Mention incident in #incidents channel
4. If database issue: Attempt restore from backup

#### Step 7: Post-Incident

When service is restored:
```bash
# Post recovery notification
# "✅ RESOLVED: [Service] is back online
# Downtime: X minutes
# Root cause: [Brief explanation]
# Prevention: [What we'll do to prevent recurrence]"

# Document:
# 1. Create incident ticket
# 2. Schedule postmortem
# 3. Add monitoring alert if needed
```

---

## Backup Verification

**Frequency**: Weekly (Sundays 3 AM)  
**Duration**: 20-30 minutes  
**Owner**: DevOps

### Procedure

#### Step 1: List Recent Backups
```bash
# Check backup directory
ls -lh backups/sidewalk_db_*.sql.gz | tail -5

# Show backup sizes and dates
du -h backups/sidewalk_db_*.sql.gz | tail -5
```

**✓ SUCCESS**: Multiple backups in last 7 days  
**✗ FAILURE**: Missing backups → Investigate backup script

#### Step 2: Verify Latest Backup
```bash
# Get file size
BACKUP_FILE=$(ls -t backups/sidewalk_db_*.sql.gz | head -1)
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Latest backup: $BACKUP_FILE ($FILE_SIZE)"

# File should be at least 1MB (typical)
if [ $(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE") -lt 1000000 ]; then
    echo "WARNING: Backup file seems too small"
fi
```

#### Step 3: Test Restore (on staging/test DB)
```bash
# Create test database
docker-compose exec postgres createdb -U dot_user test_restore_verification

# Test restore from backup
BACKUP_FILE=$(ls -t backups/sidewalk_db_*.sql.gz | head -1)
gunzip < "$BACKUP_FILE" | docker-compose exec -T postgres psql -U dot_user test_restore_verification

# Check if restore succeeded
docker-compose exec postgres psql -U dot_user test_restore_verification -c "SELECT COUNT(*) as total_records FROM sidewalk_inspections;" 

# Expected output should show a number (not zero if data exists)

# Cleanup
docker-compose exec postgres dropdb -U dot_user test_restore_verification
```

**✓ SUCCESS**: Restore completes without errors  
**✗ FAILURE**: Restore fails → Backup may be corrupted, escalate immediately

#### Step 4: Verify S3 Upload (if configured)
```bash
# Check S3 backups
aws s3 ls s3://nycdot-backups/postgres/ --recursive | tail -10

# Verify recent uploads
aws s3 ls s3://nycdot-backups/postgres/ | grep "$(date +%Y-%m-%d)"
```

**✓ SUCCESS**: Backups in S3 from today  
**✗ FAILURE**: Missing from S3 → Check AWS credentials and S3 permissions

#### Step 5: Report Status
```bash
# Update backup verification log
cat > backup_verification.log << EOF
Date: $(date)
Latest backup: $BACKUP_FILE
File size: $FILE_SIZE
Restore test: PASSED
S3 status: OK
Status: ✓ VERIFIED
EOF

# Email report to team
# Include: Backup count, sizes, restore success, S3 status
```

---

## Restore from Backup

**Frequency**: Emergency only  
**Duration**: 30-60 minutes  
**Owner**: Senior DBA / DevOps Lead

⚠️ **CRITICAL**: This procedure will overwrite current database

### Pre-Restoration Checklist

- [ ] Root cause of data loss identified
- [ ] Backup file integrity verified (restore test successful)
- [ ] Stakeholders notified
- [ ] Maintenance window scheduled
- [ ] Team assembled
- [ ] Current database backed up (as new baseline)

### Procedure

#### Step 1: Verify Backup Integrity
```bash
# Check backup file exists and is accessible
BACKUP_FILE="backups/sidewalk_db_20240511_020000.sql.gz"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found"
    exit 1
fi

# Verify file is not corrupted (test decompress)
gunzip -t "$BACKUP_FILE"
```

#### Step 2: Create Current Database Snapshot
```bash
# Before restoring, backup current state (in case of issues)
docker-compose exec postgres pg_dump -U dot_user sidewalk_db | gzip > backups/sidewalk_db_pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz
```

#### Step 3: Stop Application Access
```bash
# Stop Streamlit to prevent new writes
docker-compose stop app

# Stop API to prevent new writes
docker-compose stop api

# Keep database running
```

#### Step 4: Drop and Recreate Database
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U dot_user postgres

# In PostgreSQL prompt:
DROP DATABASE IF EXISTS sidewalk_db;
CREATE DATABASE sidewalk_db;

# Exit: \q
```

#### Step 5: Restore from Backup
```bash
# Restore database from backup
BACKUP_FILE="backups/sidewalk_db_20240511_020000.sql.gz"
gunzip < "$BACKUP_FILE" | docker-compose exec -T postgres psql -U dot_user sidewalk_db

# Monitor progress
# Should complete without errors
```

#### Step 6: Verify Restored Data
```bash
# Count records
docker-compose exec postgres psql -U dot_user sidewalk_db -c "
  SELECT 
    (SELECT COUNT(*) FROM sidewalk_inspections) as inspections,
    (SELECT COUNT(*) FROM repairs) as repairs,
    (SELECT COUNT(*) FROM contracts) as contracts,
    (SELECT COUNT(*) FROM schema_registry) as schemas;
"

# Should show non-zero counts if data exists
```

#### Step 7: Restart Application Services
```bash
# Restart API
docker-compose up -d api
sleep 10

# Restart Streamlit
docker-compose up -d app
sleep 10

# Verify they connect to database
docker-compose exec api curl http://localhost:8000/health
```

#### Step 8: Verify Data Integrity
```bash
# Run data validation queries
docker-compose exec postgres psql -U dot_user sidewalk_db -c "
  -- Check for any corrupted records
  SELECT * FROM sidewalk_inspections WHERE created_at > NOW() - INTERVAL '1 hour' LIMIT 5;
  
  -- Verify foreign key relationships
  SELECT COUNT(*) FROM repairs WHERE inspection_id NOT IN (SELECT id FROM sidewalk_inspections);
"

# Both should return 0 rows if data is good
```

#### Step 9: Notify Stakeholders
```bash
# Post in Slack:
# "✅ RESTORE COMPLETE
# Database restored to [timestamp]
# Data verified
# Services back online
# Users may resume operations
# Incident report: [link]"
```

#### Step 10: Post-Restoration Tasks
- [ ] Run full backup to create new baseline
- [ ] Schedule postmortem meeting
- [ ] Create ticket to prevent recurrence
- [ ] Update incident documentation

---

## Service Recovery

**Frequency**: As needed  
**Duration**: 15-30 minutes  
**Owner**: DevOps

Use this when a specific service is failing (not a full restart)

### Database Recovery

```bash
# Check if PostgreSQL is responsive
docker-compose exec postgres pg_isready -U dot_user

# If unresponsive, check logs
docker-compose logs postgres | tail -50

# Common issues:
# 1. Out of disk space
#    - Delete old backups: rm backups/*.sql.gz (keep recent ones)
#    - Check: df -h

# 2. Out of memory
#    - Check: docker stats
#    - Increase memory in docker-compose.yml

# 3. Connection pool exhausted
#    - See: SELECT COUNT(*) FROM pg_stat_activity;
#    - Kill long-running queries: SELECT pg_terminate_backend(pid);

# Restart if needed
docker-compose restart postgres
sleep 30
docker-compose exec postgres pg_isready -U dot_user
```

### API Recovery

```bash
# Check if API is responding
curl http://localhost:8000/health

# If not, check logs
docker-compose logs api | tail -50

# Restart if needed
docker-compose restart api
sleep 10

# Test
curl http://localhost:8000/health
```

### Dashboard Recovery

```bash
# Check if Streamlit is running
curl -s http://localhost:8501 | head -20

# If not, check logs
docker-compose logs app | tail -50

# Restart if needed
docker-compose restart app
sleep 10

# Test
curl -s http://localhost:8501 | grep -q Streamlit && echo "OK"
```

---

## Performance Investigation

**When**: API response times exceed 2 seconds  
**Duration**: 20-30 minutes  
**Owner**: DevOps / DBA

### Step 1: Check Current Performance
```bash
# Get recent query stats
docker-compose exec postgres psql -U dot_user sidewalk_db -c "
  SELECT 
    query,
    calls,
    mean_time,
    total_time
  FROM pg_stat_statements
  WHERE mean_time > 100
  ORDER BY mean_time DESC
  LIMIT 10;
"
```

### Step 2: Identify Bottleneck
```bash
# Is it database or application?

# Check database connections
docker-compose exec postgres psql -U dot_user sidewalk_db -c "SELECT COUNT(*) FROM pg_stat_activity;"

# Check API server load
docker stats api

# Check memory
docker-compose exec api free -h

# Check disk I/O
iostat -x 1 3
```

### Step 3: Optimize Query (if database issue)
```bash
# Add index for slow query
docker-compose exec postgres psql -U dot_user sidewalk_db -c "
  CREATE INDEX idx_inspections_borough ON sidewalk_inspections(borough);
  ANALYZE sidewalk_inspections;
"

# Verify improvement
# Re-run performance test
```

### Step 4: Scale Services (if API issue)
```bash
# In docker-compose.yml, add more API replicas:
#   api:
#     deploy:
#       replicas: 3

docker-compose up -d api
```

### Step 5: Monitor Improvement
```bash
# Run load test again
locust -f locustfile.py -u 10 -r 2 --run-time 5m
```

---

## Security Incident Response

**Severity**: CRITICAL  
**Duration**: Varies  
**Owner**: Security team + DBA

### Upon Detection of Breach/Incident

#### Immediate Actions (Next 15 minutes)

```bash
# 1. Alert team
# Slack: #incidents with CRITICAL tag
# Call: On-call security engineer

# 2. Assess severity
# - What data was accessed?
# - Was it encrypted?
# - How many records?
# - Any exfiltration?

# 3. Check audit logs
docker-compose exec postgres psql -U dot_user sidewalk_db -c "
  SELECT * FROM cdc_audit_log
  WHERE timestamp > NOW() - INTERVAL '1 hour'
  ORDER BY timestamp DESC;
"

# 4. Check access logs
docker-compose logs api | grep "error\|unauthorized\|denied"
```

#### Containment (Next 30 minutes)

```bash
# 1. Revoke compromised credentials
# Update .env.socrata with new passwords
POSTGRES_PASSWORD="new_secure_password_$(openssl rand -hex 16)"

# 2. Rotate API keys
# docker-compose exec postgres psql -U dot_user sidewalk_db
# UPDATE api_keys SET is_active = false WHERE created_before = NOW() - INTERVAL '1 day';

# 3. Isolate affected systems
# If specific user compromised:
# docker-compose down api  (temporary)

# 4. Take forensic backup
cp -r backups/ forensics/backup_$(date +%Y%m%d_%H%M%S)/
```

#### Investigation (Next 2-4 hours)

```bash
# 1. Detailed log analysis
docker-compose logs --since 3h > incident_logs.txt

# 2. Database audit trail
SELECT * FROM cdc_audit_log WHERE severity = 'critical';

# 3. Identify compromised records
SELECT * FROM sidewalk_inspections WHERE modified_date > [breach_date];

# 4. Document findings
# Create incident report template
# - What happened
# - How we detected it
# - Who was affected
# - What data was exposed
# - Root cause
# - Prevention measures
```

#### Recovery (Next 4-24 hours)

```bash
# 1. Reset all credentials
# 2. Force password change for all users
# 3. Audit all changes in past 24-48 hours
# 4. Restore to pre-incident state if needed
# 5. Deploy security patches
```

---

## Database Failover

**When**: Primary database is unavailable  
**Duration**: 5-10 minutes  
**Owner**: Senior DBA

For high-availability setup with replication:

```bash
# 1. Confirm primary is down
docker-compose exec postgres pg_isready -h postgres

# 2. Failover to replica
docker-compose exec replica psql -U dot_user -c "SELECT pg_promote();"

# 3. Update connection strings
# Edit docker-compose.yml to point API to new primary
#   POSTGRES_HOST: replica

# 4. Restart dependent services
docker-compose restart api
docker-compose restart app

# 5. Verify
docker-compose exec api curl http://localhost:8000/health
```

---

## Scaling Operations

**When**: Performance degrading or high load expected  
**Duration**: 30-60 minutes  
**Owner**: DevOps Lead

```bash
# 1. Identify bottleneck
docker stats

# 2. Scale appropriately
# Edit docker-compose.yml:
#   api:
#     deploy:
#       replicas: 5  (was 1)

# 3. Deploy new instances
docker-compose up -d api

# 4. Load balance traffic
# Configure Nginx or HAProxy

# 5. Monitor
docker-compose logs -f api

# 6. Verify
curl http://localhost:8000/health
```

---

## Contact Information

**On-Call Engineer**: [Rotation link]  
**Senior DBA**: [Contact]  
**Security Team**: [Channel/contact]  
**Management**: [Contact]  

---

**Last Updated**: 2026-05-11  
**Version**: 0.3.0  
**Status**: Production Ready
