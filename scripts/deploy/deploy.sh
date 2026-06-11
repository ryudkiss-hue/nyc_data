#!/bin/bash
# NYC DOT Sidewalk Data Governance Toolkit - Unix/Linux/MacOS Deployment Script
# Bash script for Linux, MacOS, and WSL environments

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Functions for output formatting
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    printf "${BOLD}${BLUE}%-64s${NC}\n" "$1" | sed 's/^/  /'
    echo -e "${BOLD}${BLUE}================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# Detect Docker Compose command
detect_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
    else
        return 1
    fi
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local all_ok=true
    
    # Check Docker
    if command -v docker &> /dev/null; then
        print_success "Docker is installed: $(docker --version)"
    else
        print_error "Docker not found. Install from https://www.docker.com"
        all_ok=false
    fi
    
    # Check Docker Compose
    if DOCKER_COMPOSE=$(detect_docker_compose); then
        print_success "Docker Compose is available: $($DOCKER_COMPOSE --version)"
        export DOCKER_COMPOSE
    else
        print_error "Docker Compose not found"
        all_ok=false
    fi
    
    # Check Python (optional)
    if command -v python3 &> /dev/null; then
        print_success "Python 3 is installed: $(python3 --version)"
    else
        print_warning "Python 3 not found (optional)"
    fi
    
    # Check Git (optional)
    if command -v git &> /dev/null; then
        print_success "Git is installed"
    else
        print_warning "Git not found (optional)"
    fi
    
    if [ "$all_ok" = false ]; then
        return 1
    fi
    return 0
}

# Setup function
setup() {
    print_header "NYC DOT Toolkit - Setup"
    
    # Create .env file if it doesn't exist
    if [ -f ".env.socrata" ]; then
        print_success ".env.socrata already exists"
    else
        print_info "Creating .env.socrata template..."
        cat > .env.socrata << 'EOF'
# Socrata Configuration
SOCRATA_DOMAIN=data.cityofnewyork.us
SOCRATA_APP_TOKEN=your_app_token_here

# PostgreSQL Configuration
POSTGRES_USER=dot_user
POSTGRES_PASSWORD=secure_password_change_this
POSTGRES_DB=sidewalk_db

# Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change_this_password

# Application Configuration
LOG_LEVEL=INFO
DEBUG=false
EOF
        print_success ".env.socrata created - please edit with your credentials"
    fi
    
    # Validate docker-compose.yml
    print_info "Validating docker-compose.yml..."
    if $DOCKER_COMPOSE config > /dev/null 2>&1; then
        print_success "docker-compose.yml is valid"
    else
        print_error "docker-compose.yml validation failed"
        return 1
    fi
    
    # Create necessary directories
    mkdir -p logs data/samples
    print_success "Created necessary directories"
    
    print_success "Setup complete! Run './deploy.sh start' to begin services"
}

# Start services
start_services() {
    local service=$1
    
    print_header "Starting Services"
    
    if ! check_prerequisites; then
        print_error "Prerequisites not met"
        return 1
    fi
    
    print_info "Starting Docker services..."
    if [ -z "$service" ]; then
        $DOCKER_COMPOSE up -d
    else
        $DOCKER_COMPOSE up -d "$service"
    fi
    
    print_success "Services started successfully"
    
    print_info "Access services at:"
    echo "  PostgreSQL:  localhost:5432"
    echo "  Prometheus:  http://localhost:9090"
    echo "  Grafana:     http://localhost:3000 (admin/admin)"
    echo "  Jaeger:      http://localhost:16686"
    echo "  Redis:       localhost:6379"
    echo ""
    
    # Wait for services
    print_info "Waiting for services to be ready..."
    sleep 5
    
    print_info "Service status:"
    $DOCKER_COMPOSE ps
}

# Stop services
stop_services() {
    local service=$1
    local remove_volumes=$2
    
    print_header "Stopping Services"
    
    if [ "$remove_volumes" = "true" ]; then
        print_warning "Stopping services and removing volumes..."
        if [ -z "$service" ]; then
            $DOCKER_COMPOSE down -v
        else
            $DOCKER_COMPOSE down -v "$service"
        fi
        print_success "Volumes removed"
    else
        if [ -z "$service" ]; then
            $DOCKER_COMPOSE down
        else
            $DOCKER_COMPOSE down "$service"
        fi
    fi
    
    print_success "Services stopped"
}

# Show status
show_status() {
    print_header "Service Status"
    
    $DOCKER_COMPOSE ps
}

# Show logs
show_logs() {
    local service=$1
    
    print_header "Service Logs"
    
    if [ -z "$service" ]; then
        $DOCKER_COMPOSE logs -f
    else
        $DOCKER_COMPOSE logs -f "$service"
    fi
}

# Clean environment
clean_environment() {
    print_header "Cleaning Environment"
    
    print_warning "This will stop all containers and remove volumes (destructive)"
    
    $DOCKER_COMPOSE down -v
    
    print_success "Environment cleaned"
}

# Restart services
restart_services() {
    local service=$1
    
    print_header "Restarting Services"
    
    if [ -z "$service" ]; then
        $DOCKER_COMPOSE restart
    else
        $DOCKER_COMPOSE restart "$service"
    fi
    
    print_success "Services restarted"
}

# Build images
build_images() {
    print_header "Building Docker Images"
    
    $DOCKER_COMPOSE build
    
    print_success "Images built successfully"
}

# Show help
show_help() {
    print_header "NYC DOT Toolkit - Deployment Help"
    
    cat << 'EOF'
USAGE:
    ./deploy.sh [action] [options]

ACTIONS:
    setup       Initialize configuration files and environment
    start       Start Docker services
    stop        Stop Docker services
    status      Show current service status
    logs        Show service logs (Ctrl+C to exit)
    restart     Restart Docker services
    build       Build Docker images
    clean       Stop services and remove volumes (destructive)
    help        Show this help message

OPTIONS:
    -s, --service <name>  Specific service to operate on (postgres, api, etc.)
    -v, --volumes         Remove volumes when stopping (use with 'stop')
    -d, --dev             Development mode (more verbose logging)

EXAMPLES:
    # Initial setup
    ./deploy.sh setup

    # Start all services
    ./deploy.sh start

    # Start only PostgreSQL
    ./deploy.sh start --service postgres

    # Stop services and remove volumes
    ./deploy.sh stop --volumes

    # View logs
    ./deploy.sh logs

    # View logs for specific service
    ./deploy.sh logs --service postgres

    # Restart services
    ./deploy.sh restart

    # Build images
    ./deploy.sh build

    # Clean everything
    ./deploy.sh clean

FIRST TIME SETUP:
    1. Run: ./deploy.sh setup
    2. Edit .env.socrata with your credentials
    3. Run: ./deploy.sh start
    4. Access services at the URLs printed above

TROUBLESHOOTING:
    - If Docker won't start: Ensure Docker daemon is running
    - Check logs: ./deploy.sh logs --service <service>
    - Full system logs: ./deploy.sh logs
    - Check status: ./deploy.sh status
    - Restart service: ./deploy.sh restart --service <service>

SERVICES:
    postgres    PostgreSQL database with PostGIS
    redis       Redis cache
    prometheus  Prometheus metrics collector
    grafana     Grafana dashboards
    jaeger      Jaeger distributed tracing
    api         FastAPI application server

EOF
}

# Main script logic
main() {
    local action="${1:-help}"
    local service=""
    local remove_volumes=false
    local dev_mode=false
    
    # Parse arguments
    shift || true
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -s|--service)
                service="$2"
                shift 2
                ;;
            -v|--volumes)
                remove_volumes=true
                shift
                ;;
            -d|--dev)
                dev_mode=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Detect Docker Compose
    if ! DOCKER_COMPOSE=$(detect_docker_compose); then
        print_error "Docker Compose not found"
        show_help
        exit 1
    fi
    
    # Route commands
    case "$action" in
        setup)
            setup
            ;;
        start)
            start_services "$service"
            ;;
        stop)
            stop_services "$service" "$remove_volumes"
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$service"
            ;;
        restart)
            restart_services "$service"
            ;;
        build)
            build_images
            ;;
        clean)
            clean_environment
            ;;
        help)
            show_help
            ;;
        *)
            print_error "Unknown action: $action"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
