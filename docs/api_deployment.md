# Phase 4 API Deployment Guide

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Configuration](#configuration)
5. [Database Setup](#database-setup)
6. [Cache Setup](#cache-setup)
7. [Production Deployment](#production-deployment)
8. [Health Checks & Monitoring](#health-checks--monitoring)
9. [Horizontal Scaling](#horizontal-scaling)
10. [SSL/TLS Configuration](#ssltls-configuration)
11. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Hardware

- **CPU**: 2 cores
- **Memory**: 4 GB RAM
- **Disk**: 20 GB (for database and cache)
- **Network**: 1 Gbps connection

### Software Requirements

- **Python**: 3.10+ (tested on 3.11)
- **PostgreSQL**: 14+ (for domain model and materialized views)
- **Redis**: 6.0+ (for caching)
- **Docker**: 20.10+ (optional, for containerized deployment)
- **Uvicorn**: 0.24.0+ (ASGI server)

### Python Dependencies

```
# Core dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg[binary]==3.1.12
redis==5.0.1
pydantic==2.5.0
python-dotenv==1.0.0
PyJWT==2.8.1

# Observability (Phase 2 integration)
prometheus-client==0.19.0

# Optional: Performance
gunicorn==21.2.0  # Production ASGI server
```

## Local Development

### 1. Clone Repository

```bash
git clone https://github.com/your-org/nyc_data.git
cd nyc_data
```

### 2. Create Virtual Environment

```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using poetry
poetry install
poetry shell
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install fastapi uvicorn sqlalchemy psycopg redis pydantic python-dotenv PyJWT prometheus-client
```

### 4. Set Environment Variables

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/nyc_sidewalk
DB_POOL_SIZE=10
DB_POOL_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_TIMEOUT=5.0

# JWT
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=1440

# API
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=debug
LOG_FORMAT=json

# CORS
CORS_ORIGINS="http://localhost:3000 http://localhost:8000"

# Rate Limiting
RATE_LIMIT_REQUESTS=100

# Cache TTL (in seconds)
CACHE_TTL_SUMMARY_KPIS=7200
CACHE_TTL_SEGMENT_DETAILS=86400
CACHE_TTL_CONTRACTOR_METRICS=21600
CACHE_TTL_INCIDENT_LISTS=3600
```

### 5. Start PostgreSQL and Redis

```bash
# Using Docker
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15-alpine

docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine

# Or using local installations
pg_ctl -D /usr/local/var/postgres start
redis-server
```

### 6. Initialize Database

```bash
# Run migrations (Phase 1 domain model)
psql postgresql://postgres:password@localhost:5432/nyc_sidewalk \
  < sql/init_nyc_domain_model.sql

# Verify tables
psql postgresql://postgres:password@localhost:5432/nyc_sidewalk \
  -c "\dt"
```

### 7. Run Development Server

```bash
# With auto-reload
python -m uvicorn socrata_toolkit.api.main:app --reload

# Or directly
uvicorn socrata_toolkit.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 8. Verify Health

```bash
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","timestamp":"2026-05-10T01:51:19Z","database":"healthy","cache":"healthy","version":"v1"}
```

### 9. Access Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Metrics: http://localhost:8000/metrics

## Docker Deployment

### Single Container (Development)

```bash
cd socrata_toolkit/api

# Build image
docker build -t nyc-sidewalk-api:latest .

# Run container
docker run -d \
  --name api \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://postgres:password@postgres:5432/nyc_sidewalk \
  -e REDIS_URL=redis://redis:6379/0 \
  -e JWT_SECRET_KEY=$(openssl rand -hex 32) \
  -e ENVIRONMENT=development \
  nyc-sidewalk-api:latest

# Check logs
docker logs -f api

# Test
curl http://localhost:8000/health
```

### Docker Compose (Recommended)

```bash
cd socrata_toolkit/api

# Start all services
docker-compose up -d

# Verify services
docker-compose ps

# Check logs
docker-compose logs -f api

# Stop services
docker-compose down

# Clean up (remove volumes)
docker-compose down -v
```

Services started:
- **postgres**: Database (port 5432)
- **redis**: Cache (port 6379)
- **api**: FastAPI service (port 8000)
- **nginx**: Reverse proxy (port 80) - optional with `--profile with-nginx`
- **prometheus**: Metrics (port 9090) - optional with `--profile with-monitoring`
- **grafana**: Dashboards (port 3000) - optional with `--profile with-monitoring`

### Custom Docker Configuration

```bash
# Start with custom environment
docker-compose -f docker-compose.yml up -d \
  -e ENVIRONMENT=production \
  -e JWT_SECRET_KEY=$(openssl rand -hex 32)

# Scale API service (requires load balancer)
docker-compose up -d --scale api=3

# Build specific service
docker-compose build api

# Push to registry
docker tag nyc-sidewalk-api:latest registry.example.com/api:latest
docker push registry.example.com/api:latest
```

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENVIRONMENT` | string | development | Environment (development, staging, production) |
| `DATABASE_URL` | string | - | PostgreSQL connection string |
| `REDIS_URL` | string | redis://localhost | Redis connection URL |
| `JWT_SECRET_KEY` | string | - | Secret key for JWT (min 32 chars in prod) |
| `JWT_ALGORITHM` | string | HS256 | JWT algorithm (HS256, HS512, RS256) |
| `JWT_EXPIRY_MINUTES` | int | 1440 | Token expiry in minutes |
| `API_HOST` | string | 0.0.0.0 | API bind address |
| `API_PORT` | int | 8000 | API bind port |
| `LOG_LEVEL` | string | info | Logging level (debug, info, warning, error) |
| `LOG_FORMAT` | string | json | Log format (json, text) |
| `CORS_ORIGINS` | string | * | CORS origins (space-separated) |
| `RATE_LIMIT_REQUESTS` | int | 100 | Requests per minute limit |
| `CACHE_TTL_SUMMARY_KPIS` | int | 7200 | Summary KPI cache TTL (seconds) |
| `CACHE_TTL_SEGMENT_DETAILS` | int | 86400 | Segment detail cache TTL |
| `CACHE_TTL_CONTRACTOR_METRICS` | int | 21600 | Contractor metrics cache TTL |
| `CACHE_TTL_INCIDENT_LISTS` | int | 3600 | Incident list cache TTL |
| `DB_POOL_SIZE` | int | 10 | PostgreSQL connection pool size |
| `DB_POOL_OVERFLOW` | int | 20 | Max overflow connections |
| `DB_POOL_TIMEOUT` | float | 30.0 | Connection timeout (seconds) |

### Configuration Priority

1. Environment variables (highest priority)
2. `.env` file
3. Hardcoded defaults (lowest priority)

### Multi-Environment Setup

**.env.development**:
```
ENVIRONMENT=development
DATABASE_URL=postgresql://postgres:password@localhost:5432/nyc_sidewalk
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=dev-secret-key-change-in-production
LOG_LEVEL=debug
```

**.env.staging**:
```
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:pass@staging-db.example.com:5432/nyc_sidewalk
REDIS_URL=redis://staging-redis.example.com:6379/0
JWT_SECRET_KEY=$(openssl rand -hex 32)
LOG_LEVEL=info
```

**.env.production**:
```
ENVIRONMENT=production
DATABASE_URL=postgresql://produser:prodpass@prod-db-cluster.example.com:5432/nyc_sidewalk
REDIS_URL=redis://prod-redis-cluster.example.com:6379/0
JWT_SECRET_KEY=$(openssl rand -hex 32)
LOG_LEVEL=warning
RATE_LIMIT_REQUESTS=1000
```

## Database Setup

### PostgreSQL Configuration

#### Connection Pool Settings

```python
# In socrata_toolkit/api/config.py
db_pool_size=20          # Initial pool size
db_pool_overflow=40      # Max overflow connections
db_pool_timeout=30.0     # Timeout for acquiring connection
db_pool_recycle=3600     # Recycle connections after 1 hour
```

For production, adjust based on:
- Number of API instances
- Expected concurrent requests
- Query latency

Formula: `pool_size = (num_cores * 2) + effective_spindle_count`

#### Connection String Examples

```
# Local development
postgresql://postgres:password@localhost:5432/nyc_sidewalk

# Remote PostgreSQL
postgresql://user:password@db.example.com:5432/nyc_sidewalk

# With SSL
postgresql://user:password@db.example.com:5432/nyc_sidewalk?sslmode=require

# Read replica
postgresql://user:password@read-replica.example.com:5432/nyc_sidewalk

# AWS RDS
postgresql://user:password@mydb.cluster-abcd1234.us-east-1.rds.amazonaws.com:5432/nyc_sidewalk
```

### Initialize Database Tables

```bash
# Run schema script
psql $DATABASE_URL < sql/init_nyc_domain_model.sql

# Verify creation
psql $DATABASE_URL -c """
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public'
  ORDER BY table_name;
"""

# Should show:
# dim_street_segments
# fact_incidents
# fact_repair_schedule
# materialized_view_material_metrics
# materialized_view_ada_metrics
# materialized_view_hazard_coverage
# materialized_view_contractor_performance
# materialized_view_cost_analytics
# audit_log
```

### Backup & Recovery

```bash
# Backup database
pg_dump $DATABASE_URL > nyc_sidewalk_backup.sql

# Backup with compression
pg_dump $DATABASE_URL | gzip > nyc_sidewalk_backup.sql.gz

# Restore from backup
psql $DATABASE_URL < nyc_sidewalk_backup.sql

# Restore from compressed backup
gunzip -c nyc_sidewalk_backup.sql.gz | psql $DATABASE_URL
```

## Cache Setup

### Redis Configuration

#### Connection String Examples

```
# Local development
redis://localhost:6379/0

# Remote Redis
redis://redis.example.com:6379/0

# With authentication
redis://:password@redis.example.com:6379/0

# Redis Cluster
rediss://password@redis-cluster.example.com:6379/0

# AWS ElastiCache
redis://mydb.abcd1234.ng.0001.use1.cache.amazonaws.com:6379
```

#### Performance Tuning

```bash
# Edit redis.conf
maxmemory 4gb
maxmemory-policy allkeys-lru  # Evict LRU keys when memory full
timeout 0                      # Don't close idle connections
tcp-keepalive 60               # Health checks every 60 seconds

# Restart Redis
redis-cli CONFIG SET maxmemory 4gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Monitor commands
redis-cli --stat              # Live stats
redis-cli --bigkeys           # Find large keys
redis-cli --latency-history   # Latency analysis
```

#### Redis Sentinel (High Availability)

```bash
# sentinel.conf
port 26379
sentinel monitor nyc-redis 127.0.0.1 6379 1
sentinel down-after-milliseconds nyc-redis 30000
sentinel parallel-syncs nyc-redis 1

# Start sentinel
redis-sentinel sentinel.conf

# Update connection string
REDIS_URL=redis-sentinel://user:password@sentinel1:26379,sentinel2:26379,sentinel3:26379/nyc-redis/0
```

## Production Deployment

### Kubernetes (EKS/GKE)

#### Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nyc-sidewalk-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: registry.example.com/nyc-sidewalk-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: redis-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: nyc-sidewalk-api
spec:
  type: LoadBalancer
  selector:
    app: api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

Deploy:
```bash
kubectl apply -f deployment.yaml
kubectl get svc nyc-sidewalk-api
```

### EC2/Virtual Machine

```bash
#!/bin/bash
# deployment.sh - Production deployment script

set -e

# Variables
APP_DIR=/opt/nyc-sidewalk-api
APP_USER=apiuser
PYTHON_VERSION=3.11

# 1. Install system dependencies
apt-get update && apt-get install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    postgresql-client \
    curl

# 2. Create app directory
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

# 3. Clone repository
cd $APP_DIR
git clone https://github.com/your-org/nyc_data.git .
chown -R $APP_USER:$APP_USER .

# 4. Create virtual environment
python${PYTHON_VERSION} -m venv venv
source venv/bin/activate

# 5. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 6. Create systemd service
cat > /etc/systemd/system/nyc-sidewalk-api.service << EOF
[Unit]
Description=NYC Sidewalk API
After=network.target

[Service]
Type=notify
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    socrata_toolkit.api.main:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 7. Enable and start service
systemctl daemon-reload
systemctl enable nyc-sidewalk-api
systemctl start nyc-sidewalk-api

# 8. Verify
sleep 5
curl http://localhost:8000/health
```

Run: `bash deployment.sh`

### Gunicorn Configuration

```bash
# gunicorn_config.py
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 60
keepalive = 5
max_requests = 10000
max_requests_jitter = 1000

# Logging
accesslog = "/var/log/nyc-sidewalk-api/access.log"
errorlog = "/var/log/nyc-sidewalk-api/error.log"
loglevel = "info"

# Pre-fork settings
preload_app = True
```

Run: `gunicorn -c gunicorn_config.py socrata_toolkit.api.main:app`

## Health Checks & Monitoring

### Health Check Endpoint

```bash
curl http://localhost:8000/health -v

# Response
HTTP/1.1 200 OK
{
  "status": "healthy",
  "timestamp": "2026-05-10T01:51:19Z",
  "database": "healthy",
  "cache": "healthy",
  "version": "v1"
}
```

### Metrics Endpoint (Prometheus)

```bash
curl http://localhost:8000/metrics

# Output (Prometheus format)
# HELP api_requests_total Total API requests
# TYPE api_requests_total counter
api_requests_total{method="GET",path="/segments"} 1234.0
api_requests_total{method="POST",path="/repairs"} 56.0

# HELP api_request_duration_seconds Request duration in seconds
# TYPE api_request_duration_seconds histogram
api_request_duration_seconds_bucket{le="0.1",path="/segments"} 1100.0
api_request_duration_seconds_bucket{le="0.5",path="/segments"} 1200.0
api_request_duration_seconds_bucket{le="1.0",path="/segments"} 1220.0
```

### Prometheus Scrape Config

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'nyc-sidewalk-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Key metrics to monitor:
- Request rate (req/sec)
- Request latency (p50, p95, p99)
- Error rate by error code
- Cache hit rate
- Database connection pool usage
- Memory usage
- API uptime

### Alerting (AlertManager)

```yaml
# alert_rules.yml
groups:
  - name: api
    rules:
      - alert: APIDown
        expr: up{job="nyc-sidewalk-api"} == 0
        for: 2m
        annotations:
          summary: "API is down"

      - alert: HighErrorRate
        expr: rate(api_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate: {{ $value }}"

      - alert: SlowRequests
        expr: api_request_duration_seconds{quantile="0.95"} > 1
        for: 5m
        annotations:
          summary: "Slow requests (p95 > 1s)"
```

## Horizontal Scaling

### Load Balancer Setup (Nginx)

```nginx
# nginx.conf
upstream api_backend {
    least_conn;
    server api1.example.com:8000 weight=1;
    server api2.example.com:8000 weight=1;
    server api3.example.com:8000 weight=1;

    # Health check
    check interval=3000 rise=2 fall=5 timeout=1000 type=http;
    check_http_send "GET /health HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx http_3xx;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Request-ID $request_id;

        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    location /health {
        access_log off;
        proxy_pass http://api_backend;
    }

    location /metrics {
        access_log off;
        proxy_pass http://api_backend;
    }
}
```

### Auto-Scaling (Kubernetes HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nyc-sidewalk-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## SSL/TLS Configuration

### Self-Signed Certificate (Development)

```bash
# Generate certificate
openssl req -x509 -newkey rsa:4096 -nodes \
    -out cert.pem -keyout key.pem -days 365

# Run with SSL
uvicorn socrata_toolkit.api.main:app \
    --ssl-certfile=cert.pem \
    --ssl-keyfile=key.pem \
    --ssl-version=TLS
```

### Let's Encrypt (Production)

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Get certificate
certbot certonly --standalone -d api.example.com

# Auto-renew
certbot renew --quiet --no-eff-email

# Nginx configuration
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Rest of configuration...
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

## Troubleshooting

### Database Connection Issues

```bash
# Check connection
psql $DATABASE_URL -c "SELECT 1"

# Verify pool settings
python -c "
from socrata_toolkit.api.config import APIConfig
config = APIConfig()
print(f'Pool size: {config.db_pool_size}')
print(f'Pool overflow: {config.db_pool_overflow}')
"

# Monitor connections
watch -n 1 "psql $DATABASE_URL -c 'SELECT count(*) FROM pg_stat_activity;'"
```

### Cache Connection Issues

```bash
# Test Redis
redis-cli ping

# Check memory
redis-cli INFO memory

# Clear cache if needed
redis-cli FLUSHDB

# Monitor commands
redis-cli MONITOR
```

### High Latency

```bash
# Check metrics
curl http://localhost:8000/metrics | grep api_request_duration

# Profile slow requests
python -m cProfile -s cumulative -m uvicorn socrata_toolkit.api.main:app

# Check database query times
EXPLAIN ANALYZE <your-query>
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Reduce cache TTLs in .env
CACHE_TTL_SUMMARY_KPIS=3600  # 1 hour instead of 2

# Check for memory leaks
python -m memory_profiler socrata_toolkit/api/main.py
```

---

For more information:
- [API User Guide](api_guide.md)
- [Examples & Use Cases](api_examples.md)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org)
- [Redis Docs](https://redis.io/documentation)
