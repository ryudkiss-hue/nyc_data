#!/bin/bash
# NYC DOT Toolkit - PostgreSQL Automated Backup Script
# Creates daily backups with compression, rotation, and optional S3 upload

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-.}/backups"
POSTGRES_USER="${POSTGRES_USER:-dot_user}"
POSTGRES_DB="${POSTGRES_DB:-sidewalk_db}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"
DOCKER_COMPOSE_PATH="${DOCKER_COMPOSE_PATH:-.}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/sidewalk_db_${TIMESTAMP}.sql"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

log_info "Starting PostgreSQL backup..."
log_info "Database: $POSTGRES_DB"
log_info "Host: $POSTGRES_HOST"
log_info "User: $POSTGRES_USER"
log_info "Output: $BACKUP_FILE_GZ"

# Check if using Docker
if [ -f "$DOCKER_COMPOSE_PATH/docker-compose.yml" ]; then
    log_info "Docker Compose detected - using docker-compose exec"
    
    # Check if Docker is running
    if ! docker-compose -f "$DOCKER_COMPOSE_PATH/docker-compose.yml" ps | grep postgres > /dev/null; then
        log_error "PostgreSQL container is not running"
        exit 1
    fi
    
    # Create backup using docker-compose
    log_info "Dumping database..."
    docker-compose -f "$DOCKER_COMPOSE_PATH/docker-compose.yml" exec -T postgres \
        pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"
else
    log_info "Using local PostgreSQL connection..."
    
    # Set password if provided
    if [ -n "$POSTGRES_PASSWORD" ]; then
        export PGPASSWORD="$POSTGRES_PASSWORD"
    fi
    
    # Create backup using local psql
    log_info "Dumping database..."
    pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"
fi

# Check backup was successful
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup failed - file not created"
    exit 1
fi

# Compress backup
log_info "Compressing backup..."
gzip "$BACKUP_FILE"

if [ ! -f "$BACKUP_FILE_GZ" ]; then
    log_error "Compression failed"
    exit 1
fi

# Get file size
BACKUP_SIZE=$(du -h "$BACKUP_FILE_GZ" | cut -f1)
log_info "Backup complete: $BACKUP_FILE_GZ ($BACKUP_SIZE)"

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    log_info "Uploading to S3 bucket: $S3_BUCKET"
    
    if command -v aws &> /dev/null; then
        if aws s3 cp "$BACKUP_FILE_GZ" "s3://$S3_BUCKET/postgres/" ; then
            log_info "S3 upload successful"
        else
            log_error "S3 upload failed"
            exit 1
        fi
    else
        log_warn "AWS CLI not found - skipping S3 upload"
    fi
fi

# Rotate old backups
log_info "Rotating backups (keeping last $RETENTION_DAYS days)..."
DELETED_COUNT=0

find "$BACKUP_DIR" -name "sidewalk_db_*.sql.gz" -mtime "+$RETENTION_DAYS" | while read old_backup; do
    log_info "Deleting old backup: $(basename $old_backup)"
    rm -f "$old_backup"
    ((DELETED_COUNT++))
done

# Backup verification - restore to test database (optional)
if [ "${VERIFY_BACKUP:-false}" = "true" ]; then
    log_info "Verifying backup by testing restore..."
    
    if [ -f "$DOCKER_COMPOSE_PATH/docker-compose.yml" ]; then
        log_info "Creating test database..."
        docker-compose -f "$DOCKER_COMPOSE_PATH/docker-compose.yml" exec -T postgres \
            createdb -U "$POSTGRES_USER" test_restore 2>/dev/null || true
        
        log_info "Testing restore..."
        cat "$BACKUP_FILE_GZ" | gunzip | docker-compose -f "$DOCKER_COMPOSE_PATH/docker-compose.yml" exec -T postgres \
            psql -U "$POSTGRES_USER" test_restore > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            log_info "Backup verification successful"
            docker-compose -f "$DOCKER_COMPOSE_PATH/docker-compose.yml" exec -T postgres \
                dropdb -U "$POSTGRES_USER" test_restore
        else
            log_warn "Backup verification failed - restore test unsuccessful"
        fi
    fi
fi

# Summary
log_info "Backup Summary:"
echo "  Backup file: $BACKUP_FILE_GZ"
echo "  Size: $BACKUP_SIZE"
echo "  Timestamp: $TIMESTAMP"
echo "  Location: $BACKUP_DIR"

if [ -n "$S3_BUCKET" ]; then
    echo "  S3 location: s3://$S3_BUCKET/postgres/"
fi

echo "  Retention: $RETENTION_DAYS days"

# Exit with success
log_info "Backup completed successfully"
exit 0
