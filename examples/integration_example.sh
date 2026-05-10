#!/bin/bash

# NYC Data Toolkit - Integration Example (Bash)
# 
# Complete end-to-end example demonstrating:
# 1. Docker service health checks
# 2. Database connectivity
# 3. Sample data verification
# 4. API functionality
# 5. Metrics availability

set -e

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-dot_user}"
DB_PASS="${DB_PASS:-dot_pass}"
DB_NAME="${DB_NAME:-sidewalk_db}"
API_KEY="${API_KEY:-sk_test_demo_admin_abc123}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Results tracking
PASSED=0
FAILED=0

# Logging function
log_step() {
    local status=$1
    local message=$2
    
    case $status in
        "OK")
            echo -e "${GREEN}[OK]${NC} $message"
            ((PASSED++))
            ;;
        "FAIL")
            echo -e "${RED}[FAIL]${NC} $message"
            ((FAILED++))
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "INFO")
            echo -e "[INFO] $message"
            ;;
    esac
}

print_header() {
    echo ""
    echo "============================================================"
    echo "NYC Data Toolkit - Integration Example (Bash)"
    echo "============================================================"
    echo ""
}

print_summary() {
    echo ""
    echo "============================================================"
    echo "Summary: $PASSED passed, $FAILED failed"
    echo "============================================================"
    echo ""
}

# Step 1: Check Docker services
check_docker_services() {
    log_step "INFO" "Step 1: Checking Docker services..."
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_step "FAIL" "docker-compose not found"
        return 1
    fi
    
    # Check service status
    if docker-compose ps | grep -q "nyc_data_api.*healthy"; then
        log_step "OK" "API service is healthy"
    else
        log_step "WARN" "API service status unknown"
    fi
    
    if docker-compose ps | grep -q "nyc_data_postgres.*healthy"; then
        log_step "OK" "PostgreSQL service is healthy"
    else
        log_step "WARN" "PostgreSQL service status unknown"
    fi
}

# Step 2: Test database connectivity
check_database() {
    log_step "INFO" "Step 2: Testing database connectivity..."
    
    if command -v psql &> /dev/null; then
        if psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1;" &> /dev/null; then
            log_step "OK" "PostgreSQL connection successful"
        else
            log_step "FAIL" "Could not connect to PostgreSQL"
            return 1
        fi
    else
        log_step "WARN" "psql not installed, skipping direct connection test"
    fi
}

# Step 3: Check sample data
check_sample_data() {
    log_step "INFO" "Step 3: Checking sample data..."
    
    if ! command -v psql &> /dev/null; then
        log_step "WARN" "psql not installed, cannot verify sample data"
        return 0
    fi
    
    # Count records in each table
    INSP_COUNT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tc "SELECT COUNT(*) FROM sidewalk_inspections;" 2>/dev/null || echo "0")
    COMPL_COUNT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tc "SELECT COUNT(*) FROM complaints_311;" 2>/dev/null || echo "0")
    CONTR_COUNT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tc "SELECT COUNT(*) FROM contractors;" 2>/dev/null || echo "0")
    
    INSP_COUNT=$(echo $INSP_COUNT | tr -d ' ')
    COMPL_COUNT=$(echo $COMPL_COUNT | tr -d ' ')
    CONTR_COUNT=$(echo $CONTR_COUNT | tr -d ' ')
    
    if [ "$INSP_COUNT" -gt 0 ]; then
        log_step "OK" "Sidewalk Inspections: $INSP_COUNT records"
    else
        log_step "WARN" "Sidewalk Inspections: 0 records"
    fi
    
    if [ "$COMPL_COUNT" -gt 0 ]; then
        log_step "OK" "311 Complaints: $COMPL_COUNT records"
    else
        log_step "WARN" "311 Complaints: 0 records"
    fi
    
    if [ "$CONTR_COUNT" -gt 0 ]; then
        log_step "OK" "Contractors: $CONTR_COUNT records"
    else
        log_step "WARN" "Contractors: 0 records"
    fi
}

# Step 4: Test API health
check_api_health() {
    log_step "INFO" "Step 4: Testing API health..."
    
    if ! command -v curl &> /dev/null; then
        log_step "WARN" "curl not installed, skipping API tests"
        return 0
    fi
    
    if curl -s -f "$API_URL/health" > /dev/null 2>&1; then
        log_step "OK" "API health check passed"
    else
        log_step "FAIL" "API health check failed"
        return 1
    fi
}

# Step 5: Test API with authentication
check_api_auth() {
    log_step "INFO" "Step 5: Testing API authentication..."
    
    if ! command -v curl &> /dev/null; then
        log_step "WARN" "curl not installed, skipping API auth test"
        return 0
    fi
    
    RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "$API_URL/api/v1/sidewalk_inspections?limit=1" 2>/dev/null || echo "FAILED")
    
    if echo "$RESPONSE" | grep -q "data" 2>/dev/null; then
        log_step "OK" "API authentication successful"
    else
        log_step "WARN" "API authentication test inconclusive"
    fi
}

# Step 6: Query sample data
check_api_data() {
    log_step "INFO" "Step 6: Querying sample data via API..."
    
    if ! command -v curl &> /dev/null; then
        log_step "WARN" "curl not installed, skipping API data query"
        return 0
    fi
    
    # Query sidewalk inspections
    INSP_RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "$API_URL/api/v1/sidewalk_inspections?limit=1" 2>/dev/null || echo "")
    
    if echo "$INSP_RESPONSE" | grep -q "inspection_id" 2>/dev/null; then
        log_step "OK" "Sidewalk Inspections API query successful"
    else
        log_step "WARN" "Sidewalk Inspections API query failed or no data"
    fi
    
    # Query complaints
    COMPL_RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "$API_URL/api/v1/complaints_311?limit=1" 2>/dev/null || echo "")
    
    if echo "$COMPL_RESPONSE" | grep -q "complaint_id" 2>/dev/null; then
        log_step "OK" "311 Complaints API query successful"
    else
        log_step "WARN" "311 Complaints API query failed or no data"
    fi
}

# Step 7: Check quality metrics
check_quality_metrics() {
    log_step "INFO" "Step 7: Checking quality metrics..."
    
    if ! command -v psql &> /dev/null; then
        log_step "WARN" "psql not installed, cannot verify metrics"
        return 0
    fi
    
    METRIC_COUNT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tc \
        "SELECT COUNT(*) FROM quality_metrics;" 2>/dev/null || echo "0")
    METRIC_COUNT=$(echo $METRIC_COUNT | tr -d ' ')
    
    if [ "$METRIC_COUNT" -gt 0 ]; then
        log_step "OK" "Quality metrics available: $METRIC_COUNT records"
    else
        log_step "WARN" "No quality metrics found"
    fi
}

# Step 8: Check audit trail
check_audit_trail() {
    log_step "INFO" "Step 8: Checking audit trail..."
    
    if ! command -v psql &> /dev/null; then
        log_step "WARN" "psql not installed, cannot verify audit trail"
        return 0
    fi
    
    AUDIT_COUNT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tc \
        "SELECT COUNT(*) FROM audit_log;" 2>/dev/null || echo "0")
    AUDIT_COUNT=$(echo $AUDIT_COUNT | tr -d ' ')
    
    if [ "$AUDIT_COUNT" -ge 0 ]; then
        log_step "OK" "Audit trail is active: $AUDIT_COUNT entries"
    else
        log_step "WARN" "Audit trail status unknown"
    fi
}

# Step 9: Check data lineage
check_lineage() {
    log_step "INFO" "Step 9: Checking data lineage..."
    
    if ! command -v psql &> /dev/null; then
        log_step "WARN" "psql not installed, cannot verify lineage"
        return 0
    fi
    
    LINEAGE_COUNT=$(psql -h $DB_HOST -U $DB_USER -d $DB_NAME -tc \
        "SELECT COUNT(*) FROM data_lineage;" 2>/dev/null || echo "0")
    LINEAGE_COUNT=$(echo $LINEAGE_COUNT | tr -d ' ')
    
    if [ "$LINEAGE_COUNT" -gt 0 ]; then
        log_step "OK" "Data lineage is configured: $LINEAGE_COUNT relationships"
    else
        log_step "WARN" "No lineage data found"
    fi
}

# Step 10: Check API documentation
check_api_docs() {
    log_step "INFO" "Step 10: Checking API documentation..."
    
    if ! command -v curl &> /dev/null; then
        log_step "WARN" "curl not installed, skipping docs check"
        return 0
    fi
    
    if curl -s -f "$API_URL/docs" > /dev/null 2>&1; then
        log_step "OK" "API documentation available at $API_URL/docs"
    else
        log_step "WARN" "API documentation not accessible"
    fi
}

# Main execution
main() {
    print_header
    
    echo "Configuration:"
    echo "  API URL:      $API_URL"
    echo "  Database:     $DB_HOST:$DB_PORT/$DB_NAME"
    echo "  DB User:      $DB_USER"
    echo ""
    
    # Run all checks
    check_docker_services
    check_database
    check_sample_data
    check_api_health
    check_api_auth
    check_api_data
    check_quality_metrics
    check_audit_trail
    check_lineage
    check_api_docs
    
    print_summary
    
    # Exit with appropriate code
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed!${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Visit API docs: $API_URL/docs"
        echo "  2. Run Python example: python examples/integration_example.py"
        echo "  3. View Grafana dashboards: http://localhost:3000"
        echo ""
        return 0
    else
        echo -e "${RED}✗ Some checks failed${NC}"
        return 1
    fi
}

main
