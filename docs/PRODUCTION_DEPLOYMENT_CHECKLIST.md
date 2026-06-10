# NYC DOT Toolkit - Production Deployment Checklist

Complete step-by-step guide to take the toolkit from current state to production-ready deployment.

## Executive Summary

**Current Status**: 80% code-ready, 20% operational procedures needed

**Effort Required**: 2-3 weeks of implementation work

**Timeline**:
- Week 1: Testing, backups, monitoring
- Week 2: Security, runbooks, final testing
- Week 3: Deployment and go-live

---

## Week 1: Critical Infrastructure

### Day 1: Test Verification

**Goal**: Ensure all code passes tests with >70% coverage

#### Tasks

- [ ] Make test verification script executable
  ```bash
  chmod +x scripts/test_verification.sh
  ```

- [ ] Run test verification
  ```bash
  ./scripts/test_verification.sh
  ```

- [ ] Review test results
  - Check `test_results.txt` for failures
  - Review `htmlcov/index.html` for coverage gaps
  - Document any failures

- [ ] Fix failing tests
  ```bash
  # For each failure:
  # 1. Understand the failure
  # 2. Fix the code
  # 3. Re-run that specific test
  pytest tests/test_name.py -v
  ```

- [ ] Commit passing tests
  ```bash
  git add -A
  git commit -m "Test verification complete - all tests passing with [XX]% coverage"
  ```

**Success Criteria**:
- ✅ All tests passing
- ✅ Coverage >= 70%
- ✅ Test results committed to git

---

### Day 2-3: Backup Automation

**Goal**: Set up automated daily backups with verification

#### Tasks

- [ ] Make backup script executable
  ```bash
  chmod +x scripts/backup_postgres.sh
  ```

- [ ] Create backups directory
  ```bash
  mkdir -p backups
  ```

- [ ] Test backup script manually
  ```bash
  # Test on local Docker setup
  DOCKER_COMPOSE_PATH=. ./scripts/backup_postgres.sh
  ```

- [ ] Verify backup was created
  ```bash
  ls -lh backups/sidewalk_db_*.sql.gz
  ```

- [ ] Test restore from backup (verify it works)
  ```bash
  # Create test database
  docker-compose exec postgres createdb -U dot_user test_restore
  
  # Restore backup
  BACKUP_FILE=$(ls -t backups/sidewalk_db_*.sql.gz | head -1)
  gunzip < "$BACKUP_FILE" | docker-compose exec -T postgres psql -U dot_user test_restore
  
  # Verify data
  docker-compose exec postgres psql -U dot_user test_restore -c "SELECT COUNT(*) FROM sidewalk_inspections;"
  
  # Cleanup
  docker-compose exec postgres dropdb -U dot_user test_restore
  ```

- [ ] Schedule automated daily backups

  **Linux/MacOS**: Add to crontab
  ```bash
  crontab -e
  
  # Add this line (2 AM daily):
  0 2 * * * cd /app/nyc_data && DOCKER_COMPOSE_PATH=. ./scripts/backup_postgres.sh >> /var/log/nyc_dot_backup.log 2>&1
  ```

  **Windows**: Add to Task Scheduler
  ```
  Create Basic Task:
  Name: NYC DOT Backup
  Trigger: Daily at 2:00 AM
  Action: Run script C:\nyc_data\scripts\backup_postgres.ps1
  ```

- [ ] Create backup verification script to run weekly
  ```bash
  chmod +x scripts/backup_postgres.sh
  
  # Add to crontab (Sunday 3 AM):
  0 3 * * 0 VERIFY_BACKUP=true DOCKER_COMPOSE_PATH=/app/nyc_data /app/nyc_data/scripts/backup_postgres.sh
  ```

**Success Criteria**:
- ✅ Backup script runs successfully
- ✅ Backup file created and compressed
- ✅ Restore test passes
- ✅ Scheduled daily backups configured
- ✅ Recent backups exist (if applying to existing system)

---

### Day 4-5: Monitoring & Alerts

**Goal**: Enable Prometheus monitoring and Grafana alerting

#### Tasks

- [ ] Review alert rules
  ```bash
  cat docker/prometheus/rules/alerts.yml
  ```

- [ ] Update docker-compose.yml to include alert rules
  ```bash
  # In prometheus service, add:
  # volumes:
  #   - ./docker/prometheus/rules/alerts.yml:/etc/prometheus/rules/alerts.yml
  ```

- [ ] Restart Prometheus to load rules
  ```bash
  docker-compose restart prometheus
  ```

- [ ] Access Prometheus UI
  ```
  http://localhost:9090/alerts
  ```

- [ ] Verify alerts are loaded
  - Should see ~30 alert rules
  - Status should show "Pending" or "Firing"

- [ ] Configure Grafana alerting
  - Login to Grafana: http://localhost:3000
  - Go to Alerting → Notification Channels
  - Add notification channel (Teams/email/Slack)
  - Configure contact details

- [ ] Test alert channel
  ```bash
  # Trigger test alert (optional)
  # Or test by sending test notification from Grafana
  ```

- [ ] Create Grafana dashboard for key metrics
  - Add panels for:
    - API response times (histogram_quantile 95th percentile)
    - Error rate (requests with 5xx status)
    - Database connections
    - Disk usage
    - Memory usage
    - Backup status

**Success Criteria**:
- ✅ Alert rules loaded in Prometheus
- ✅ Grafana notification channel configured
- ✅ Dashboard created with key metrics
- ✅ Test alert sent successfully

---

## Week 2: Security & Operations

### Day 6: Secrets Management

**Goal**: Move from plaintext .env to vault-based secrets

**Choose ONE approach** (HashiCorp Vault recommended):

#### Option A: HashiCorp Vault (Recommended)

```bash
# 1. Install Vault (development mode for testing)
# https://www.vaultproject.io/downloads

# 2. Start Vault in background
vault server -dev &

# 3. Export environment variables
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='s.xxxxx'  # From output above

# 4. Store secrets
vault kv put secret/nycdot/postgres \
  username="dot_user" \
  password="$(openssl rand -hex 16)"

vault kv put secret/nycdot/socrata \
  api_token="your_socrata_token"

# 5. Update launcher.py to read from Vault
# (Code provided in docs/SECURITY_AND_PACKAGING.md)

# 6. Test secret retrieval
vault kv get secret/nycdot/postgres
```

#### Option B: AWS Secrets Manager

```bash
# 1. Configure AWS credentials
aws configure

# 2. Create secret
aws secretsmanager create-secret \
  --name nyc_dot/postgres \
  --secret-string '{"username":"dot_user","password":"secure_password"}'

# 3. Update launcher.py (code in docs/SECURITY_AND_PACKAGING.md)
```

#### Option C: Azure Key Vault

```bash
# 1. Create vault
az keyvault create --name nycdot-vault --resource-group nycdot

# 2. Add secrets
az keyvault secret set --vault-name nycdot-vault --name postgres-password

# 3. Update launcher.py (code in docs/SECURITY_AND_PACKAGING.md)
```

**Verification**:
- [ ] Secrets stored in chosen vault
- [ ] launcher.py reads from vault
- [ ] .env.socrata removed from production (or contains vault address only)
- [ ] No plaintext passwords in git
- [ ] Secret access logged

---

### Day 7: SSL/TLS Configuration

**Goal**: Enable HTTPS for all external connections

#### Tasks

- [ ] Make SSL setup script executable
  ```bash
  chmod +x scripts/setup_ssl.sh
  ```

- [ ] Run SSL setup
  ```bash
  ./scripts/setup_ssl.sh
  ```

- [ ] Choose certificate type:
  - **Development**: Self-signed (option 1)
  - **Production**: Let's Encrypt (option 2)
  - **Enterprise**: Your CA (option 3)

- [ ] Verify certificate
  ```bash
  openssl x509 -in certs/server.crt -text -noout
  ```

- [ ] Uncomment Nginx service in docker-compose.yml
  ```yaml
  nginx:
    image: nginx:latest
    container_name: nyc_data_nginx
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./certs:/etc/nginx/certs:ro
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - api
      - app
    networks:
      - nyc_data
  ```

- [ ] Start Nginx
  ```bash
  docker-compose up -d nginx
  ```

- [ ] Test HTTPS access
  ```bash
  curl -k https://localhost/  # Self-signed
  # OR
  curl https://yourdomain.com/  # Let's Encrypt
  ```

- [ ] Configure certificate auto-renewal (Let's Encrypt)
  ```bash
  # Add to crontab (3 AM daily):
  0 3 * * * certbot renew --quiet
  ```

**Success Criteria**:
- ✅ Certificate files in certs/
- ✅ Nginx running and serving HTTPS
- ✅ HTTP redirects to HTTPS
- ✅ Certificate renewal configured (if Let's Encrypt)
- ✅ SSL Labs score A+ (production)

---

### Day 8-9: Operational Runbooks

**Goal**: Document all operational procedures

#### Tasks

- [ ] Review runbooks file
  ```bash
  cat docs/RUNBOOKS.md
  ```

- [ ] Create runbook copies for your environment
  ```bash
  cp docs/RUNBOOKS.md runbooks_nyc_dot.md
  ```

- [ ] Customize for your environment:
  - [ ] Update server names/IPs
  - [ ] Update on-call contact information
  - [ ] Update Slack channels
  - [ ] Add team-specific procedures
  - [ ] Add escalation procedures

- [ ] Test critical procedures:
  - [ ] Daily Health Check (do it live)
  - [ ] Backup Verification (run weekly test)
  - [ ] Restore from Backup (test on staging)
  - [ ] Emergency Restart (test without going live)

- [ ] Post runbooks in accessible location:
  - [ ] Share in team wiki/confluence
  - [ ] Print copies for war room
  - [ ] Add to on-call documentation
  - [ ] Email to team

- [ ] Train team on runbooks
  - [ ] Walk through each procedure
  - [ ] Discuss when to use each
  - [ ] Answer questions
  - [ ] Assign on-call responsibilities

**Success Criteria**:
- ✅ Customized runbooks exist
- ✅ Team trained on procedures
- ✅ Procedures tested on non-prod
- ✅ On-call rotation established
- ✅ Escalation contacts documented

---

## Week 3: Final Testing & Deployment

### Day 10-11: Performance Testing

**Goal**: Establish baseline and ensure system can handle expected load

#### Tasks

- [ ] Install load testing tool
  ```bash
  pip install locust
  ```

- [ ] Create performance test file
  ```bash
  cat > locustfile.py << 'EOF'
  from locust import HttpUser, task, between
  
  class APIUser(HttpUser):
      wait_time = between(1, 3)
      
      @task(3)
      def list_datasets(self):
          self.client.get("/api/datasets")
      
      @task(1)
      def get_inspections(self):
          self.client.get("/api/inspections?limit=100")
  
  class DashboardUser(HttpUser):
      wait_time = between(2, 5)
      
      @task
      def load_dashboard(self):
          self.client.get("/")
  EOF
  ```

- [ ] Run performance test with increasing load
  ```bash
  # Small test (10 users, 2/s ramp)
  locust -f locustfile.py -u 10 -r 2 --run-time 5m
  
  # Medium test (50 users)
  locust -f locustfile.py -u 50 -r 5 --run-time 10m
  
  # Large test (100 users - only if you expect this)
  locust -f locustfile.py -u 100 -r 10 --run-time 10m
  ```

- [ ] Document baseline metrics
  ```
  Load Test Results - [DATE]
  ========================
  
  10 Users:
  - Average response time: ___ ms
  - 95th percentile: ___ ms
  - 99th percentile: ___ ms
  - Error rate: ___ %
  - Requests/second: ___
  
  50 Users:
  - [same metrics]
  
  100 Users:
  - [same metrics]
  
  Bottleneck identified: ___________
  Recommended scaling: ___________
  ```

- [ ] Identify and document bottlenecks
  - Is it database?
  - Is it API server?
  - Is it memory/CPU?

- [ ] Optimize if needed
  ```bash
  # Add database indexes for slow queries
  docker-compose exec postgres psql -U dot_user sidewalk_db -c "
    CREATE INDEX idx_inspections_borough ON sidewalk_inspections(borough);
    ANALYZE sidewalk_inspections;
  "
  
  # Re-run test to verify improvement
  ```

**Success Criteria**:
- ✅ Performance baseline established
- ✅ All response times < 2 seconds
- ✅ Error rate < 1%
- ✅ No memory leaks detected
- ✅ Scaling plan documented

---

### Day 12: Compliance Review

**Goal**: Verify all security and compliance requirements met

#### Checklist

**Security**:
- [ ] All passwords in vault (not .env)
- [ ] HTTPS enabled
- [ ] TLS 1.2+ only
- [ ] Security headers set (X-Frame-Options, etc.)
- [ ] Input validation enabled
- [ ] SQL injection prevention active
- [ ] Rate limiting configured
- [ ] Audit logging enabled

**Operations**:
- [ ] Daily backups automated
- [ ] Backup restoration tested
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Runbooks written
- [ ] On-call rotation established
- [ ] Incident response plan documented

**Data Protection**:
- [ ] Data encryption at rest (pgcrypto)
- [ ] CDC audit logging working
- [ ] Data lineage tracking enabled
- [ ] Compliance rules enforced
- [ ] Access controls implemented
- [ ] PII handling documented

**Compliance (if applicable)**:
- [ ] HIPAA compliance verified (if needed)
- [ ] GDPR compliance verified (if needed)
- [ ] Data retention policies configured
- [ ] Right to be forgotten procedures documented
- [ ] Privacy impact assessment completed

**Documentation**:
- [ ] API documentation complete
- [ ] User guide written
- [ ] Deployment guide completed
- [ ] Troubleshooting guide provided
- [ ] Runbooks completed

#### Sign-Off

Create compliance sign-off document:
```
COMPLIANCE SIGN-OFF
===================

System: NYC DOT Sidewalk Toolkit
Version: 0.3.0
Date: [Date]

Security Review:     ☐ PASS  ☐ FAIL  Reviewer: ________
Operations Review:   ☐ PASS  ☐ FAIL  Reviewer: ________
Compliance Review:   ☐ PASS  ☐ FAIL  Reviewer: ________
Performance Review:  ☐ PASS  ☐ FAIL  Reviewer: ________

Issues/Exceptions:
[List any items not meeting criteria and remediation plan]

Approved for production:
Date: __________
Approver: __________
```

---

### Day 13: Rehearsal Deployment

**Goal**: Practice deployment procedure without going live

#### Tasks

- [ ] Deploy to staging environment (if available)
  ```bash
  # On staging server:
  git clone [repo]
  cd nyc_data
  python launcher.py setup all
  python launcher.py docker up
  ```

- [ ] Verify all services running
  ```bash
  python launcher.py doctor
  docker-compose ps
  ```

- [ ] Run health check
  ```bash
  # See docs/RUNBOOKS.md - Daily Health Check section
  ```

- [ ] Run data validation
  ```bash
  docker-compose exec postgres psql -U dot_user sidewalk_db -c "
    SELECT COUNT(*) FROM sidewalk_inspections;
    SELECT COUNT(*) FROM repairs;
    SELECT COUNT(*) FROM contracts;
  "
  ```

- [ ] Test backup/restore
  ```bash
  scripts/backup_postgres.sh
  # [Wait for completion]
  # Test restore (don't actually restore, just verify backup works)
  ```

- [ ] Create deployment runbook
  ```
  NYC DOT Toolkit - Production Deployment Runbook
  
  Pre-Deployment:
  [ ] Get approvals
  [ ] Schedule maintenance window
  [ ] Notify stakeholders
  [ ] Create pre-deployment backup
  [ ] Brief ops team
  
  Deployment:
  [ ] Checkout code: git clone ...
  [ ] Run setup: python launcher.py setup all
  [ ] Start services: python launcher.py docker up
  [ ] Run health check
  [ ] Run data validation
  [ ] Monitor logs for 10 minutes
  
  Post-Deployment:
  [ ] Verify all users can access
  [ ] Test critical workflows
  [ ] Monitor metrics for 1 hour
  [ ] Post deployment summary
  [ ] Schedule postmortem if issues
  ```

**Success Criteria**:
- ✅ Deployment completed successfully
- ✅ All services operational
- ✅ Data integrity verified
- ✅ Deployment runbook tested
- ✅ Team confident in procedure

---

### Day 14: Production Deployment

**Goal**: Deploy to production

#### Pre-Deployment

- [ ] Final approvals obtained
- [ ] Maintenance window scheduled
- [ ] All stakeholders notified
- [ ] Backup completed
- [ ] On-call engineer standing by
- [ ] Runbook reviewed with team

#### Deployment Steps

1. **Notification** (30 minutes before)
   ```
   Slack: "Production deployment starting in 30 minutes
   System: NYC DOT Toolkit
   Maintenance window: [start] - [end]
   Expected downtime: 15 minutes
   Updates required: None for users
   Questions: Contact [on-call engineer]"
   ```

2. **Backup Current State**
   ```bash
   scripts/backup_postgres.sh
   # Wait for completion
   ```

3. **Deploy Code**
   ```bash
   cd /app/nyc_data
   git pull origin main
   ```

4. **Start Services**
   ```bash
   python launcher.py setup all
   python launcher.py docker up
   ```

5. **Health Checks**
   ```bash
   python launcher.py doctor
   # See docs/RUNBOOKS.md - Daily Health Check
   ```

6. **Data Validation**
   ```bash
   docker-compose exec postgres psql -U dot_user sidewalk_db -c "
     SELECT COUNT(*) FROM sidewalk_inspections;
   "
   ```

7. **Service Verification** (5-10 minutes)
   ```bash
   curl -k https://yourdomain/api/datasets
   # Should return data
   ```

8. **Team Notification**
   ```
   Slack: "✅ DEPLOYMENT COMPLETE
   All services operational
   Monitoring active
   Users can resume operations"
   ```

9. **Post-Deployment Monitoring**
   - [ ] Monitor Grafana for 1 hour
   - [ ] Check error rates (should be < 1%)
   - [ ] Monitor response times (should be < 2s)
   - [ ] Watch for any alerts
   - [ ] Respond to user issues immediately

#### Post-Deployment

- [ ] Create deployment ticket documenting:
  - What was deployed
  - When it was deployed
  - Who approved it
  - Any issues encountered
  - Resolution

- [ ] Schedule postmortem if any issues occurred

- [ ] Communicate success to stakeholders

**Success Criteria**:
- ✅ All services running in production
- ✅ Users can access system
- ✅ No critical errors in logs
- ✅ Monitoring showing healthy metrics
- ✅ Team confident in operations

---

## Post-Deployment Tasks

### Ongoing (First Month)

- [ ] **Daily**: Run health check (see Runbooks)
- [ ] **Weekly**: Verify backups
- [ ] **Weekly**: Review error logs
- [ ] **Weekly**: Check performance metrics
- [ ] **Monthly**: Capacity review
- [ ] **Monthly**: Update runbooks with lessons learned
- [ ] **Monthly**: Disaster recovery test

### Continuous Improvement

- [ ] Monitor error rates and address root causes
- [ ] Optimize slow queries
- [ ] Adjust alert thresholds based on actual usage
- [ ] Document operational issues and resolutions
- [ ] Schedule team training updates
- [ ] Plan for scaling if needed

---

## Troubleshooting During Deployment

### If Tests Fail

See `docs/PRODUCTION_GAPS.md` for detailed troubleshooting

### If Backup Fails

```bash
# Check backup logs
tail -50 /var/log/nyc_dot_backup.log

# Test backup manually
DOCKER_COMPOSE_PATH=. ./scripts/backup_postgres.sh

# Check disk space
df -h
```

### If Services Won't Start

```bash
# Check logs
docker-compose logs -f

# Check resource usage
docker stats

# Restart individual service
docker-compose restart postgres
```

### If Performance is Poor

```bash
# See docs/RUNBOOKS.md - Performance Investigation section
docker-compose exec postgres psql -U dot_user sidewalk_db -c "
  SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
"
```

---

## Success Criteria - Production Ready

When you can check all these boxes, you're ready for production:

### Testing
- ✅ All tests passing
- ✅ Coverage >= 70%
- ✅ Performance baselines established

### Backups
- ✅ Automated daily backups
- ✅ Restore process tested
- ✅ Backup retention configured

### Monitoring
- ✅ Alert rules configured
- ✅ Notification channel active
- ✅ Dashboard with key metrics

### Security
- ✅ Secrets in vault (not .env)
- ✅ HTTPS/TLS enabled
- ✅ Audit logging active
- ✅ Access controls enforced

### Operations
- ✅ Runbooks written and tested
- ✅ Team trained
- ✅ On-call rotation established
- ✅ Escalation procedures documented

### Documentation
- ✅ Deployment procedure documented
- ✅ Troubleshooting guide complete
- ✅ API documentation updated
- ✅ User guide provided

### Compliance
- ✅ Security review passed
- ✅ Compliance review passed
- ✅ Sign-offs obtained
- ✅ Data retention policies configured

---

## Support Resources

| Need | Resource |
|------|----------|
| Test failures | docs/PRODUCTION_GAPS.md |
| Backup help | scripts/backup_postgres.sh (comments) |
| Monitoring setup | docker/prometheus/rules/alerts.yml |
| Operational procedures | docs/RUNBOOKS.md |
| Security questions | docs/SECURITY_AND_PACKAGING.md |
| Deployment help | docs/DEPLOYMENT_GUIDE.md |

---

**Start Date**: [Your start date]  
**Target Production Date**: [3 weeks from start]  
**Deployment Lead**: [Your name]  
**On-Call Engineer**: [Name]  
**Status**: Ready to Begin

---

## Questions?

Contact:
- **Technical Lead**: [Name/email]
- **DevOps Lead**: [Name/email]
- **Security**: [Name/email]
- **Management**: [Name/email]

Good luck! You've got this. 🚀
