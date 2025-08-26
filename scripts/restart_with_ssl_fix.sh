#!/bin/bash

# Simple SSL fix using existing www certificate
# This avoids the IPv6 certificate generation issues

echo "🔧 Applying SSL fix using existing www certificate..."

# Navigate to project directory
cd /var/www/omcrm

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin stanford

# Test nginx configuration first
echo "🧪 Testing Nginx configuration..."
docker exec omcrm_nginx nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid!"
    
    # Reload nginx with new configuration
    echo "🔄 Reloading Nginx..."
    docker exec omcrm_nginx nginx -s reload
    
    echo ""
    echo "🎉 SSL fix applied successfully!"
    echo ""
    echo "📋 How it works:"
    echo "- stanford-capital.com uses www certificate (may show brief warning)"
    echo "- Immediately redirects to www.stanford-capital.com with proper SSL"
    echo "- End result: users get to secure www site"
    echo ""
    echo "🔍 Test with:"
    echo "   curl -I https://stanford-capital.com"
    echo "   (should show 301 redirect to www)"
    
else
    echo "❌ Nginx configuration test failed!"
    echo "Restarting containers to apply changes..."
    
    # Restart containers if config test fails
    docker-compose down
    docker-compose up -d
    
    # Wait a moment and test again
    sleep 10
    docker exec omcrm_nginx nginx -t
fi

echo ""
echo "📊 Current SSL certificates:"
sudo certbot certificates | grep -A 5 -B 2 stanford-capital

echo ""
echo "🌐 Domain status check:"
echo "Testing www.stanford-capital.com..."
curl -I https://www.stanford-capital.com 2>/dev/null | head -1

echo "Testing crm.stanford-capital.com..."
curl -I https://crm.stanford-capital.com 2>/dev/null | head -1
