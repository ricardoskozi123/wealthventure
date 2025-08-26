# 🦁 Stanford Capital Domain & SSL Setup Guide

## 🌐 Prerequisites
- DNS records created and propagated
- VPS running at `84.32.185.133`
- Domain: `stanford-capital.com`

## 📋 DNS Records Required
Make sure these DNS records are set up:
```
A record: stanford-capital.com → 84.32.185.133
A record: www.stanford-capital.com → 84.32.185.133
A record: crm.stanford-capital.com → 84.32.185.133
```

## 🚀 Step-by-Step Setup

### 1. Connect to your Stanford VPS
```bash
ssh root@84.32.185.133
cd /var/www/omcrm
```

### 2. Pull the latest Stanford branch
```bash
git pull origin stanford
```

### 3. Make the SSL setup script executable
```bash
chmod +x scripts/setup_stanford_ssl.sh
```

### 4. Run the SSL setup script
```bash
sudo ./scripts/setup_stanford_ssl.sh
```

This script will:
- ✅ Install Certbot (if needed)
- ✅ Check DNS propagation
- ✅ Stop containers to free ports 80/443
- ✅ Obtain SSL certificates from Let's Encrypt
- ✅ Set proper permissions
- ✅ Start containers with SSL
- ✅ Test HTTPS connectivity
- ✅ Set up auto-renewal

### 5. Verify Everything Works
After the script completes, test these URLs:
- 🔗 https://stanford-capital.com (Client portal)
- 🔗 https://www.stanford-capital.com (Client portal)
- 🔗 https://crm.stanford-capital.com (Admin/CRM portal)
- 🔗 http://stanford-capital.com (should redirect to HTTPS)

## 🔧 Manual SSL Setup (Alternative)

If the automated script doesn't work, here's the manual process:

### Stop containers
```bash
cd /var/www/omcrm
docker-compose down
```

### Install Certbot
```bash
sudo apt update
sudo apt install -y certbot
```

### Get SSL certificates
```bash
sudo certbot certonly --standalone \
    --email admin@stanford-capital.com \
    --agree-tos \
    --domains stanford-capital.com,www.stanford-capital.com,crm.stanford-capital.com
```

### Start containers
```bash
docker-compose up -d
```

## 🔍 Troubleshooting

### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Test renewal
sudo certbot renew --dry-run

# Check certificate files
ls -la /etc/letsencrypt/live/stanford-capital.com/
```

### Container Issues
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs nginx
docker-compose logs web

# Restart specific service
docker-compose restart nginx
```

### Domain Not Resolving
```bash
# Check DNS propagation
dig stanford-capital.com
nslookup stanford-capital.com

# Check from external tool
# https://dnschecker.org/
```

## 🎯 Expected Results

After successful setup:
- ✅ https://stanford-capital.com loads with SSL
- ✅ HTTP redirects to HTTPS
- ✅ Stanford Capital branding and lion logo
- ✅ Professional SSL certificate (A+ rating)
- ✅ Auto-renewal configured

## 🔐 Security Features Enabled
- TLS 1.2 and 1.3 only
- Strong cipher suites
- HSTS headers
- Security headers (X-Frame-Options, etc.)
- Automatic HTTP to HTTPS redirect

## 📞 Support
If you encounter issues:
1. Check the logs: `docker-compose logs`
2. Verify DNS: `dig stanford-capital.com`
3. Test SSL: https://www.ssllabs.com/ssltest/
4. Check firewall: `ufw status`
