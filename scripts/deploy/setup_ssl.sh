#!/bin/bash
# Let's Encrypt SSL/TLS Certificate Setup Script
# For NYC Sidewalk Toolkit production deployment
# Supports: Development (self-signed), Let's Encrypt (free), and Enterprise (manual)

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CERT_DIR="${CERT_DIR:-.}/certs"
NGINX_CONF_DIR="${NGINX_CONF_DIR:-.}/docker/nginx"
DOMAIN="${DOMAIN:-localhost}"
EMAIL="${EMAIL:-admin@example.com}"
CERT_TYPE="${CERT_TYPE:-self-signed}"

# Functions
print_header() {
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if openssl is installed
    if ! command -v openssl &> /dev/null; then
        print_error "OpenSSL is not installed"
        print_info "Install with: apt-get install openssl (Linux) or brew install openssl (macOS)"
        exit 1
    fi
    print_success "OpenSSL found: $(openssl version)"
    
    # Check if Docker is installed (optional)
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found (optional, only needed for Nginx)"
    else
        print_success "Docker found: $(docker --version)"
    fi
    
    # Check if Certbot is installed (only for Let's Encrypt)
    if [ "$CERT_TYPE" = "letsencrypt" ]; then
        if ! command -v certbot &> /dev/null; then
            print_error "Certbot is not installed"
            print_info "Install with: apt-get install certbot (Linux) or brew install certbot (macOS)"
            exit 1
        fi
        print_success "Certbot found: $(certbot --version)"
    fi
}

# Create certificate directory
create_cert_directory() {
    print_header "Creating Certificate Directory"
    
    mkdir -p "$CERT_DIR"
    chmod 700 "$CERT_DIR"
    print_success "Certificate directory created: $CERT_DIR"
}

# Generate self-signed certificate (Development)
generate_self_signed() {
    print_header "Generating Self-Signed Certificate"
    
    local CERT_FILE="$CERT_DIR/server.crt"
    local KEY_FILE="$CERT_DIR/server.key"
    
    print_info "Generating RSA private key (4096-bit)..."
    openssl genrsa -out "$KEY_FILE" 4096
    
    print_info "Generating self-signed certificate (365 days)..."
    openssl req -new -x509 -key "$KEY_FILE" -out "$CERT_FILE" -days 365 \
        -subj "/C=US/ST=New York/L=New York/O=NYC DOT/CN=$DOMAIN"
    
    chmod 600 "$KEY_FILE"
    chmod 644 "$CERT_FILE"
    
    print_success "Self-signed certificate generated"
    print_info "Certificate: $CERT_FILE"
    print_info "Private Key: $KEY_FILE"
    
    # Display certificate info
    print_info "\nCertificate Details:"
    openssl x509 -in "$CERT_FILE" -text -noout | grep -A 2 "Not Before\|Not After\|Subject:"
}

# Generate Let's Encrypt certificate (Production)
generate_letsencrypt() {
    print_header "Generating Let's Encrypt Certificate"
    
    # Check if certificate already exists
    CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    if [ -f "$CERT_PATH" ]; then
        print_warning "Certificate already exists for $DOMAIN"
        read -p "Renew certificate? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Renewing certificate..."
            certbot renew --force-renewal
        fi
        return
    fi
    
    print_info "Domain: $DOMAIN"
    print_info "Email: $EMAIL"
    print_info "Using Let's Encrypt standalone validation..."
    
    # Stop any service using port 80
    print_warning "Port 80 must be available for validation"
    read -p "Stop services on port 80? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Port 80 must be available"
        return 1
    fi
    
    # Generate certificate
    certbot certonly --standalone \
        -d "$DOMAIN" \
        -d "*.$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        --rsa-key-size 4096
    
    print_success "Let's Encrypt certificate generated"
    print_info "Certificate: $CERT_PATH"
    
    # Copy to certs directory
    print_info "Copying certificate to $CERT_DIR..."
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_DIR/server.crt"
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$CERT_DIR/server.key"
    chmod 600 "$CERT_DIR/server.key"
    
    # Set up auto-renewal
    print_info "Setting up auto-renewal..."
    echo "0 3 * * * certbot renew --quiet && docker exec nyc_data_nginx nginx -s reload" | crontab -
    print_success "Auto-renewal cron job added (3 AM daily)"
}

# Generate CSR for enterprise certificate
generate_enterprise_csr() {
    print_header "Generating Enterprise Certificate Signing Request"
    
    local CSR_FILE="$CERT_DIR/server.csr"
    local KEY_FILE="$CERT_DIR/server.key"
    
    print_info "Generating private key..."
    openssl genrsa -out "$KEY_FILE" 4096
    
    print_info "Generating CSR..."
    openssl req -new -key "$KEY_FILE" -out "$CSR_FILE" \
        -subj "/C=US/ST=New York/L=New York/O=NYC DOT/CN=$DOMAIN"
    
    print_success "CSR generated: $CSR_FILE"
    print_info "Submit this CSR to your Certificate Authority (CA)"
    print_info "Once you receive the signed certificate, place it in: $CERT_DIR/server.crt"
    
    echo ""
    echo "CSR Content:"
    cat "$CSR_FILE"
}

# Create Nginx configuration
create_nginx_config() {
    print_header "Creating Nginx Configuration"
    
    mkdir -p "$NGINX_CONF_DIR"
    
    cat > "$NGINX_CONF_DIR/nginx.conf" << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=web_limit:10m rate=30r/s;
    
    # SSL/TLS Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    
    # Upstream services
    upstream api_backend {
        least_conn;
        server api:8000 max_fails=3 fail_timeout=30s;
    }
    
    upstream web_backend {
        least_conn;
        server app:8501 max_fails=3 fail_timeout=30s;
    }
    
    # HTTP redirect to HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }
    
    # HTTPS server (API)
    server {
        listen 443 ssl http2;
        server_name api.* ~^api\..*;
        
        ssl_certificate /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        
        client_max_body_size 100M;
        
        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;
        
        # Health check endpoint (no auth required)
        location /health {
            proxy_pass http://api_backend;
            access_log off;
        }
        
        # Metrics endpoint (protected)
        location /metrics {
            proxy_pass http://api_backend;
            auth_basic "Restricted";
            auth_basic_user_file /etc/nginx/.htpasswd;
        }
        
        # API endpoints
        location / {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
    
    # HTTPS server (Web)
    server {
        listen 443 ssl http2;
        server_name ~^(www\.)?.*;
        
        ssl_certificate /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;
        
        # Rate limiting
        limit_req zone=web_limit burst=50 nodelay;
        
        location / {
            proxy_pass http://web_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
EOF
    
    print_success "Nginx configuration created: $NGINX_CONF_DIR/nginx.conf"
}

# Verify certificate
verify_certificate() {
    print_header "Verifying Certificate"
    
    local CERT_FILE="$CERT_DIR/server.crt"
    local KEY_FILE="$CERT_DIR/server.key"
    
    if [ ! -f "$CERT_FILE" ]; then
        print_error "Certificate file not found: $CERT_FILE"
        return 1
    fi
    
    if [ ! -f "$KEY_FILE" ]; then
        print_error "Private key file not found: $KEY_FILE"
        return 1
    fi
    
    print_info "Certificate Information:"
    openssl x509 -in "$CERT_FILE" -text -noout | grep -E "Subject:|Issuer:|Not Before|Not After|Public-Key:"
    
    print_info "\nVerifying certificate and key match..."
    CERT_MODULUS=$(openssl x509 -noout -modulus -in "$CERT_FILE" | openssl md5)
    KEY_MODULUS=$(openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5)
    
    if [ "$CERT_MODULUS" = "$KEY_MODULUS" ]; then
        print_success "Certificate and private key match"
    else
        print_error "Certificate and private key do NOT match"
        return 1
    fi
    
    # Check certificate expiry
    EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
    print_info "Certificate expires: $EXPIRY"
}

# Setup Docker volumes
setup_docker_volumes() {
    print_header "Setting Up Docker Volumes"
    
    print_info "Creating certificate volume..."
    docker volume create nyc_sidewalk_certs 2>/dev/null || true
    
    print_info "Copying certificates to volume..."
    docker run --rm \
        -v "$CERT_DIR":/source \
        -v nyc_sidewalk_certs:/dest \
        alpine:latest \
        cp -v /source/* /dest/
    
    print_success "Certificates copied to Docker volume"
}

# Main menu
show_menu() {
    echo ""
    echo "SSL/TLS Certificate Setup for NYC Sidewalk Toolkit"
    echo "=================================================="
    echo "1) Self-Signed Certificate (Development)"
    echo "2) Let's Encrypt Certificate (Production - Free)"
    echo "3) Enterprise Certificate CSR (Manual)"
    echo "4) Verify Existing Certificate"
    echo "5) Create Nginx Configuration"
    echo "6) Setup Docker Volumes"
    echo "7) Exit"
    echo ""
    read -p "Select option (1-7): " choice
}

# Main script
main() {
    print_header "NYC Sidewalk Toolkit - SSL/TLS Setup"
    
    check_prerequisites
    create_cert_directory
    
    while true; do
        show_menu
        case $choice in
            1)
                generate_self_signed
                ;;
            2)
                print_info "Let's Encrypt setup requires:"
                print_info "1. Domain registered and pointing to server"
                print_info "2. Port 80 available"
                read -p "Domain name: " DOMAIN
                read -p "Admin email: " EMAIL
                generate_letsencrypt
                ;;
            3)
                read -p "Domain name: " DOMAIN
                generate_enterprise_csr
                ;;
            4)
                verify_certificate
                ;;
            5)
                create_nginx_config
                ;;
            6)
                setup_docker_volumes
                ;;
            7)
                print_success "Setup complete!"
                print_info "Next steps:"
                print_info "1. Update docker-compose.yml with certificate paths"
                print_info "2. Uncomment nginx service in docker-compose.yml"
                print_info "3. Run: docker-compose up -d nginx"
                print_info "4. Test: curl https://localhost/ --insecure"
                exit 0
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac
    done
}

# Run main function
main
