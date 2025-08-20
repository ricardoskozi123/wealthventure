# 🌐 Domain Setup & Disaster Recovery Guide

## Overview

This guide will help you:
1. **Setup multi-domain architecture** (investmentprohub.com + crm.investmentprohub.com)
2. **Connect your VPS to your domain**
3. **Setup automated daily backups**
4. **Prepare for 10-minute disaster recovery**

## 🏗️ Architecture

```
investmentprohub.com          → Client Trading Platform
crm.investmentprohub.com      → Admin/Agent CRM Interface
```

- **Clients** access trading platform at `investmentprohub.com/login`
- **Admins/Agents** access CRM at `crm.investmentprohub.com/login`
- **Automatic redirects** prevent wrong access

---

## 📋 Prerequisites

### 1. Domain Requirements
- ✅ Domain: `investmentprohub.com` (purchased and owned)
- ✅ Access to DNS management (Cloudflare, Namecheap, etc.)
- ✅ VPS with public IP (your current: `84.32.188.252`)

### 2. VPS Requirements
- ✅ Ubuntu 20.04+ or similar
- ✅ Docker & Docker Compose installed
- ✅ Root access
- ✅ Ports 80, 443 open

---

## 🚀 Quick Setup (10 Minutes)

### Step 1: Connect Domain to VPS

#### Option A: Using Cloudflare (Recommended)
1. **Login to Cloudflare** → Add Site → `investmentprohub.com`
2. **Add DNS Records:**
   ```
   Type: A    Name: @              Content: 84.32.188.252
   Type: A    Name: crm            Content: 84.32.188.252
   Type: A    Name: www            Content: 84.32.188.252
   ```
3. **Set Proxy Status:** ⚡ (Proxied) for DDoS protection
4. **Update nameservers** at your domain registrar

#### Option B: Direct DNS (Simple)
At your domain provider (Namecheap, GoDaddy, etc.):
```
Type: A    Host: @              Value: 84.32.188.252
Type: A    Host: crm            Value: 84.32.188.252
Type: A    Host: www            Value: 84.32.188.252
```

### Step 2: Run Automated Setup

```bash
# On your VPS, run the automated setup
cd /opt/omcrm
chmod +x scripts/setup_domains.sh
./scripts/setup_domains.sh
```

**That's it!** The script will:
- ✅ Install SSL certificates (Let's Encrypt)
- ✅ Configure nginx for both domains
- ✅ Setup automatic backups (daily at 2 AM)
- ✅ Setup SSL auto-renewal
- ✅ Verify everything works

### Step 3: Update Environment Variables

```bash
# Add domain configuration
echo "CLIENT_DOMAIN=investmentprohub.com" >> .env
echo "CRM_SUBDOMAIN=crm.investmentprohub.com" >> .env

# Restart services
docker-compose restart
```

---

## 📧 Backup Configuration

### Step 1: Configure Email Notifications

Edit `scripts/backup_config.json`:
```json
{
  "notifications": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "your-email@gmail.com",
      "password": "your-app-password",
      "to_addresses": ["admin@investmentprohub.com"]
    }
  }
}
```

### Step 2: Setup Cloud Storage (Optional but Recommended)

#### DigitalOcean Spaces
```json
{
  "digitalocean": {
    "enabled": true,
    "space": "omcrm-backups-your-unique-name",
    "region": "nyc3",
    "access_key": "YOUR_DO_SPACES_KEY",
    "secret_key": "YOUR_DO_SPACES_SECRET"
  }
}
```

#### AWS S3
```json
{
  "aws_s3": {
    "enabled": true,
    "bucket": "omcrm-backups-your-unique-name",
    "region": "us-east-1",
    "access_key": "YOUR_AWS_ACCESS_KEY",
    "secret_key": "YOUR_AWS_SECRET_KEY"
  }
}
```

### Step 3: Test Backup System

```bash
# Test backup manually
cd /opt/omcrm
python3 scripts/backup_system.py
```

---

## 🚨 Disaster Recovery (10-Minute Deployment)

### Preparation (Do This Now!)

1. **Save these files securely:**
   ```bash
   # Download critical files to your computer
   scp -r root@84.32.188.252:/opt/omcrm/scripts/disaster_recovery_config.json ./
   scp -r root@84.32.188.252:/opt/omcrm/scripts/backup_config.json ./
   scp -r root@84.32.188.252:/root/.ssh/id_rsa ./omcrm_ssh_key
   ```

2. **Configure disaster recovery:**
   Edit `scripts/disaster_recovery_config.json`:
   ```json
   {
     "backup_sources": {
       "digitalocean": {
         "enabled": true,
         "space": "omcrm-backups",
         "access_key": "YOUR_KEY",
         "secret_key": "YOUR_SECRET"
       }
     }
   }
   ```

### Emergency Deployment (When Disaster Strikes)

1. **Get a new VPS** (DigitalOcean, AWS, etc.)
2. **Run disaster recovery:**
   ```bash
   # Replace NEW_SERVER_IP with your new server's IP
   python3 scripts/disaster_recovery.py NEW_SERVER_IP ./omcrm_ssh_key
   ```
3. **Update DNS** to point to new IP
4. **Verify** everything works

**Total time: ~10 minutes!** ⚡

---

## 🔧 Manual Configuration

### Custom Domain Changes

If you want to change domains later, update these files:

1. **Environment variables** (`.env`):
   ```bash
   CLIENT_DOMAIN=yournewdomain.com
   CRM_SUBDOMAIN=crm.yournewdomain.com
   ```

2. **Nginx configuration** (`nginx/multi_domain.conf`):
   ```nginx
   server_name yournewdomain.com www.yournewdomain.com;
   server_name crm.yournewdomain.com;
   ```

3. **Restart services:**
   ```bash
   docker-compose restart
   ```

### SSL Certificate Management

```bash
# Get new certificates
certbot certonly --standalone -d yournewdomain.com -d crm.yournewdomain.com

# Copy certificates
cp /etc/letsencrypt/live/yournewdomain.com/fullchain.pem /opt/omcrm/ssl/investmentprohub.com/cert.pem
cp /etc/letsencrypt/live/yournewdomain.com/privkey.pem /opt/omcrm/ssl/investmentprohub.com/key.pem

# Restart nginx
docker-compose restart nginx
```

---

## 🔍 Verification & Testing

### Domain Testing

```bash
# Test redirects
curl -I http://investmentprohub.com          # Should redirect to HTTPS
curl -I https://investmentprohub.com         # Should return 200
curl -I https://crm.investmentprohub.com     # Should return 200

# Test admin redirect
curl -I https://investmentprohub.com/login   # Should redirect to CRM

# Test client redirect  
curl -I https://crm.investmentprohub.com/client/  # Should redirect to main
```

### Application Testing

1. **Client Login:** https://investmentprohub.com/login
2. **Admin Login:** https://crm.investmentprohub.com/login
3. **WebTrader:** https://investmentprohub.com/webtrader
4. **Admin Dashboard:** https://crm.investmentprohub.com/

### Backup Testing

```bash
# Test backup
python3 scripts/backup_system.py

# Check backup logs
tail -f /app/logs/backup.log

# List backups
ls -la /app/backup/
```

---

## 📊 Monitoring & Maintenance

### Daily Checks

```bash
# Check service status
docker-compose ps

# Check backup logs
tail -50 /var/log/omcrm-backup.log

# Check SSL expiry
openssl x509 -in /opt/omcrm/ssl/investmentprohub.com/cert.pem -text -noout | grep "Not After"

# Check disk space
df -h
```

### Monthly Tasks

1. **Test disaster recovery** (on staging server)
2. **Review backup retention** settings
3. **Update SSL certificates** (automatic but verify)
4. **Security updates** for VPS

---

## 🆘 Troubleshooting

### Common Issues

#### Domain Not Resolving
```bash
# Check DNS propagation
nslookup investmentprohub.com
dig @8.8.8.8 investmentprohub.com

# Wait up to 24 hours for full propagation
```

#### SSL Certificate Issues
```bash
# Check certificate validity
openssl s_client -connect investmentprohub.com:443 -servername investmentprohub.com

# Renew certificates manually
certbot renew --force-renewal
```

#### Backup Failures
```bash
# Check backup logs
tail -100 /app/logs/backup.log

# Test database connection
docker-compose exec db psql -U omcrm_user -d omcrm_trading -c "SELECT 1;"

# Check storage credentials
python3 -c "import boto3; print('AWS credentials OK')"
```

#### Services Not Starting
```bash
# Check logs
docker-compose logs web
docker-compose logs nginx
docker-compose logs db

# Restart services
docker-compose down && docker-compose up -d
```

---

## 📞 Support

### Getting Help

1. **Check logs first:**
   ```bash
   docker-compose logs --tail=100
   tail -100 /var/log/omcrm-backup.log
   ```

2. **Common commands:**
   ```bash
   # Reset everything
   docker-compose down && docker-compose up -d --build

   # Clean restart
   docker system prune -f && docker-compose up -d --build
   ```

3. **Emergency contacts:**
   - Email: admin@investmentprohub.com
   - Backup email from disaster recovery notifications

---

## 🎯 Success Checklist

- ✅ Domain points to VPS
- ✅ SSL certificates working
- ✅ Client login at investmentprohub.com/login
- ✅ Admin login at crm.investmentprohub.com/login
- ✅ Daily backups configured
- ✅ Email notifications working
- ✅ Disaster recovery tested
- ✅ Auto-renewal setup
- ✅ Monitoring in place

**Congratulations! Your multi-domain trading platform is now bulletproof! 🎉** 