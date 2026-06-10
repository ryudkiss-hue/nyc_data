# Production Deployment Playbook - NYC Sidewalk Toolkit

Complete step-by-step guide for deploying the NYC Sidewalk Toolkit to production on AWS with full monitoring, SSL, and CI/CD automation.

## Deployment Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1: Planning** | Day 1 | AWS account setup, domain registration, IAM configuration |
| **Phase 2: Infrastructure** | Days 2-3 | VPC, RDS, ElastiCache, ECR, ALB setup |
| **Phase 3: Application** | Days 4-5 | Docker images, ECS deployment, Nginx configuration |
| **Phase 4: Security** | Day 6 | SSL/TLS, secrets management, security groups |
| **Phase 5: Automation** | Day 7 | CI/CD pipelines, monitoring, auto-scaling |
| **Phase 6: Testing** | Day 8 | Load testing, failover testing, security audits |
| **Phase 7: Launch** | Day 9 | DNS cutover, monitoring, runbooks |

## Phase 1: Planning & Setup (Day 1)

### 1.1 AWS Account Preparation

```bash
# Create AWS account if needed
# https://aws.amazon.com/console/

# Set up IAM root user
aws configure
# Enter: AWS Access Key ID, Secret Access Key, Default region (us-east-1)

# Create billing alert
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json
```

**budget.json:**
```json
{
  "BudgetName": "NYC Sidewalk Monthly",
  "BudgetLimit": {
    "Amount": "500.00",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

### 1.2 Domain Registration

```bash
# Option 1: Route 53 (AWS)
aws route53 register-domain \
  --domain-name nyc-sidewalk.example.com \
  --duration-in-years 1 \
  --privacy-type REDACTED

# Option 2: External registrar (GoDaddy, Namecheap, etc.)
# After registration, create hosted zone in Route 53
aws route53 create-hosted-zone \
  --name nyc-sidewalk.example.com \
  --caller-reference $(date +%s)
```

### 1.3 GitHub Repository Setup

```bash
# Add secrets to GitHub (see docs/GITHUB_SECRETS_SETUP.md)
# Navigate to: Settings → Secrets and variables → Actions

# Required secrets:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - AWS_ACCOUNT_ID
# - AWS_REGION
# - ECR_REGISTRY
# - ECR_REPOSITORY_API
# - ECR_REPOSITORY_WEB
# - OPENAI_API_KEY
# - SOCRATA_APP_TOKEN
# - DB_PASSWORD
```

## Phase 2: Infrastructure Setup (Days 2-3)

### 2.1 VPC & Networking

```bash
# Run the infrastructure setup
bash scripts/infrastructure_setup.sh

# Verify VPC created
aws ec2 describe-vpcs --filters Name=tag:Name,Values=nyc-sidewalk-vpc
```

### 2.2 RDS Database

```bash
# Wait for RDS to be available
aws rds wait db-instance-available \
  --db-instance-identifier nyc-sidewalk-db

# Get connection endpoint
aws rds describe-db-instances \
  --db-instance-identifier nyc-sidewalk-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text

# Initialize database schema
PGPASSWORD=$DB_PASSWORD psql \
  -h <RDS_ENDPOINT> \
  -U dot_user \
  -d sidewalk_db \
  -f sql/init_nyc_domain_model.sql
```

### 2.3 ElastiCache Redis

```bash
# Wait for Redis cluster
aws elasticache wait replication-group-available \
  --replication-group-id nyc-sidewalk-redis

# Get Redis endpoint
aws elasticache describe-replication-groups \
  --replication-group-id nyc-sidewalk-redis \
  --query 'ReplicationGroups[0].PrimaryEndpoint.Address' \
  --output text

# Test connection
redis-cli -h <REDIS_ENDPOINT> -p 6379 ping
# Should return: PONG
```

### 2.4 ECR Repositories

```bash
# Create repositories
aws ecr create-repository --repository-name nyc-sidewalk-api
aws ecr create-repository --repository-name nyc-sidewalk-web

# Get login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com
```

## Phase 3: Application Deployment (Days 4-5)

### 3.1 Build & Push Docker Images

```bash
# Build API image
docker build -t nyc-sidewalk-api:latest -f Dockerfile.api .

# Tag for ECR
docker tag nyc-sidewalk-api:latest \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/nyc-sidewalk-api:latest

# Push to ECR
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/nyc-sidewalk-api:latest

# Build Web image
cd frontend && npm install && npm run build && cd ..

docker build -t nyc-sidewalk-web:latest \
  --build-arg VITE_API_URL=https://api.nyc-sidewalk.example.com/api/v1 .

docker tag nyc-sidewalk-web:latest \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/nyc-sidewalk-web:latest

docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/nyc-sidewalk-web:latest
```

### 3.2 ECS Deployment

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name nyc-sidewalk

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json

# Create ECS service
aws ecs create-service \
  --cluster nyc-sidewalk \
  --service-name nyc-sidewalk-api \
  --task-definition nyc-sidewalk-api \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx]}"

# Check service status
aws ecs describe-services \
  --cluster nyc-sidewalk \
  --services nyc-sidewalk-api \
  --query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount}'
```

### 3.3 ALB & Target Groups

```bash
# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name nyc-sidewalk-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

# Create target group
TG_ARN=$(aws elbv2 create-target-group \
  --name nyc-sidewalk-api \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --health-check-path /health \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

# Register targets
aws elbv2 register-targets \
  --target-group-arn $TG_ARN \
  --targets Id=eni-xxx Id=eni-yyy Id=eni-zzz
```

## Phase 4: Security & SSL (Day 6)

### 4.1 ACM Certificate

```bash
# Request certificate
CERT_ARN=$(aws acm request-certificate \
  --domain-name nyc-sidewalk.example.com \
  --subject-alternative-names '*.nyc-sidewalk.example.com' \
  --validation-method DNS \
  --query 'CertificateArn' \
  --output text)

# Validate DNS records (follow ACM console)
# Add CNAME records to Route 53 as shown in ACM

# Wait for validation
aws acm wait certificate-validated --certificate-arn $CERT_ARN

echo "Certificate ARN: $CERT_ARN"
```

### 4.2 HTTPS Listener

```bash
# Add HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=$CERT_ARN \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN \
  --ssl-policy ELBSecurityPolicy-TLS-1-2-2017-01

# Add HTTP redirect to HTTPS
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions \
    Type=redirect,RedirectConfig="{Protocol=HTTPS,StatusCode=301,Port=443}"
```

### 4.3 Secrets Manager

```bash
# Store sensitive data
aws secretsmanager create-secret \
  --name nyc-sidewalk/db-password \
  --secret-string $(base64 -w0 < /dev/urandom | head -c 32)

aws secretsmanager create-secret \
  --name nyc-sidewalk/openai-key \
  --secret-string "sk-..."

aws secretsmanager create-secret \
  --name nyc-sidewalk/api-key \
  --secret-string "$(openssl rand -hex 32)"
```

## Phase 5: CI/CD & Automation (Day 7)

### 5.1 GitHub Actions Configuration

```bash
# Verify workflows are in .github/workflows/
ls -la .github/workflows/
# Should show: ci.yml, deploy.yml

# Trigger a test workflow
git commit --allow-empty -m "test: trigger ci workflow"
git push origin main

# Monitor in GitHub Actions tab
```

### 5.2 CloudWatch Setup

```bash
# Create log group
aws logs create-log-group --log-group-name /ecs/nyc-sidewalk-api
aws logs create-log-group --log-group-name /ecs/nyc-sidewalk-web

# Set retention
aws logs put-retention-policy \
  --log-group-name /ecs/nyc-sidewalk-api \
  --retention-in-days 30

# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name nyc-sidewalk-prod \
  --dashboard-body file://dashboard-body.json
```

### 5.3 Alarms & Notifications

```bash
# Create SNS topic for alerts
SNS_ARN=$(aws sns create-topic \
  --name nyc-sidewalk-alerts \
  --query 'TopicArn' \
  --output text)

# Subscribe email
aws sns subscribe \
  --topic-arn $SNS_ARN \
  --protocol email \
  --notification-endpoint ops@nycdot.gov

# Create high CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name nyc-sidewalk-high-cpu \
  --alarm-actions $SNS_ARN \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Create high error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name nyc-sidewalk-5xx-errors \
  --alarm-actions $SNS_ARN \
  --metric-name HTTPCode_Target_5XX \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1
```

## Phase 6: Testing (Day 8)

### 6.1 Health Checks

```bash
# Test API health
curl https://api.nyc-sidewalk.example.com/health

# Test web health
curl https://nyc-sidewalk.example.com/health

# Check ECS task health
aws ecs describe-services \
  --cluster nyc-sidewalk \
  --services nyc-sidewalk-api \
  --query 'services[0].taskDefinition'
```

### 6.2 Load Testing

```bash
# Install Apache Bench
apt-get install apache2-utils  # Linux
brew install ab  # macOS

# Run load test (1000 requests, 10 concurrent)
ab -n 1000 -c 10 https://api.nyc-sidewalk.example.com/health

# Expected: Response time <100ms, Error rate 0%
```

### 6.3 Failover Testing

```bash
# Stop one ECS task
TASK_ID=$(aws ecs list-tasks \
  --cluster nyc-sidewalk \
  --service-name nyc-sidewalk-api \
  --query 'taskArns[0]' \
  --output text | cut -d'/' -f3)

aws ecs stop-task \
  --cluster nyc-sidewalk \
  --task $TASK_ID

# Verify traffic reroutes to other tasks
curl https://api.nyc-sidewalk.example.com/health  # Should still work
sleep 30
curl https://api.nyc-sidewalk.example.com/health  # Task should restart

# Check ECS desired/running count
aws ecs describe-services \
  --cluster nyc-sidewalk \
  --services nyc-sidewalk-api
```

### 6.4 Database Backup Test

```bash
# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier nyc-sidewalk-db \
  --db-snapshot-identifier nyc-sidewalk-backup-test

# Verify snapshot completed
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier nyc-sidewalk-backup-test

# (Optional) Test restore to different instance
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier nyc-sidewalk-db-restore \
  --db-snapshot-identifier nyc-sidewalk-backup-test

# Verify restore (then delete)
aws rds delete-db-instance \
  --db-instance-identifier nyc-sidewalk-db-restore \
  --skip-final-snapshot
```

## Phase 7: Launch (Day 9)

### 7.1 DNS Cutover

```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Update Route 53 records
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789ABC \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "nyc-sidewalk.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "'$ALB_DNS'",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'

# Wait for DNS propagation
echo "Waiting for DNS propagation..."
sleep 300

# Verify DNS resolution
nslookup nyc-sidewalk.example.com
dig nyc-sidewalk.example.com +short
```

### 7.2 Production Validation

```bash
# Test HTTPS connection
curl -I https://nyc-sidewalk.example.com
# Expected: HTTP/2 200

# Test API functionality
curl https://api.nyc-sidewalk.example.com/api/v1/health
# Expected: {"status": "healthy"}

# Test LLM endpoints
curl -X POST https://api.nyc-sidewalk.example.com/api/v1/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# Monitor logs
aws logs tail /ecs/nyc-sidewalk-api --follow

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=nyc-sidewalk-api \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### 7.3 Runbook Distribution

Create and distribute operational runbooks:

```bash
# Email to ops team:
Subject: NYC Sidewalk Toolkit - Production Launch

Attached:
- OPERATIONS_MANUAL.md
- RUNBOOKS.md
- Emergency Contacts (phone numbers, on-call schedule)
- Escalation Procedures

Key Resources:
- Dashboard: https://console.aws.amazon.com/cloudwatch
- API Logs: /ecs/nyc-sidewalk-api
- Web Logs: /ecs/nyc-sidewalk-web
- On-Call: ops@nycdot.gov

Emergency Contact: [PHONE_NUMBER]
```

### 7.4 Post-Launch Monitoring (First 24 Hours)

```bash
# Monitor key metrics
watch -n 60 'aws ecs describe-services \
  --cluster nyc-sidewalk \
  --services nyc-sidewalk-api \
  --query "services[0].[status,runningCount,desiredCount]"'

# Check error rates
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX \
  --dimensions Name=LoadBalancer,Value=app/nyc-sidewalk-alb/* \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum

# Monitor database connections
PGPASSWORD=$DB_PASSWORD psql \
  -h <RDS_ENDPOINT> \
  -U dot_user \
  -d sidewalk_db \
  -c "SELECT count(*) FROM pg_stat_activity;"
```

## Rollback Procedure (If Needed)

```bash
# Scale down current service
aws ecs update-service \
  --cluster nyc-sidewalk \
  --service nyc-sidewalk-api \
  --desired-count 0

# Update DNS to previous endpoint (if available)
# Wait 5 minutes for DNS propagation
# Scale up previous service

# Restore database if needed
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier nyc-sidewalk-db-recovery \
  --db-snapshot-identifier <BACKUP_SNAPSHOT_ID>
```

## Cost Optimization (Post-Launch)

```bash
# Enable AWS Compute Optimizer
aws compute-optimizer put-recommendation-preferences \
  --resource-type Ec2Instance \
  --enhanced-infrastructure-metrics Active

# Reserved Instance Purchasing
# Review ECS and RDS usage patterns after 1 month
# Purchase 1-year reserved instances for 30% discount

# S3 Intelligent-Tiering for logs
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket nyc-sidewalk-logs \
  --id AutoTiering \
  --intelligent-tiering-configuration '{"Id":"AutoTiering","Filter":{"Prefix":"logs/"},"Status":"Enabled"}'
```

## Maintenance Schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| SSL Certificate Renewal | 30 days before expiry | DevOps |
| Database Backups | Daily | Automated |
| Log Rotation | Daily (30-day retention) | CloudWatch |
| Security Updates | Monthly | DevOps |
| Performance Review | Weekly | SRE |
| Disaster Recovery Drill | Quarterly | DevOps |
| Capacity Planning | Monthly | SRE |

## Support & Escalation

**Tier 1 - Application Support**
- Email: app-support@nycdot.gov
- Response: 2 hours
- Issues: User requests, data questions

**Tier 2 - Infrastructure Support**
- Slack: #nyc-sidewalk-ops
- Response: 1 hour  
- Issues: Performance, errors, scaling

**Tier 3 - Emergency Support**
- Phone: (212) XXX-XXXX
- Response: 15 minutes
- Issues: Service outage, data loss

## Success Criteria

✅ All health checks passing
✅ API response time <200ms (p99)
✅ Database connections stable
✅ Zero data loss in tests
✅ Failover works automatically
✅ Monitoring and alerts active
✅ Runbooks documented
✅ Team trained

**Go-Live Status: APPROVED** 🚀
