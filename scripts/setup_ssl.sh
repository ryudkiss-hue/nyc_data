#!/bin/bash
# NYC DOT Toolkit - SSL/TLS Setup Script
# Creates self-signed certificates or configures production certificates

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=========================================="
echo "NYC DOT Toolkit - SSL/TLS Configuration"
echo "=========================================="
echo ""

# Step 1: Check for existing certificates
if [ -f "certs/server.crt" ] && [ -f "certs/server.key" ]; then
    log_warn "Certificates already exist"
    read -p "Do you want to regenerate? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Using existing certificates"
        exit 0
    fi
fi

# Create certs directory
mkdir -p certs

# Step 2: Choose certificate type
echo "Certificate Type:"
echo "1) Self-signed (for testing/development)"
echo "2) Let's Encrypt (free, production-ready)"
echo "3) Bring your own (paste path)"
read -p "Choose (1-3): " CERT_TYPE

case $CERT_TYPE in
    1)
        log_info "Generating self-signed certificate..."
        
        # Get domain/hostname
        read -p "Enter domain/hostname (or localhost): " DOMAIN
        DOMAIN=${DOMAIN:-localhost}
        
        # Generate private key
        openssl genrsa -out certs/server.key 2048
        
        # Generate self-signed certificate (valid 365 days)
        openssl req -new -x509 -key certs/server.key -out certs/server.crt \
            -days 365 -subj "/CN=$DOMAIN/O=NYC DOT/C=US"
        
        log_info "Self-signed certificate created"
        log_warn "⚠️ Self-signed certificates are NOT suitable for production"
        log_warn "⚠️ Browsers will show warnings"
        log_warn "⚠️ Use Let's Encrypt or proper CA for production"
        ;;
    
    2)
        log_info "Setting up Let's Encrypt..."
        log_info "This requires your domain to be publicly accessible"
        
        read -p "Enter your domain: " DOMAIN
        read -p "Enter your email: " EMAIL
        
        # Check if certbot is installed
        if ! command -v certbot &> /dev/null; then
            log_error "certbot not installed"
            log_info "Install with: sudo apt-get install certbot"
            exit 1
        fi
        
        # Get certificate
        log_info "Requesting certificate from Let's Encrypt..."
        sudo certbot certonly --standalone \
            -d "$DOMAIN" \
            --email "$EMAIL" \
            --agree-tos \
            --non-interactive
        
        # Copy to certs directory
        sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem certs/server.crt
        sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem certs/server.key
        sudo chmod 644 certs/server.crt certs/server.key
        
        log_info "Let's Encrypt certificate installed"
        log_info "⚠️ Certificate will auto-renew via Let's Encrypt"
        log_info "⚠️ Ensure renewal is configured in cron: certbot renew --quiet"
        ;;
    
    3)
        read -p "Enter path to certificate (.crt): " CERT_PATH
        read -p "Enter path to private key (.key): " KEY_PATH
        
        if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
            log_error "Certificate or key file not found"
            exit 1
        fi
        
        cp "$CERT_PATH" certs/server.crt
        cp "$KEY_PATH" certs/server.key
        chmod 644 certs/server.crt certs/server.key
        
        log_info "Certificates copied to certs/"
        ;;
    
    *)
        log_error "Invalid selection"
        exit 1
        ;;
esac

# Step 3: Verify certificates
log_info "Verifying certificate..."
openssl x509 -in certs/server.crt -text -noout | head -20

# Get expiration date
EXPIRY=$(openssl x509 -in certs/server.crt -noout -enddate | cut -d= -f2)
log_info "Certificate expires: $EXPIRY"

# Step 4: Update docker-compose.yml for HTTPS
log_info "Updating docker-compose configuration..."

cat >> docker-compose.yml << 'EOF'

  # Uncomment to enable HTTPS (after running setup_ssl.sh)
  # nginx:
  #   image: nginx:latest
  #   container_name: nyc_data_nginx
  #   ports:
  #     - "443:443"
  #     - "80:80"
  #   volumes:
  #     - ./certs:/etc/nginx/certs:ro
  #     - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
  #   depends_on:
  #     - api
  #     - app
  #   networks:
  #     - nyc_data

EOF

log_warn "HTTPS support requires nginx reverse proxy"
log_warn "To enable HTTPS:"
log_warn "1. Uncomment nginx service in docker-compose.yml"
log_warn "2. Create docker/nginx/nginx.conf (see below)"
log_warn "3. Run: docker-compose up -d nginx"

# Step 5: Create nginx config template
mkdir -p docker/nginx

cat > docker/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
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

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name _;

        ssl_certificate /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # API proxy
        location /api {
            proxy_pass http://api:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 60s;
        }

        # Streamlit proxy
        location / {
            proxy_pass http://app:8501;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Streamlit-specific settings
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 60s;
            proxy_buffering off;
        }
    }
}
EOF

log_info "nginx configuration template created at docker/nginx/nginx.conf"

# Step 6: Test certificate
log_info ""
log_info "Testing SSL certificate..."
if [ -f "certs/server.crt" ] && [ -f "certs/server.key" ]; then
    # Verify cert matches key
    CERT_MODULUS=$(openssl x509 -noout -modulus -in certs/server.crt | openssl md5)
    KEY_MODULUS=$(openssl rsa -noout -modulus -in certs/server.key | openssl md5)
    
    if [ "$CERT_MODULUS" = "$KEY_MODULUS" ]; then
        log_info "✓ Certificate and key match"
    else
        log_error "Certificate and key do not match!"
        exit 1
    fi
fi

# Step 7: Summary
echo ""
echo "=========================================="
echo "SSL/TLS Setup Complete"
echo "=========================================="
echo ""
echo "Certificates created:"
echo "  Certificate: certs/server.crt"
echo "  Private Key: certs/server.key"
echo ""
echo "Next steps:"
echo "1. Review docker/nginx/nginx.conf"
echo "2. Uncomment nginx service in docker-compose.yml"
echo "3. Run: docker-compose up -d nginx"
echo "4. Access at: https://$(hostname)"
echo ""
echo "For automatic renewal (Let's Encrypt):"
echo "  sudo certbot renew --quiet"
echo "  (Add to crontab: 0 3 * * * certbot renew --quiet)"
echo ""
