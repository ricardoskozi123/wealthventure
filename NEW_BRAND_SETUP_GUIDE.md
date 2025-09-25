# 🏢 New Brand Setup Guide

## Overview
This guide will help you create a new brand using your existing OMCRM system as a foundation.

## 🚀 Quick Start Options

### Option 1: Separate Repository (Recommended)
**Best for:** Complete brand separation, independent development

1. **Create New GitHub Repository**
   ```bash
   # Create new repo on GitHub: your-new-brand-crm
   git clone https://github.com/yourusername/your-new-brand-crm.git
   cd your-new-brand-crm
   ```

2. **Copy Current Codebase**
   ```bash
   # Copy all files from current project
   cp -r /path/to/current/omcrm/* .
   cp -r /path/to/current/scripts .
   cp -r /path/to/current/nginx .
   cp docker-compose.yml Dockerfile requirements.txt .
   ```

3. **Update Brand Configuration**
   - Update `docker-compose.yml` environment variables
   - Modify `nginx/` configurations for new domain
   - Update `scripts/backup_config.json` with new email
   - Customize branding in templates

### Option 2: Multi-Brand Monorepo
**Best for:** Shared core functionality, easier maintenance

1. **Add Brand Configuration System**
   ```python
   # omcrm/config.py
   import os
   
   BRAND_CONFIG = {
       'stanford': {
           'name': 'Stanford Capital',
           'domain': 'stanford-capital.com',
           'email': 'admin@stanford-capital.com'
       },
       'newbrand': {
           'name': 'Your New Brand',
           'domain': 'yournewbrand.com',
           'email': 'admin@yournewbrand.com'
       }
   }
   
   CURRENT_BRAND = os.getenv('BRAND_NAME', 'stanford')
   ```

2. **Environment-Based Switching**
   ```bash
   # In docker-compose.yml
   environment:
     - BRAND_NAME=newbrand
     - CLIENT_DOMAIN=yournewbrand.com
   ```

## 📧 Email Backup Setup

### Gmail Setup (FREE - Recommended)
1. **Create Gmail Account**
   - Go to [gmail.com](https://gmail.com)
   - Create: `yourbrandbackup@gmail.com`

2. **Enable 2FA & Generate App Password**
   - Go to [myaccount.google.com](https://myaccount.google.com)
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"

3. **Update Configuration**
   ```json
   {
     "notifications": {
       "email": {
         "enabled": true,
         "smtp_server": "smtp.gmail.com",
         "smtp_port": 587,
         "username": "yourbrandbackup@gmail.com",
         "password": "your-16-digit-app-password",
         "to_addresses": ["admin@yournewbrand.com"]
       }
     }
   }
   ```

### Alternative: Outlook (FREE)
```json
{
  "smtp_server": "smtp-mail.outlook.com",
  "smtp_port": 587,
  "username": "yourbrandbackup@outlook.com",
  "password": "your-password"
}
```

## 🔧 Brand Customization Checklist

### 1. Domain & SSL Setup
- [ ] Register new domain
- [ ] Update DNS records
- [ ] Configure SSL certificates
- [ ] Update nginx configurations

### 2. Database Configuration
- [ ] Create new database
- [ ] Update connection strings
- [ ] Run migrations
- [ ] Set up backup system

### 3. Branding Updates
- [ ] Update company name in templates
- [ ] Change logos and colors
- [ ] Update email templates
- [ ] Modify footer/header content

### 4. Environment Variables
```bash
# New brand environment
CLIENT_DOMAIN=yournewbrand.com
CRM_SUBDOMAIN=crm.yournewbrand.com
BRAND_NAME=yournewbrand
EMAIL_FROM=noreply@yournewbrand.com
```

### 5. Docker Configuration
```yaml
# docker-compose.yml for new brand
services:
  web:
    environment:
      - CLIENT_DOMAIN=yournewbrand.com
      - CRM_SUBDOMAIN=crm.yournewbrand.com
      - BRAND_NAME=yournewbrand
```

## 🧪 Testing Your Setup

### 1. Test Backup System
```bash
# Run backup test
python3 scripts/test_backup.py
```

### 2. Test Email Notifications
```bash
# Test email configuration
python3 -c "
import smtplib
from email.mime.text import MimeText

msg = MimeText('Test backup notification')
msg['Subject'] = 'Test Backup'
msg['From'] = 'yourbrandbackup@gmail.com'
msg['To'] = 'admin@yournewbrand.com'

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('yourbrandbackup@gmail.com', 'your-app-password')
server.send_message(msg)
server.quit()
print('Email test successful!')
"
```

### 3. Test Application
```bash
# Start containers
docker-compose up -d

# Check logs
docker-compose logs web
docker-compose logs backup
```

## 📊 Backup Monitoring

### Daily Backup Schedule
Your backup runs automatically at 2 AM UTC via Docker:
```yaml
backup:
  entrypoint: ["sh", "-c", "while true; do sleep 86400; python3 scripts/backup_system.py; done"]
```

### Email Notifications
You'll receive:
- ✅ **Success emails** with backup details
- ❌ **Failure emails** with error information
- 📊 **Size and timestamp** information

### Backup Storage Options
1. **Local Storage** (default): `/app/backup`
2. **Cloud Storage**: AWS S3, Google Cloud, Azure, DigitalOcean
3. **Email Attachments**: Small backups via email
4. **FTP Server**: Remote backup storage

## 🔐 Security Best Practices

1. **Use App Passwords**: Never use main account passwords
2. **Separate Email Accounts**: Dedicated backup email
3. **Monitor Regularly**: Check backup emails daily
4. **Test Monthly**: Run test backups monthly
5. **Multiple Recipients**: Add backup email addresses

## 🚨 Troubleshooting

### Common Issues
1. **Email Authentication Failed**
   - Check App Password (not main password)
   - Verify 2FA is enabled
   - Test SMTP settings

2. **Database Connection Failed**
   - Check Docker containers are running
   - Verify database credentials
   - Check network connectivity

3. **Backup File Not Created**
   - Check disk space
   - Verify write permissions
   - Check pg_dump installation

### Debug Commands
```bash
# Check container status
docker-compose ps

# View backup logs
docker-compose logs backup

# Test database connection
docker-compose exec db pg_isready -U omcrm_user -d omcrm_trading

# Manual backup test
docker-compose exec backup python3 scripts/test_backup.py
```

## 📈 Next Steps

1. **Deploy to Production**
   - Set up VPS/server
   - Configure domain and SSL
   - Deploy with Docker

2. **Monitor and Maintain**
   - Set up monitoring alerts
   - Regular backup testing
   - Performance optimization

3. **Scale as Needed**
   - Add more storage backends
   - Implement disaster recovery
   - Add monitoring dashboards

## 💡 Pro Tips

- **Start with Gmail**: Easiest free email setup
- **Test Everything**: Always test before production
- **Document Changes**: Keep track of customizations
- **Backup Your Configs**: Version control your configurations
- **Monitor Costs**: Track cloud storage usage

---

**Need Help?** Check the logs, test configurations, and don't hesitate to ask for assistance!

