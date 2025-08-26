#!/bin/bash
# Stanford Capital SSL Setup Script
# Run this script on your VPS to set up SSL certificates

set -e

echo "🦁 Stanford Capital SSL Setup Starting..."
echo "============================================"

# Variables
DOMAIN="stanford-capital.com"
EMAIL="admin@stanford-capital.com"  # Change this to your actual email

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

echo "🔧 Step 1: Installing Certbot..."
# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    apt update
    apt install -y certbot python3-certbot-nginx
    echo "✅ Certbot installed successfully"
else
    echo "✅ Certbot already installed"
fi

echo "🌐 Step 2: Checking DNS propagation..."
# Check if domain resolves to this server
SERVER_IP=$(curl -s ifconfig.me)
DOMAIN_IP=$(dig +short $DOMAIN)

echo "Server IP: $SERVER_IP"
echo "Domain IP: $DOMAIN_IP"

if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
    echo "⚠️  WARNING: Domain does not resolve to this server yet"
    echo "   Make sure your DNS A record points $DOMAIN to $SERVER_IP"
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "🛑 Step 3: Stopping containers to free ports..."
cd /var/www/omcrm
docker-compose down

echo "🔐 Step 4: Obtaining SSL certificates..."
# Get SSL certificate
certbot certonly --standalone \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    --domains $DOMAIN,www.$DOMAIN

if [ $? -eq 0 ]; then
    echo "✅ SSL certificates obtained successfully"
else
    echo "❌ Failed to obtain SSL certificates"
    echo "   Common issues:"
    echo "   - Domain not pointing to this server"
    echo "   - Port 80/443 blocked by firewall"
    echo "   - Rate limit exceeded (5 attempts per week)"
    exit 1
fi

echo "🔧 Step 5: Setting up certificate permissions..."
chmod -R 755 /etc/letsencrypt/live/
chmod -R 755 /etc/letsencrypt/archive/

echo "🐳 Step 6: Starting containers with SSL..."
docker-compose up -d

echo "⏳ Waiting for containers to start..."
sleep 30

echo "🧪 Step 7: Testing SSL configuration..."
if curl -s https://$DOMAIN > /dev/null; then
    echo "✅ HTTPS is working!"
else
    echo "⚠️  HTTPS test failed, but certificates are installed"
    echo "   Check container logs: docker-compose logs nginx"
fi

echo "🔄 Step 8: Setting up auto-renewal..."
# Add cron job for auto-renewal
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'cd /var/www/omcrm && docker-compose restart nginx'") | crontab -

echo ""
echo "🎉 Stanford Capital SSL Setup Complete!"
echo "============================================"
echo "✅ Domain: https://$DOMAIN"
echo "✅ SSL certificates installed"
echo "✅ Auto-renewal configured"
echo ""
echo "🔗 Test your site:"
echo "   https://$DOMAIN"
echo "   https://www.$DOMAIN"
echo ""
echo "📋 Next steps:"
echo "   1. Test the website in your browser"
echo "   2. Check SSL rating: https://www.ssllabs.com/ssltest/"
echo "   3. Update any hardcoded HTTP links to HTTPS"
echo ""
