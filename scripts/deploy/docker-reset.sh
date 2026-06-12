#!/bin/bash

# NYC Data Toolkit - Docker Compose Reset Script
# CAUTION: Stops all services and DELETES all data volumes
# Use this to start fresh with a clean database

echo "========================================="
echo "NYC Data Toolkit - RESET DATA"
echo "========================================="
echo ""
echo "WARNING: This will DELETE all data in volumes"
echo "Including PostgreSQL, Redis, Prometheus, Grafana data"
echo ""

read -p "Are you sure? Type 'yes' to confirm: " confirm
if [ "$confirm" != "yes" ]; then
    echo "Reset cancelled."
    exit 0
fi

if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running."
    exit 1
fi

echo ""
echo "Stopping and removing all containers..."
docker-compose down -v

echo "Removing volumes..."
docker volume rm nyc_data_pgdata 2>/dev/null || true
docker volume rm nyc_data_redisdata 2>/dev/null || true
docker volume rm nyc_data_prometheus_data 2>/dev/null || true
docker volume rm nyc_data_grafana_data 2>/dev/null || true
docker volume rm nyc_data_miniodata 2>/dev/null || true

echo ""
echo "✓ All data has been reset."
echo ""
echo "To start fresh: ./scripts/docker-start.sh"
echo ""
