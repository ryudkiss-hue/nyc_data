# AWS Deployment Guide - NYC DOT Socrata Toolkit

Complete guide for deploying the NYC DOT Socrata Toolkit to AWS with production-grade 
infrastructure.


## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│               AWS PRODUCTION DEPLOYMENT                  │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Route 53 (DNS)                                  │    │
│  │  nyc-sidewalk.example.com                       │    │
│  └────────────────┬────────────────────────────────┘    │
│                   │                                      │
│  ┌────────────────▼────────────────────────────────┐    │
│  │  CloudFront (CDN) + WAF                         │    │
│  │  TLS Certificates (ACM)                         │    │
│  └────────────────┬────────────────────────────────┘    │
│                   │                                      │
│  ┌────────────────▼────────────────────────────────┐    │
│  │  Application Load Balancer (ALB)                │    │
│  │  443 (HTTPS) → 8000 (HTTP internal)            │    │
│  │  Security Group: Allow 443, 80                 │    │
│  └────────────────┬────────────────────────────────┘    │
│                   │                                      │
│  ┌────────────────▼────────────────────────────────┐    │
│  │  ECS Fargate Cluster                            │    │
│  │  ┌──────────────┐  ┌──────────────┐             │    │
│  │  │ API Service  │  │ Web Service  │             │    │
│  │  │ (FastAPI)    │  │ (Streamlit)  │             │    │
│  │  │ 3 Tasks      │  │ 2 Tasks      │             │    │
│  │  └──────────────┘  └──────────────┘             │    │
│  └────────────────┬────────────────────────────────┘    │
│                   │                                      │
│  ┌────────────────▼────────────────────────────────┐    │
│  │  RDS PostgreSQL + PostGIS                        │    │
│  │  Multi-AZ, automated backups, encryption        │    │
│  │  Subnet Group: Private VPC                      │    │
│  └────────────────┬────────────────────────────────┘    │
│                   │                                      │
│  ┌────────────────┴────────────────────────────────┐    │
│  │  ElastiCache Redis                              │    │
│  │  Multi-AZ, automatic failover                   │    │
│  │  For: rate limiting, caching, sessions          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  CloudWatch Monitoring & Alarms                  │    │
│  │  - Application Logs                              │    │
│  │  - Performance Metrics                           │    │
│  │  - Error Rate & Latency Alerts                  │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Secrets Manager                                │    │
│  │  - Database credentials                          │    │
│  │  - API keys (OpenAI, etc.)                       │    │
│  │  - TLS certificates                              │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## Prerequisites

- AWS Account with appropriate IAM permissions
- Domain name (Route 53 or external registrar)
- Docker images pushed to ECR
- GitHub repository with Actions enabled

## Step 1: Create AWS ECR Repository

```bash
# Create repository for API and web services
aws ecr create-repository \
  --repository-name nyc-sidewalk-api \
  --region us-east-1 \
  --encryption-configuration encryptionType=AES

aws ecr create-repository \
  --repository-name nyc-sidewalk-web \
  --region us-east-1
```

## Step 2: Configure VPC & Networking

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region us-east-1

# Create public subnets (ALB)
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create private subnets (ECS, RDS, ElastiCache)
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.10.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.11.0/24 --availability-zone us-east-1b

# Create security groups
aws ec2 create-security-group \
  --group-name nyc-sidewalk-alb \
  --description "ALB security group" \
  --vpc-id vpc-xxx

# Allow HTTPS inbound
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

## Step 3: Create RDS PostgreSQL Database

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name nyc-sidewalk-db \
  --db-subnet-group-description "DB subnets for NYC Sidewalk" \
  --subnet-ids subnet-xxx subnet-yyy

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier nyc-sidewalk-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 14.7 \
  --master-username dot_user \
  --master-user-password <SECURE_PASSWORD> \
  --allocated-storage 100 \
  --db-subnet-group-name nyc-sidewalk-db \
  --vpc-security-group-ids sg-xxx \
  --multi-az \
  --storage-encrypted \
  --backup-retention-period 30 \
  --enable-cloudwatch-logs-exports postgresql \
  --region us-east-1

# Enable PostGIS
aws rds modify-db-instance \
  --db-instance-identifier nyc-sidewalk-db \
  --db-parameter-group-name default.postgres14 \
  --apply-immediately
```

## Step 4: Create ElastiCache Redis Cluster

```bash
# Create cache subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name nyc-sidewalk-redis \
  --cache-subnet-group-description "Redis for NYC Sidewalk" \
  --subnet-ids subnet-xxx subnet-yyy

# Create Redis cluster
aws elasticache create-replication-group \
  --replication-group-description "Redis for NYC Sidewalk" \
  --replication-group-id nyc-sidewalk-redis \
  --engine redis \
  --engine-version 7.0 \
  --cache-node-type cache.t3.small \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --cache-subnet-group-name nyc-sidewalk-redis \
  --security-group-ids sg-xxx \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled
```

## Step 5: Set Up Secrets Manager

```bash
# Store database password
aws secretsmanager create-secret \
  --name nyc-sidewalk/db-password \
  --secret-string <DB_PASSWORD>

# Store API keys
aws secretsmanager create-secret \
  --name nyc-sidewalk/openai-key \
  --secret-string sk-...

aws secretsmanager create-secret \
  --name nyc-sidewalk/socrata-token \
  --secret-string <SOCRATA_TOKEN>

# Store TLS certificate
aws secretsmanager create-secret \
  --name nyc-sidewalk/tls-certificate \
  --secret-string file://cert.pem
```

## Step 6: Configure ACM Certificates

```bash
# Request certificate
aws acm request-certificate \
  --domain-name nyc-sidewalk.example.com \
  --subject-alternative-names *.nyc-sidewalk.example.com \
  --validation-method DNS \
  --region us-east-1

# Validate certificate via DNS (follow ACM console instructions)
```

## Step 7: Create ECS Task Definition

Create `ecs-task-definition.json`:

```json
{
  "family": "nyc-sidewalk-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/nyc-sidewalk-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://dot_user@nyc-sidewalk-db.xxx.us-east-1.rds.amazonaws.com:5432/sidewalk_db"
        },
        {
          "name": "REDIS_URL",
          "value": "redis://nyc-sidewalk-redis.xxx.ng.0001.use1.cache.amazonaws.com:6379"
        },
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DB_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:nyc-sidewalk/db-password"
        },
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:nyc-sidewalk/openai-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/nyc-sidewalk-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/ecsTaskRole"
}
```

## Step 8: Create ECS Service

```bash
# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json

# Create ECS cluster
aws ecs create-cluster --cluster-name nyc-sidewalk

# Create service
aws ecs create-service \
  --cluster nyc-sidewalk \
  --service-name nyc-sidewalk-api \
  --task-definition nyc-sidewalk-api \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=api,containerPort=8000
```

## Step 9: Create Load Balancer

```bash
# Create target group
aws elbv2 create-target-group \
  --name nyc-sidewalk-api \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --health-check-enabled \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Create ALB
aws elbv2 create-load-balancer \
  --name nyc-sidewalk-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx \
  --type application \
  --ip-address-type ipv4

# Create HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

## Step 10: Configure Route 53

```bash
# Create hosted zone (if new domain)
aws route53 create-hosted-zone \
  --name nyc-sidewalk.example.com \
  --caller-reference $(date +%s)

# Create DNS record pointing to ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789ABC \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "nyc-sidewalk.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "nyc-sidewalk-alb-123.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

## Step 11: Enable CloudWatch Monitoring

```bash
# Create log group
aws logs create-log-group --log-group-name /ecs/nyc-sidewalk-api

# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name nyc-sidewalk \
  --dashboard-body file://dashboard-config.json

# Create alarms
aws cloudwatch put-metric-alarm \
  --alarm-name nyc-sidewalk-high-error-rate \
  --alarm-description "Alert on high error rate" \
  --metric-name HTTPCode_Target_5XX \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

## Cost Estimation

| Service | Instance | Monthly Cost |
|---------|----------|-------------|
| ECS Fargate | 1 vCPU, 2GB RAM (5 tasks) | ~$50 |
| RDS PostgreSQL | db.t3.medium, Multi-AZ | ~$200 |
| ElastiCache Redis | cache.t3.small, Multi-AZ | ~$60 |
| ALB | 1 ALB, ~1M requests | ~$20 |
| Data Transfer | ~100GB outbound | ~$10 |
| CloudWatch Logs | ~50GB/month | ~$25 |
| Secrets Manager | 3 secrets | <$1 |
| **Total** | | **~$365/month** |

## Backup & Disaster Recovery

```bash
# Enable RDS automated backups
aws rds modify-db-instance \
  --db-instance-identifier nyc-sidewalk-db \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00" \
  --apply-immediately

# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier nyc-sidewalk-db \
  --db-snapshot-identifier nyc-sidewalk-backup-$(date +%Y-%m-%d)

# Export to S3 for long-term storage
aws rds start-export-task \
  --export-task-identifier nyc-sidewalk-export \
  --source-arn arn:aws:rds:us-east-1:123456789012:db:nyc-sidewalk-db \
  --s3-bucket-name mycompany-backups \
  --s3-prefix nyc-sidewalk/
```

## Security Best Practices

✅ **VPC & Network**
- Private subnets for database and cache
- Security groups with minimal permissions
- VPN/bastion host for administrative access

✅ **Encryption**
- TLS 1.3 for all traffic (ALB → ECS → RDS)
- Encryption at rest for RDS and ElastiCache
- KMS keys for Secrets Manager

✅ **Access Control**
- IAM roles with least privilege
- Secrets Manager for all credentials
- VPC endpoints for AWS services

✅ **Monitoring**
- CloudWatch logs for all services
- Application Performance Monitoring (APM)
- Security group flow logs
- S3 access logs

## Troubleshooting

### ECS Tasks failing to start
```bash
# Check logs
aws logs tail /ecs/nyc-sidewalk-api --follow

# Check task status
aws ecs list-tasks --cluster nyc-sidewalk
aws ecs describe-tasks --cluster nyc-sidewalk --tasks <task-arn>
```

### Database connection errors
```bash
# Check RDS security group
aws ec2 describe-security-groups --group-ids sg-xxx

# Test connectivity
aws ec2-instance-connect open-osm-tunnel --remote-port 5432
psql -h <RDS_ENDPOINT> -U dot_user -d sidewalk_db
```

### High latency
```bash
# Check ALB target health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:...

# Check ECS task CPU/memory
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=nyc-sidewalk-api \
  --start-time 2026-01-01T00:00:00Z \
  --end-time 2026-01-01T01:00:00Z \
  --period 300 \
  --statistics Average,Maximum
```

## Next Steps

1. Test ECS deployment with staging environment
2. Set up CloudFront CDN for static content
3. Configure WAF rules for DDoS protection
4. Implement auto-scaling policies
5. Set up CloudTrail for audit logging
