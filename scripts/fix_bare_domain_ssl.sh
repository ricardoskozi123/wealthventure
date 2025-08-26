#!/bin/bash

# Fix Bare Domain SSL Certificate for Stanford Capital
# This script will get an SSL certificate that covers both stanford-capital.com and www.stanford-capital.com

echo "🔧 Fixing bare domain SSL certificate for Stanford Capital..."

# Stop containers to free up port 80
echo "📦 Stopping containers..."
cd /var/www/omcrm
docker-compose down

# Get SSL certificate for both domains
echo "🔐 Obtaining SSL certificate for both domains..."
sudo certbot certonly \
  --standalone \
  --non-interactive \
  --agree-tos \
  --email admin@stanford-capital.com \
  -d stanford-capital.com \
  -d www.stanford-capital.com \
  --force-renewal

if [ $? -eq 0 ]; then
    echo "✅ SSL certificate obtained successfully!"
    
    # Update certificate paths in nginx config if needed
    echo "📝 Certificate will be available at:"
    echo "   /etc/letsencrypt/live/stanford-capital.com/fullchain.pem"
    echo "   /etc/letsencrypt/live/stanford-capital.com/privkey.pem"
    
    # Start containers
    echo "🚀 Starting containers..."
    docker-compose up -d
    
    # Test the configuration
    echo "🧪 Testing Nginx configuration..."
    docker exec omcrm_nginx nginx -t
    
    if [ $? -eq 0 ]; then
        echo "✅ Nginx configuration is valid!"
        
        # Reload Nginx
        echo "🔄 Reloading Nginx..."
        docker exec omcrm_nginx nginx -s reload
        
        echo ""
        echo "🎉 SSL certificate fix completed!"
        echo ""
        echo "📋 Test Results:"
        echo "1. https://stanford-capital.com → should redirect to https://www.stanford-capital.com"
        echo "2. https://www.stanford-capital.com → should load normally"
        echo "3. https://crm.stanford-capital.com → should load CRM"
        echo ""
        echo "🔍 You can test with:"
        echo "   curl -I https://stanford-capital.com"
        echo "   (should show 301 redirect to www)"
        
    else
        echo "❌ Nginx configuration test failed!"
        echo "Please check the configuration manually."
    fi
    
else
    echo "❌ Failed to obtain SSL certificate!"
    echo "Please check:"
    echo "1. DNS records point to this server"
    echo "2. Port 80 is not blocked by firewall"
    echo "3. Domain is properly configured"
    
    # Start containers anyway
    echo "🚀 Starting containers..."
    docker-compose up -d
fi

echo ""
echo "📊 Current certificate status:"
sudo certbot certificates
