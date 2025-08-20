#!/bin/bash

# Domain Setup Script for OMCRM Trading Platform
# Sets up investmentprohub.com and crm.investmentprohub.com with SSL

set -e

# Configuration
CLIENT_DOMAIN="investmentprohub.com"
CRM_SUBDOMAIN="crm.investmentprohub.com"
EMAIL="admin@investmentprohub.com"
STAGING=${STAGING:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
}

install_certbot() {
    print_status "Installing Certbot..."
    apt-get update
    apt-get install -y certbot
    print_success "Certbot installed"
}

stop_nginx() {
    print_status "Stopping nginx to free port 80..."
    if docker-compose ps | grep nginx; then
        docker-compose stop nginx
    fi
}

start_nginx() {
    print_status "Starting nginx..."
    docker-compose up -d nginx
    print_success "Nginx started"
}

get_ssl_certificate() {
    local domain=$1
    print_status "Getting SSL certificate for $domain..."
    
    local staging_flag=""
    if [[ "$STAGING" == "true" ]]; then
        staging_flag="--staging"
        print_warning "Using Let's Encrypt staging environment"
    fi
    
    certbot certonly \
        --standalone \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        $staging_flag \
        -d "$domain"
    
    if [[ $? -eq 0 ]]; then
        print_success "SSL certificate obtained for $domain"
    else
        print_error "Failed to get SSL certificate for $domain"
        exit 1
    fi
}

setup_ssl_directories() {
    print_status "Setting up SSL directories..."
    mkdir -p /opt/omcrm/ssl/investmentprohub.com
    
    # Copy certificates to nginx directory
    if [[ -d "/etc/letsencrypt/live/$CLIENT_DOMAIN" ]]; then
        cp "/etc/letsencrypt/live/$CLIENT_DOMAIN/fullchain.pem" "/opt/omcrm/ssl/investmentprohub.com/cert.pem"
        cp "/etc/letsencrypt/live/$CLIENT_DOMAIN/privkey.pem" "/opt/omcrm/ssl/investmentprohub.com/key.pem"
        chmod 644 /opt/omcrm/ssl/investmentprohub.com/*.pem
        print_success "SSL certificates copied to nginx directory"
    else
        print_error "SSL certificates not found for $CLIENT_DOMAIN"
        exit 1
    fi
}

setup_nginx_config() {
    print_status "Setting up nginx configuration..."
    
    # Backup original config
    if [[ -f "/opt/omcrm/nginx/app.conf" ]]; then
        cp "/opt/omcrm/nginx/app.conf" "/opt/omcrm/nginx/app.conf.backup"
    fi
    
    # Copy multi-domain config
    cp "/opt/omcrm/nginx/multi_domain.conf" "/opt/omcrm/nginx/app.conf"
    print_success "Nginx configuration updated"
}

create_cron_backup() {
    print_status "Setting up automated backups..."
    
    # Create backup script
    cat > /opt/omcrm/scripts/daily_backup.sh << 'EOF'
#!/bin/bash
cd /opt/omcrm
python3 scripts/backup_system.py
EOF
    
    chmod +x /opt/omcrm/scripts/daily_backup.sh
    
    # Add to crontab (run at 2 AM daily)
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/omcrm/scripts/daily_backup.sh >> /var/log/omcrm-backup.log 2>&1") | crontab -
    
    print_success "Daily backup scheduled for 2:00 AM"
}

create_cert_renewal() {
    print_status "Setting up SSL certificate auto-renewal..."
    
    # Create renewal script
    cat > /opt/omcrm/scripts/renew_certs.sh << EOF
#!/bin/bash
# Stop nginx
docker-compose -f /opt/omcrm/docker-compose.yml stop nginx

# Renew certificates
certbot renew --standalone

# Copy renewed certificates
if [[ -d "/etc/letsencrypt/live/$CLIENT_DOMAIN" ]]; then
    cp "/etc/letsencrypt/live/$CLIENT_DOMAIN/fullchain.pem" "/opt/omcrm/ssl/investmentprohub.com/cert.pem"
    cp "/etc/letsencrypt/live/$CLIENT_DOMAIN/privkey.pem" "/opt/omcrm/ssl/investmentprohub.com/key.pem"
    chmod 644 /opt/omcrm/ssl/investmentprohub.com/*.pem
fi

# Start nginx
docker-compose -f /opt/omcrm/docker-compose.yml up -d nginx
EOF
    
    chmod +x /opt/omcrm/scripts/renew_certs.sh
    
    # Add to crontab (run every Sunday at 3 AM)
    (crontab -l 2>/dev/null; echo "0 3 * * 0 /opt/omcrm/scripts/renew_certs.sh >> /var/log/omcrm-ssl-renewal.log 2>&1") | crontab -
    
    print_success "SSL certificate auto-renewal configured"
}

verify_domains() {
    print_status "Verifying domain configuration..."
    
    # Test HTTP redirect
    local http_test=$(curl -s -I "http://$CLIENT_DOMAIN" | grep "Location:" | grep "https://")
    if [[ -n "$http_test" ]]; then
        print_success "HTTP to HTTPS redirect working for $CLIENT_DOMAIN"
    else
        print_warning "HTTP to HTTPS redirect may not be working for $CLIENT_DOMAIN"
    fi
    
    # Test HTTPS
    if curl -s -k "https://$CLIENT_DOMAIN" > /dev/null; then
        print_success "HTTPS working for $CLIENT_DOMAIN"
    else
        print_warning "HTTPS may not be working for $CLIENT_DOMAIN"
    fi
    
    if curl -s -k "https://$CRM_SUBDOMAIN" > /dev/null; then
        print_success "HTTPS working for $CRM_SUBDOMAIN"
    else
        print_warning "HTTPS may not be working for $CRM_SUBDOMAIN"
    fi
}

main() {
    print_status "Starting domain setup for OMCRM Trading Platform"
    print_status "Client Domain: $CLIENT_DOMAIN"
    print_status "CRM Subdomain: $CRM_SUBDOMAIN"
    echo
    
    # Check if running as root
    check_root
    
    # Change to project directory
    cd /opt/omcrm
    
    # Install dependencies
    install_certbot
    
    # Stop nginx to free port 80
    stop_nginx
    
    # Get SSL certificates
    get_ssl_certificate "$CLIENT_DOMAIN"
    get_ssl_certificate "$CRM_SUBDOMAIN"
    
    # Setup SSL directories and files
    setup_ssl_directories
    
    # Update nginx configuration
    setup_nginx_config
    
    # Start nginx with new configuration
    start_nginx
    
    # Setup automated backups
    create_cron_backup
    
    # Setup SSL renewal
    create_cert_renewal
    
    # Wait a moment for nginx to start
    sleep 10
    
    # Verify configuration
    verify_domains
    
    print_success "Domain setup completed successfully!"
    echo
    print_status "Next steps:"
    echo "1. Update your DNS records to point both domains to this server:"
    echo "   $CLIENT_DOMAIN     A    $(curl -s ifconfig.me)"
    echo "   $CRM_SUBDOMAIN     A    $(curl -s ifconfig.me)"
    echo
    echo "2. Test your domains:"
    echo "   Client site: https://$CLIENT_DOMAIN"
    echo "   Admin CRM:   https://$CRM_SUBDOMAIN/login"
    echo
    echo "3. Configure backup settings in scripts/backup_config.json"
    echo
    print_success "Setup complete! 🎉"
}

# Show usage if no arguments
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --staging    Use Let's Encrypt staging environment (for testing)"
    echo
    echo "Environment variables:"
    echo "  CLIENT_DOMAIN=$CLIENT_DOMAIN"
    echo "  CRM_SUBDOMAIN=$CRM_SUBDOMAIN"
    echo "  EMAIL=$EMAIL"
    echo
    echo "Example:"
    echo "  $0                    # Production certificates"
    echo "  $0 --staging          # Staging certificates (for testing)"
    exit 0
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --staging)
            STAGING=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main 