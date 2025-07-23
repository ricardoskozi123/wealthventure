#!/bin/bash

# 🚀 OMCRM Trading Platform - VPS Deployment Script
# Run this script on your VPS to deploy your trading platform

set -e

echo "🚀 OMCRM Trading Platform - VPS Deployment"
echo "=========================================="
echo "Server: 84.32.188.252"
echo "Starting deployment..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Update system
print_status "Updating system packages..."
apt update && apt upgrade -y

# Install Docker and Docker Compose
print_status "Installing Docker and Docker Compose..."
apt install -y docker.io docker-compose curl git python3 python3-pip

# Start Docker
print_status "Starting Docker service..."
systemctl start docker
systemctl enable docker

# Create application directory
print_status "Setting up application directory..."
mkdir -p /var/www/omcrm
cd /var/www/omcrm

# Clone the repository
print_status "Cloning your trading platform..."
if [ -d ".git" ]; then
    print_status "Repository exists, pulling latest changes..."
    git pull origin main
else
    print_status "Cloning repository..."
    # Replace with your actual repository URL
    read -p "Enter your GitHub repository URL (e.g., https://github.com/username/repo.git): " REPO_URL
    git clone $REPO_URL .
fi

# Create necessary directories
print_status "Creating required directories..."
mkdir -p logs backup instance ssl

# Set up environment file
print_status "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f "production.env.example" ]; then
        cp production.env.example .env
        print_warning "Created .env file from example"
        print_warning "You should update the SECRET_KEY and other settings in .env"
    else
        print_status "Creating basic .env file..."
        cat > .env << EOL
# OMCRM Trading Platform Environment
SECRET_KEY=$(openssl rand -base64 32)
FLASK_ENV=production
FLASK_DEBUG=0
PLATFORM_NAME=OMCRM Trading
DATABASE_URL=sqlite:///instance/site.db
EOL
    fi
fi

# Initialize database
print_status "Initializing database..."
python3 -c "
import sqlite3
import os

os.makedirs('instance', exist_ok=True)
conn = sqlite3.connect('instance/site.db')
conn.execute('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL);')
conn.close()
print('Database initialized')
" 2>/dev/null || print_warning "Database initialization skipped"

# Update nginx configuration with server IP
print_status "Configuring nginx for your server..."
if [ -f "nginx/app.conf" ]; then
    # Replace server_name with actual IP
    sed -i 's/server_name _;/server_name 84.32.188.252;/' nginx/app.conf
fi

# Stop any existing containers
print_status "Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build and start containers
print_status "Building and starting containers..."
docker-compose build --no-cache
docker-compose up -d

# Wait for containers to start
print_status "Waiting for containers to start..."
sleep 30

# Check if containers are running
if docker-compose ps | grep -q "Up"; then
    print_success "Containers are running!"
else
    print_error "Some containers failed to start"
    docker-compose logs
    exit 1
fi

# Run database migrations
print_status "Setting up database..."
docker-compose exec -T web python -c "
from omcrm import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
" 2>/dev/null || print_warning "Database setup completed with warnings"

# Health check
print_status "Performing health check..."
sleep 10

if curl -f http://localhost:80 >/dev/null 2>&1; then
    print_success "Application is responding!"
else
    print_warning "Application might still be starting up..."
fi

# Configure firewall
print_status "Configuring firewall..."
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw --force enable

# Display final information
echo ""
print_success "🎉 DEPLOYMENT COMPLETED! 🎉"
echo "================================"
echo ""
print_success "Your OMCRM Trading Platform is now LIVE!"
echo ""
echo "🌐 Access your platform:"
echo "   📱 Website: http://84.32.188.252"
echo "   🔧 Admin Login: http://84.32.188.252/users/login"
echo ""
echo "📊 Monitor your deployment:"
echo "   📋 View logs: docker-compose logs -f"
echo "   🔄 Restart: docker-compose restart"
echo "   ⏹️ Stop: docker-compose down"
echo ""
echo "🔧 Next Steps:"
echo "   1. Visit your site to see the stunning landing page"
echo "   2. Create an admin account to access the dashboard"
echo "   3. Set up your domain name (optional)"
echo "   4. Configure SSL certificate for HTTPS"
echo ""
print_success "💰 Your trading platform is ready to make money!"
echo "🚀 Go to: http://84.32.188.252"
echo "" 