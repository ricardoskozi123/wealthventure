#!/bin/bash

# Setup Backup System for Stanford Capital
# Installs dependencies and configures backup system

echo "🔧 Setting up Stanford Capital Backup System..."

# Create backup directory
echo "📁 Creating backup directory..."
mkdir -p /app/backup
mkdir -p /app/logs
chmod 755 /app/backup
chmod 755 /app/logs

# Install PostgreSQL client if not present
echo "📦 Checking PostgreSQL client..."
if ! command -v pg_dump &> /dev/null; then
    echo "Installing postgresql-client..."
    apt-get update
    apt-get install -y postgresql-client
    echo "✅ PostgreSQL client installed"
else
    echo "✅ PostgreSQL client already installed"
fi

# Install Python dependencies for backup system
echo "🐍 Installing Python dependencies..."
pip install --no-cache-dir boto3 google-cloud-storage azure-storage-blob

# Copy configuration file if it doesn't exist
echo "⚙️  Setting up configuration..."
if [ ! -f "/app/scripts/backup_config.json" ]; then
    cp /app/scripts/backup_config.json.example /app/scripts/backup_config.json
    echo "📝 Created backup configuration file"
    echo "⚠️  Please edit /app/scripts/backup_config.json with your email settings"
else
    echo "✅ Configuration file already exists"
fi

# Test backup system
echo "🧪 Testing backup system..."
cd /app
python3 scripts/test_backup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Backup system setup completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Edit /app/scripts/backup_config.json with your email settings"
    echo "2. Test email notifications: python3 scripts/test_backup.py"
    echo "3. Backups will run daily at 2 AM UTC automatically"
    echo ""
    echo "📧 Email Setup Guide: /app/scripts/setup_tutanota_email.md"
else
    echo ""
    echo "⚠️  Backup system setup completed with warnings"
    echo "Please check the configuration and try again"
fi

