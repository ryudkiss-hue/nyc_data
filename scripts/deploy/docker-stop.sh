#!/bin/bash

# NYC Data Toolkit - Docker Compose Stop Script
# Stops all services (data is preserved)

echo "========================================="
echo "NYC Data Toolkit - Stopping Services"
echo "========================================="
echo ""

if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running."
    exit 1
fi

echo "Stopping all services..."
docker-compose down

echo ""
echo "✓ All services stopped. Data is preserved in volumes."
echo ""
echo "To restart:      ./scripts/docker-start.sh"
echo "To reset data:   ./scripts/docker-reset.sh"
echo ""
