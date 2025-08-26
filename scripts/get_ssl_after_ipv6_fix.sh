#!/bin/bash

# Get SSL Certificate for Stanford Capital after IPv6 removal
# Now that IPv6 is removed, this should work properly

echo "🔐 Attempting SSL certificate generation after IPv6 removal..."

# Navigate to project directory
cd /var/www/omcrm

# Stop containers to free up port 80
echo "🛑 Stopping containers to free port 80..."
docker-compose down

# Wait a moment for ports to be freed
sleep 5

# Check if port 80 is free
echo "🔍 Checking port 80 availability..."
if netstat -tlnp | grep :80 > /dev/null; then
    echo "⚠️  Port 80 is still in use. Waiting..."
    sleep 10
fi

# Try to get SSL certificate for both domains
echo "📜 Attempting to get SSL certificate for both domains..."
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
    
    # Show certificate details
    echo "📋 Certificate details:"
    sudo certbot certificates | grep -A 10 stanford-capital.com
    
    # Update nginx configuration to use the new certificate
    echo "🔧 The certificate should be available at:"
    echo "   /etc/letsencrypt/live/stanford-capital.com/fullchain.pem"
    echo "   /etc/letsencrypt/live/stanford-capital.com/privkey.pem"
    
    # Start containers
    echo "🚀 Starting containers..."
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
        echo "🎉 SSL certificate setup completed!"
        echo ""
        echo "🧪 Testing redirects:"
        
        echo "HTTP test:"
        curl -I http://stanford-capital.com 2>/dev/null | head -2
        
        echo ""
        echo "HTTPS bare domain test:"
        curl -I https://stanford-capital.com 2>/dev/null | head -2
        
        echo ""
        echo "HTTPS www test:"
        curl -I https://www.stanford-capital.com 2>/dev/null | head -2
        
    else
        echo "❌ Nginx configuration test failed!"
        docker logs omcrm_nginx --tail 10
    fi
    
else
    echo "❌ Failed to obtain SSL certificate!"
    echo ""
    echo "🔍 Troubleshooting steps:"
    echo "1. Check if IPv6 record is completely removed from DNS"
    echo "2. Verify A record points to this server: $(curl -s ifconfig.me)"
    echo "3. Check firewall allows port 80"
    echo ""
    echo "📋 DNS check:"
    echo "Current server IP: $(curl -s ifconfig.me)"
    echo "stanford-capital.com resolves to:"
    dig +short stanford-capital.com
    echo "www.stanford-capital.com resolves to:"
    dig +short www.stanford-capital.com
    
    # Start containers anyway
    echo "🚀 Starting containers with current configuration..."
    docker-compose up -d
fi

echo ""
echo "📊 Current certificate status:"
sudo certbot certificates
