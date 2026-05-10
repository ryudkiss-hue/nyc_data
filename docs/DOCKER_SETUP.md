# Docker Development Environment Setup

Complete guide to spinning up the NYC Data Toolkit in Docker for local development and testing.

## Prerequisites

- **Docker Desktop** (latest version recommended)
  - Download: https://www.docker.com/products/docker-desktop
  - Minimum requirements: 4GB RAM, 20GB disk space
- **Docker Compose** (included with Docker Desktop)
  - Verify: `docker-compose --version`
- **Git** (for cloning the repository)
- **curl** or **Postman** (for testing API endpoints)

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 4GB | 8GB+ |
| CPU | 2 cores | 4+ cores |
| Disk | 20GB free | 50GB free |
| Docker Engine | 20.10+ | Latest |

## Quick Start (3 Steps)

### 1. Clone and Prepare

```bash
# Clone the repository
git clone <repository-url>
cd nyc_data

# Copy environment file (if not already present)
cp .env.docker.example .env.docker

# Make scripts executable (Linux/macOS)
chmod +x scripts/docker-*.sh
```

### 2. Start Services

```bash
# One-command startup
./scripts/docker-start.sh

# Windows (PowerShell):
# docker-compose up -d
```

**Expected output:**
```
[1/5] Starting PostgreSQL, Redis, Prometheus, Grafana, Jaeger, API, and MinIO...
[2/5] Waiting for PostgreSQL to be ready...
✓ PostgreSQL is healthy
[3/5] Waiting for Redis to be ready...
✓ Redis is healthy
[4/5] Waiting for API to be ready...
✓ API is healthy
[5/5] Checking all services...
✓ All services are running!
```

### 3. Verify Installation

```bash
# Check all services are healthy
docker-compose ps

# Test API health endpoint
curl http://localhost:8000/health

# Check PostgreSQL connection
psql -h localhost -U dot_user -d sidewalk_db -c "SELECT COUNT(*) FROM sidewalk_inspections;"
```

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **API (FastAPI)** | http://localhost:8000 | REST API endpoints |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **API ReDoc** | http://localhost:8000/redoc | API documentation |
| **Grafana** | http://localhost:3000 | Dashboards & monitoring |
| **Prometheus** | http://localhost:9090 | Metrics scraping & queries |
| **Jaeger UI** | http://localhost:16686 | Distributed tracing |
| **MinIO Console** | http://localhost:9001 | S3-compatible storage UI |
| **PostgreSQL** | localhost:5432 | Database server |
| **Redis** | localhost:6379 | Cache & rate limiting |

## Credentials

### Default Credentials

| Service | Username | Password | Notes |
|---------|----------|----------|-------|
| **Grafana** | admin | admin | Change in production |
| **MinIO** | minioadmin | minioadmin | Change in production |
| **PostgreSQL** | dot_user | dot_pass | Change in production |
| **API JWT Secret** | — | dev-secret-key-... | Change in production |

### Demo API Keys

For testing API endpoints with authentication:

```bash
export API_KEY="sk_test_demo_admin_abc123"

# Use in requests:
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/v1/sidewalk_inspections
```

Available demo keys:
- `sk_test_demo_admin_abc123` - Admin access (user: demo_admin)
- `sk_test_demo_developer_def456` - Developer access (user: demo_developer)
- `sk_test_demo_analyst_ghi789` - Analyst access (user: demo_analyst)

## Sample Data

### Pre-seeded Datasets

The Docker environment automatically seeds sample data on startup:

| Dataset | Records | Purpose |
|---------|---------|---------|
| **Sidewalk Inspections** | 1,000 | Test inspection data with ADA compliance |
| **311 Complaints** | 500 | Sample complaint data with status tracking |
| **Contractors** | 50 | Master contractor data with ratings |

### Verify Sample Data

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U dot_user -d sidewalk_db

# List available tables
\dt

# Count records in each table
SELECT 'sidewalk_inspections' as table_name, COUNT(*) FROM sidewalk_inspections
UNION ALL
SELECT 'complaints_311', COUNT(*) FROM complaints_311
UNION ALL
SELECT 'contractors', COUNT(*) FROM contractors;
```

## Working with Services

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f redis

# Last 100 lines
docker-compose logs -f --tail=100 api
```

### Access Database

```bash
# Direct PostgreSQL connection
docker-compose exec postgres psql -U dot_user -d sidewalk_db

# Or use psql installed locally
psql -h localhost -U dot_user -d sidewalk_db

# Common queries
# List tables
\dt

# Show schema of a table
\d sidewalk_inspections

# Count records
SELECT COUNT(*) FROM sidewalk_inspections;
```

### Access Redis CLI

```bash
docker-compose exec redis redis-cli

# Check cache status
INFO

# View keys
KEYS *

# Get value
GET key_name
```

### Restart a Service

```bash
# Restart single service
docker-compose restart api

# Restart all
docker-compose restart

# Rebuild and restart
docker-compose up -d --build api
```

## Troubleshooting

### Port Already in Use

If you get "port X is already in use" error:

```bash
# Find what's using the port (Linux/macOS)
lsof -i :8000  # for port 8000

# Kill the process
kill -9 <PID>

# Or modify docker-compose.yml to use different ports
```

### Docker Daemon Not Running

```bash
# Check if Docker is running
docker ps

# If error: Cannot connect to Docker daemon
# Start Docker Desktop application
# Or on Linux: sudo systemctl start docker
```

### Out of Memory Errors

Docker containers consume significant memory. If you see memory errors:

```bash
# Increase Docker's allocated memory
# 1. Open Docker Desktop Preferences
# 2. Go to Resources > Memory
# 3. Increase to 6-8GB

# Or check current usage
docker stats
```

### Stuck or Unhealthy Services

```bash
# Check service health
docker-compose ps

# View detailed logs
docker-compose logs api

# Reset everything (WARNING: deletes data)
./scripts/docker-reset.sh

# Then restart
./scripts/docker-start.sh
```

### Database Connection Issues

```bash
# Verify PostgreSQL is healthy
docker-compose exec postgres pg_isready -U dot_user

# Check database exists
docker-compose exec postgres psql -U dot_user -l

# View PostgreSQL logs
docker-compose logs postgres
```

### API Not Responding

```bash
# Check if API container is running
docker-compose ps api

# View API logs
docker-compose logs api

# Test connection
curl -v http://localhost:8000/health

# Check if port is open
netstat -an | grep 8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows
```

## Next Steps

After successful startup:

1. **Explore API Documentation**
   - Visit http://localhost:8000/docs
   - Try sample endpoints with demo API keys

2. **View Sample Data**
   ```bash
   curl -H "Authorization: Bearer sk_test_demo_admin_abc123" \
     http://localhost:8000/api/v1/sidewalk_inspections?limit=5
   ```

3. **Check Dashboards**
   - Grafana: http://localhost:3000
   - Prometheus: http://localhost:9090
   - Jaeger: http://localhost:16686

4. **Run Integration Example**
   ```bash
   python examples/integration_example.py
   ```

5. **Follow Integration Quick Start**
   - See: [INTEGRATION_QUICK_START.md](INTEGRATION_QUICK_START.md)

## Development Workflow

### Making Code Changes

Code changes are reflected immediately due to volume mounts:

```bash
# Edit a file in socrata_toolkit/
# Changes are automatically reflected in running container
# Some services may need restart for changes to take effect

docker-compose restart api  # For API code changes
```

### Adding New Database Tables

```bash
# 1. Create migration file in sql/
# 2. Add to docker-compose.yml volumes if not already there
# 3. Restart PostgreSQL
docker-compose restart postgres

# Or reset and restart all
./scripts/docker-reset.sh
./scripts/docker-start.sh
```

## Stopping and Cleanup

```bash
# Stop all services (data preserved)
./scripts/docker-stop.sh

# Remove containers and networks (data preserved in volumes)
docker-compose down

# Remove everything including data (WARNING: destructive)
./scripts/docker-reset.sh

# Remove specific volumes
docker volume rm nyc_data_pgdata
docker volume rm nyc_data_redisdata
```

## Performance Tuning

### For Development (Default)

Suitable for local development and testing:

```yaml
# docker-compose.yml defaults are optimized for development
# - Single replicas
# - Development logging
# - Hot reload enabled
```

### For Heavier Testing

If running heavy workloads:

```bash
# Increase PostgreSQL memory
# In docker-compose.yml, add to postgres service:
environment:
  - POSTGRES_INIT_ARGS=-c shared_buffers=512MB -c effective_cache_size=2GB

# Increase Redis memory
command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

## Monitoring and Health Checks

### Health Check Status

```bash
# View health status for all services
docker-compose ps

# Expected output:
# NAME                 STATE       PORTS
# nyc_data_postgres    healthy     5432/tcp
# nyc_data_redis       healthy     6379/tcp
# nyc_data_api         healthy     8000/tcp
# nyc_data_grafana     healthy     3000/tcp
```

### Metrics and Monitoring

```bash
# View Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query a metric
curl 'http://localhost:9090/api/v1/query?query=up'

# View Grafana dashboards
# http://localhost:3000/api/search
```

## Environment Variables

### Customizing Configuration

Edit `.env.docker` to customize:

```bash
# PostgreSQL
POSTGRES_USER=dot_user
POSTGRES_PASSWORD=dot_pass
POSTGRES_DB=sidewalk_db

# API
JWT_SECRET=dev-secret-key-change-in-production
ENVIRONMENT=development

# Grafana
GRAFANA_ADMIN_PASSWORD=admin

# Logging
LOG_LEVEL=INFO
```

After changes:

```bash
# Rebuild and restart
docker-compose up -d --build
```

## Docker Image Sizes

Expected disk usage:

```
postgres:16         ~300MB
redis:7             ~50MB
prometheus          ~150MB
grafana             ~250MB
jaeger              ~100MB
api (built locally) ~500MB
minio               ~100MB

Total (approx):     ~1.5GB
+ volumes:          ~5GB (sample data, metrics)
```

## Persistence

### Data Volumes

All data is stored in Docker named volumes:

```
nyc_data_pgdata          # PostgreSQL data
nyc_data_redisdata       # Redis persistence
nyc_data_prometheus_data # Metrics
nyc_data_grafana_data    # Dashboards & configs
nyc_data_miniodata       # Object storage
```

View volumes:

```bash
docker volume ls | grep nyc_data
```

### Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U dot_user sidewalk_db > backup.sql

# Backup all volumes (advanced)
# See: https://docs.docker.com/storage/volumes/#backup-restore-or-migrate-data-volumes
```

## Getting Help

If you encounter issues:

1. **Check logs**: `docker-compose logs service_name`
2. **Verify Docker**: `docker ps` and `docker-compose ps`
3. **Review errors**: Look for error messages in startup output
4. **Restart services**: `docker-compose restart`
5. **Reset if needed**: `./scripts/docker-reset.sh`

For detailed debugging:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG docker-compose up -d

# Inspect service configuration
docker-compose config
```

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [API Documentation](INTEGRATION_QUICK_START.md)
- [Metrics Glossary](METRICS_GLOSSARY.md)
- [Architecture Documentation](COMPREHENSIVE_ARCHITECTURE_ASSESSMENT.md)
