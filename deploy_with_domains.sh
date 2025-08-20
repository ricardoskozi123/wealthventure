#!/bin/bash

# Master Deployment Script for OMCRM Trading Platform
# Sets up multi-domain architecture with investmentprohub.com

set -e

# Configuration
PROJECT_DIR="/opt/omcrm"
CLIENT_DOMAIN="investmentprohub.com"
CRM_SUBDOMAIN="crm.investmentprohub.com"
EMAIL="admin@investmentprohub.com"

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

install_dependencies() {
    print_status "Installing system dependencies..."
    apt-get update
    apt-get install -y curl wget git python3 python3-pip postgresql-client
}

setup_project_directory() {
    print_status "Setting up project directory..."
    
    if [[ ! -d "$PROJECT_DIR" ]]; then
        mkdir -p "$PROJECT_DIR"
        print_success "Created project directory: $PROJECT_DIR"
    fi
    
    # Change to project directory
    cd "$PROJECT_DIR"
    
    # Create necessary directories
    mkdir -p logs backup ssl/investmentprohub.com scripts nginx
    chmod 755 logs backup ssl scripts
}

create_environment_file() {
    print_status "Creating environment configuration..."
    
    cat > .env << EOF
# Domain Configuration
CLIENT_DOMAIN=$CLIENT_DOMAIN
CRM_SUBDOMAIN=$CRM_SUBDOMAIN

# Flask Configuration
SECRET_KEY=omcrm-trading-$(date +%Y%m%d)-$(openssl rand -hex 8)
FLASK_ENV=production
FLASK_DEBUG=0

# Database Configuration
DATABASE_URL=postgresql://omcrm_user:omcrm_password_2024@db:5432/omcrm_trading

# Platform Configuration
PLATFORM_NAME=Investment Pro Hub
EOF
    
    print_success "Environment file created"
}

setup_backup_configuration() {
    print_status "Setting up backup configuration..."
    
    # Copy backup config if it doesn't exist
    if [[ ! -f "scripts/backup_config.json" ]]; then
        cat > scripts/backup_config.json << 'EOF'
{
  "database": {
    "type": "postgresql",
    "host": "db",
    "port": 5432,
    "name": "omcrm_trading",
    "user": "omcrm_user",
    "password": "omcrm_password_2024"
  },
  "storage": {
    "primary": "local",
    "backup_location": "/app/backup",
    "retention_days": 30,
    "compress": true
  },
  "digitalocean": {
    "enabled": false,
    "space": "omcrm-backups-your-unique-name",
    "region": "nyc3",
    "access_key": "",
    "secret_key": ""
  },
  "notifications": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "to_addresses": ["admin@investmentprohub.com"]
    }
  }
}
EOF
        print_success "Backup configuration created"
    fi
}

start_services() {
    print_status "Starting services..."
    
    # Stop any existing services
    if docker-compose ps > /dev/null 2>&1; then
        docker-compose down
    fi
    
    # Build and start services
    docker-compose build --no-cache
    docker-compose up -d
    
    print_success "Services started"
}

wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for database
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose exec -T db pg_isready -U omcrm_user > /dev/null 2>&1; then
            print_success "Database is ready"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Database failed to start"
            exit 1
        fi
        
        print_status "Waiting for database... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    # Wait for web application
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:5000 > /dev/null 2>&1; then
            print_success "Web application is ready"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Web application failed to start"
            exit 1
        fi
        
        print_status "Waiting for web application... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
}

show_next_steps() {
    local server_ip=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
    
    print_success "Deployment completed successfully!"
    echo
    print_status "🌐 NEXT STEPS:"
    echo
    echo "1. UPDATE DNS RECORDS:"
    echo "   Point these domains to your server IP ($server_ip):"
    echo "   $CLIENT_DOMAIN     A    $server_ip"
    echo "   $CRM_SUBDOMAIN     A    $server_ip"
    echo "   www.$CLIENT_DOMAIN A    $server_ip"
    echo
    echo "2. SETUP SSL CERTIFICATES:"
    echo "   cd $PROJECT_DIR"
    echo "   chmod +x scripts/setup_domains.sh"
    echo "   ./scripts/setup_domains.sh"
    echo
    echo "3. CONFIGURE BACKUPS:"
    echo "   Edit scripts/backup_config.json with your settings"
    echo "   Test backup: python3 scripts/backup_system.py"
    echo
    echo "4. ACCESS YOUR PLATFORM:"
    echo "   Client Trading: http://$server_ip (will be https://$CLIENT_DOMAIN after SSL)"
    echo "   Admin CRM:      http://$server_ip/login (will be https://$CRM_SUBDOMAIN/login)"
    echo
    echo "5. CONFIGURE DISASTER RECOVERY:"
    echo "   Edit scripts/disaster_recovery_config.json"
    echo "   Save your SSH keys securely"
    echo
    print_success "Your trading platform is ready! 🚀"
}

main() {
    print_status "Starting OMCRM Trading Platform deployment..."
    print_status "Client Domain: $CLIENT_DOMAIN"
    print_status "CRM Subdomain: $CRM_SUBDOMAIN"
    echo
    
    # Check if running as root
    check_root
    
    # Install dependencies
    install_dependencies
    
    # Setup project directory
    setup_project_directory
    
    # Create environment configuration
    create_environment_file
    
    # Setup backup configuration
    setup_backup_configuration
    
    # Start services
    start_services
    
    # Wait for services to be ready
    wait_for_services
    
    # Show next steps
    show_next_steps
}

# Show usage if help requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "OMCRM Trading Platform Deployment Script"
    echo
    echo "This script sets up the complete trading platform with:"
    echo "  • Multi-domain architecture (investmentprohub.com + crm.investmentprohub.com)"
    echo "  • PostgreSQL database"
    echo "  • Automated backup system"
    echo "  • Docker containerization"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo
    echo "Requirements:"
    echo "  • Ubuntu 20.04+ VPS with root access"
    echo "  • Docker and Docker Compose installed"
    echo "  • Domain 'investmentprohub.com' ready for DNS configuration"
    echo
    echo "After running this script, follow the displayed next steps to:"
    echo "  1. Configure DNS records"
    echo "  2. Setup SSL certificates"
    echo "  3. Configure backups"
    echo
    exit 0
fi

# Run main function
main 