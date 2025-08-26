#!/bin/bash

# Switch to Proper SSL Configuration
# Use this after SSL certificate is successfully obtained

echo "🔄 Switching to proper SSL configuration..."

cd /var/www/omcrm

# Update docker-compose.yml to use proper SSL config
echo "📝 Updating docker-compose.yml..."
sed -i 's|stanford_simple.conf|stanford_proper_ssl.conf|g' docker-compose.yml

# Restart containers with new configuration
echo "🔄 Restarting containers with proper SSL config..."
docker-compose down
docker-compose up -d

# Wait for containers to start
sleep 15

# Test nginx configuration
echo "🧪 Testing Nginx configuration..."
docker exec omcrm_nginx nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid!"
    
    # Reload nginx
    echo "🔄 Reloading Nginx..."
    docker exec omcrm_nginx nginx -s reload
    
    echo ""
    echo "🎉 Switched to proper SSL configuration!"
    echo ""
    echo "🧪 Testing all redirects:"
    
    echo "1. HTTP bare domain:"
    curl -I http://stanford-capital.com 2>/dev/null | head -2
    
    echo ""
    echo "2. HTTPS bare domain:"
    curl -I https://stanford-capital.com 2>/dev/null | head -2
    
    echo ""
    echo "3. HTTPS www domain:"
    curl -I https://www.stanford-capital.com 2>/dev/null | head -2
    
    echo ""
    echo "✅ All redirects should now work without SSL warnings!"
    
else
    echo "❌ Nginx configuration test failed!"
    echo "🔄 Reverting to simple configuration..."
    
    # Revert to simple config
    sed -i 's|stanford_proper_ssl.conf|stanford_simple.conf|g' docker-compose.yml
    docker-compose down
    docker-compose up -d
    
    echo "⚠️  Reverted to simple configuration due to errors"
fi
