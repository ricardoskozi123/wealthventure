#!/bin/bash

# Deploy Simple Redirect Configuration
# This avoids SSL certificate issues by handling redirects properly

echo "🚀 Deploying simple redirect configuration..."

# Navigate to project directory
cd /var/www/omcrm

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin stanford

# Stop containers
echo "🛑 Stopping containers..."
docker-compose down

# Start containers with new configuration
echo "🚀 Starting containers with simple redirect config..."
docker-compose up -d

# Wait for containers to start
echo "⏳ Waiting for containers to start..."
sleep 15

# Test nginx configuration
echo "🧪 Testing Nginx configuration..."
docker exec omcrm_nginx nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid!"
else
    echo "❌ Nginx configuration test failed!"
    echo "📋 Container logs:"
    docker logs omcrm_nginx --tail 20
    exit 1
fi

echo ""
echo "🎉 Simple redirect configuration deployed!"
echo ""
echo "📋 Expected behavior:"
echo "✅ http://stanford-capital.com → https://www.stanford-capital.com"
echo "✅ https://www.stanford-capital.com → loads normally"
echo "✅ https://crm.stanford-capital.com → CRM access"
echo ""
echo "🔍 Test with:"
echo "   curl -I http://stanford-capital.com"
echo "   curl -I https://www.stanford-capital.com"

echo ""
echo "🌐 Testing redirects..."
echo "HTTP test:"
curl -I http://stanford-capital.com 2>/dev/null | head -3

echo ""
echo "HTTPS www test:"
curl -I https://www.stanford-capital.com 2>/dev/null | head -3
