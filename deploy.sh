#!/bin/bash

# 🚀 OMCRM Trading Platform - One-Click Deployment Script
# This script automates the entire deployment process

set -e  # Exit on any error

echo "🚀 Starting OMCRM Trading Platform Deployment..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    directories=("logs" "backup" "instance" "ssl")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        fi
    done
}

# Initialize database
init_database() {
    print_status "Initializing database..."
    
    if [ ! -f "instance/site.db" ]; then
        print_status "Creating new database..."
        # Create a basic SQLite database
        python3 -c "
import sqlite3
import os

# Ensure instance directory exists
os.makedirs('instance', exist_ok=True)

# Create database
conn = sqlite3.connect('instance/site.db')
conn.execute('CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL);')
conn.close()
print('Database initialized successfully')
"
        print_success "Database created"
    else
        print_success "Database already exists"
    fi
}

# Set up environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    if [ ! -f ".env" ]; then
        if [ -f "production.env.example" ]; then
            cp production.env.example .env
            print_warning "Created .env file from example. Please update the values!"
            print_warning "IMPORTANT: Change the SECRET_KEY in .env file!"
        else
            print_error "No environment file found. Please create .env file manually."
            exit 1
        fi
    else
        print_success "Environment file already exists"
    fi
}

# Build and start containers
deploy_containers() {
    print_status "Building and starting Docker containers..."
    
    # Stop existing containers
    print_status "Stopping existing containers..."
    docker-compose down 2>/dev/null || true
    
    # Build and start new containers
    print_status "Building new containers..."
    docker-compose build --no-cache
    
    print_status "Starting containers..."
    docker-compose up -d
    
    # Wait for containers to be healthy
    print_status "Waiting for containers to start..."
    sleep 30
    
    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Containers are running successfully"
    else
        print_error "Some containers failed to start"
        docker-compose logs
        exit 1
    fi
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    # Run migrations inside the container
    docker-compose exec -T web flask db upgrade 2>/dev/null || {
        print_warning "Migration failed, initializing database..."
        docker-compose exec -T web python -c "
from omcrm import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created')
" || print_warning "Database initialization failed - this might be normal for first run"
    }
}

# Health check
health_check() {
    print_status "Performing health check..."
    
    # Check if the application is responding
    max_attempts=10
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:80 >/dev/null 2>&1; then
            print_success "Application is responding on port 80"
            break
        else
            print_status "Attempt $attempt/$max_attempts - waiting for application..."
            sleep 5
            ((attempt++))
        fi
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_error "Application health check failed"
        print_status "Container logs:"
        docker-compose logs --tail=50
        exit 1
    fi
}

# Display final information
show_final_info() {
    echo ""
    echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY! 🎉"
    echo "========================================"
    echo ""
    print_success "Your OMCRM Trading Platform is now live!"
    echo ""
    echo "📱 Access your platform:"
    echo "   🌐 Main Site: http://localhost (or your domain)"
    echo "   🔧 Admin Panel: http://localhost/users/login"
    echo ""
    echo "🔧 Next Steps:"
    echo "   1. Update .env file with your domain and settings"
    echo "   2. Set up SSL certificates for HTTPS"
    echo "   3. Configure your domain DNS to point to this server"
    echo "   4. Update nginx/app.conf with your domain name"
    echo "   5. Create admin user: docker-compose exec web python manage.py create-admin"
    echo ""
    echo "📊 Monitor your deployment:"
    echo "   📋 View logs: docker-compose logs -f"
    echo "   🔄 Restart: docker-compose restart"
    echo "   ⬇️ Stop: docker-compose down"
    echo ""
    echo "💰 Start making money with your trading platform!"
}

# Main deployment process
main() {
    print_status "OMCRM Trading Platform Deployment Script"
    echo ""
    
    # Run deployment steps
    check_docker
    create_directories
    setup_environment
    init_database
    deploy_containers
    run_migrations
    health_check
    show_final_info
}

# Handle script interruption
trap 'print_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@" 