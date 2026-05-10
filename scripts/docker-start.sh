#!/bin/bash

# NYC Data Toolkit - Docker Compose Startup Script
# Starts all services and waits for them to be healthy

set -e

echo "========================================="
echo "NYC Data Toolkit - Docker Environment"
echo "Starting all services..."
echo "========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running. Please start Docker and try again."
    exit 1
fi

# Start services
echo "[1/5] Starting PostgreSQL, Redis, Prometheus, Grafana, Jaeger, API, and MinIO..."
docker-compose up -d

# Wait for services to be healthy
echo ""
echo "[2/5] Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U dot_user -d sidewalk_db > /dev/null 2>&1; then
        echo "✓ PostgreSQL is healthy"
        break
    fi
    echo "  Attempt $i/30 - waiting..."
    sleep 2
done

echo "[3/5] Waiting for Redis to be ready..."
for i in {1..20}; do
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✓ Redis is healthy"
        break
    fi
    echo "  Attempt $i/20 - waiting..."
    sleep 2
done

echo "[4/5] Waiting for API to be ready..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API is healthy"
        break
    fi
    echo "  Attempt $i/30 - waiting..."
    sleep 2
done

echo "[5/5] Checking all services..."
echo ""

# Display service status
docker-compose ps

echo ""
echo "========================================="
echo "✓ All services are running!"
echo "========================================="
echo ""
echo "Service URLs:"
echo "  • API Documentation:    http://localhost:8000/docs"
echo "  • API Redoc:            http://localhost:8000/redoc"
echo "  • Grafana Dashboards:   http://localhost:3000 (admin/admin)"
echo "  • Prometheus Metrics:   http://localhost:9090"
echo "  • Jaeger Tracing:       http://localhost:16686"
echo "  • MinIO Storage:        http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "Database Connection:"
echo "  • Host:     localhost"
echo "  • Port:     5432"
echo "  • Database: sidewalk_db"
echo "  • User:     dot_user"
echo "  • Password: dot_pass"
echo ""
echo "Next Steps:"
echo "  1. View API docs: http://localhost:8000/docs"
echo "  2. Run integration example: python examples/integration_example.py"
echo "  3. Check sample data: curl -H 'Authorization: Bearer sk_test_demo_admin_abc123' http://localhost:8000/api/v1/sidewalk_inspections?limit=5"
echo ""
echo "To stop services: ./scripts/docker-stop.sh"
echo "To reset data:    ./scripts/docker-reset.sh"
echo ""
