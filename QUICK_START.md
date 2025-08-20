# 🚀 Quick Start: Multi-Domain Trading Platform

## 🎯 What We've Built

You now have a **bulletproof trading platform** with:

- **Client Domain**: `investmentprohub.com` → Trading platform for clients
- **Admin Domain**: `crm.investmentprohub.com` → CRM for admins/agents  
- **Daily Backups**: Automated with email notifications
- **10-Minute Recovery**: Complete disaster recovery system
- **SSL Security**: Automatic HTTPS with Let's Encrypt
- **Domain Flexibility**: Easy to change domains in future

---

## 🏃‍♂️ Super Quick Setup (5 Commands)

### On Your VPS (84.32.188.252):

```bash
# 1. Deploy the platform
cd /opt/omcrm
sudo ./deploy_with_domains.sh

# 2. Setup domains & SSL (after DNS is configured)
sudo ./scripts/setup_domains.sh

# 3. Test backup system
python3 scripts/backup_system.py

# Done! Your platform is live! 🎉
```

---

## 🌐 DNS Configuration

**Point these records to `84.32.188.252`:**

```
Type: A    Name: @              Value: 84.32.188.252
Type: A    Name: crm            Value: 84.32.188.252  
Type: A    Name: www            Value: 84.32.188.252
```

**Using Cloudflare?** 
- ✅ Set to "Proxied" for DDoS protection
- ✅ Enable "Always Use HTTPS"

---

## 🔑 Access Your Platform

After DNS + SSL setup:

| Service | URL | Users |
|---------|-----|-------|
| **Client Trading** | `https://investmentprohub.com/login` | Traders/Clients |
| **Admin CRM** | `https://crm.investmentprohub.com/login` | Admins/Agents |
| **WebTrader** | `https://investmentprohub.com/webtrader` | Active traders |

---

## 📧 Backup Configuration

### Email Notifications
Edit `scripts/backup_config.json`:
```json
{
  "notifications": {
    "email": {
      "enabled": true,
      "username": "your-gmail@gmail.com",
      "password": "your-app-password",
      "to_addresses": ["admin@investmentprohub.com"]
    }
  }
}
```

### Cloud Storage (Optional)
```json
{
  "digitalocean": {
    "enabled": true,
    "space": "omcrm-backups-unique",
    "access_key": "YOUR_KEY",
    "secret_key": "YOUR_SECRET"
  }
}
```

---

## 🆘 Disaster Recovery

### Preparation (Save these files now!)
```bash
# Download to your local computer
scp root@84.32.188.252:/opt/omcrm/scripts/disaster_recovery_config.json ./
scp root@84.32.188.252:/root/.ssh/id_rsa ./omcrm_ssh_key
```

### Emergency Deployment (10 minutes)
```bash
# Get new VPS, then run:
python3 scripts/disaster_recovery.py NEW_SERVER_IP ./omcrm_ssh_key

# Update DNS to new IP
# ✅ Back online in 10 minutes!
```

---

## 🔄 Changing Domains (Future)

Want to use different domains? Super easy:

```bash
# Update environment
nano .env
# Change CLIENT_DOMAIN and CRM_SUBDOMAIN

# Update nginx config  
nano nginx/multi_domain.conf
# Update server_name lines

# Get new SSL certificates
certbot certonly --standalone -d yournewdomain.com -d crm.yournewdomain.com

# Restart
docker-compose restart
```

---

## 📊 Daily Operations

### Health Checks
```bash
# Service status
docker-compose ps

# Backup logs
tail -50 /var/log/omcrm-backup.log

# SSL expiry
openssl x509 -in /opt/omcrm/ssl/investmentprohub.com/cert.pem -text -noout | grep "Not After"
```

### Manual Backup
```bash
cd /opt/omcrm
python3 scripts/backup_system.py
```

---

## 🛠️ Troubleshooting

### Domain Not Working?
```bash
# Check DNS propagation
nslookup investmentprohub.com

# Check services
docker-compose logs web
docker-compose logs nginx
```

### SSL Issues?
```bash
# Check certificate
openssl s_client -connect investmentprohub.com:443

# Renew manually
certbot renew --force-renewal
```

### Reset Everything
```bash
cd /opt/omcrm
docker-compose down
docker system prune -f
docker-compose up -d --build
```

---

## 🎯 Success Checklist

- ✅ DNS points to your VPS
- ✅ SSL certificates working  
- ✅ Client login: `https://investmentprohub.com/login`
- ✅ Admin login: `https://crm.investmentprohub.com/login`
- ✅ Backup emails working
- ✅ Disaster recovery tested
- ✅ Team trained on access URLs

---

## 🚨 Important Notes

### Security
- **Change default passwords** in production
- **Enable 2FA** for admin accounts
- **Regular backups** are automated (2 AM daily)
- **SSL auto-renewal** every Sunday 3 AM

### Monitoring
- Check logs weekly: `/var/log/omcrm-backup.log`
- Monitor disk space: `df -h`
- Test disaster recovery monthly

### Support
- Platform logs: `docker-compose logs`
- Backup issues: Check `scripts/backup_config.json`
- SSL problems: Run `scripts/setup_domains.sh` again

---

## 🎉 You're All Set!

Your trading platform is now:
- **Live** on your professional domain
- **Secure** with SSL certificates  
- **Backed up** daily automatically
- **Disaster-proof** with 10-minute recovery
- **Scalable** for future domain changes

**Welcome to your bulletproof trading empire! 🚀**

---

*Need help? Check the detailed guides:*
- 📖 [DOMAIN_SETUP_GUIDE.md](DOMAIN_SETUP_GUIDE.md) - Complete setup instructions
- 🔧 [docker-compose.yml](docker-compose.yml) - Service configuration  
- 🛡️ [scripts/](scripts/) - Backup & recovery tools 