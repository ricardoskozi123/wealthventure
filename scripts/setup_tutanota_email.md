# Tutanota Email Setup for Stanford Capital Backups

## 🆓 Free Tutanota Account Setup

### Step 1: Create Tutanota Account
1. Go to https://tutanota.com/
2. Click "Sign up for free"
3. Choose a username like `stanfordcapital` or `backup`
4. Create account: `backup@tutanota.com` (or your preferred username)
5. Verify email address

### Step 2: Enable SMTP/IMAP (Premium Feature)
**Note**: Tutanota's free tier doesn't include SMTP/IMAP access. 
**Alternative FREE options:**

#### Option A: Gmail with App Password (FREE)
1. Create Gmail account: `stanfordcapitalbackup@gmail.com`
2. Enable 2-factor authentication
3. Generate App Password for "Mail"
4. Use these settings:
   ```json
   {
     "smtp_server": "smtp.gmail.com",
     "smtp_port": 587,
     "username": "stanfordcapitalbackup@gmail.com",
     "password": "your-16-digit-app-password"
   }
   ```

#### Option B: Outlook/Hotmail (FREE)
1. Create Outlook account: `stanfordcapitalbackup@outlook.com`
2. Use these settings:
   ```json
   {
     "smtp_server": "smtp-mail.outlook.com",
     "smtp_port": 587,
     "username": "stanfordcapitalbackup@outlook.com",
     "password": "your-password"
   }
   ```

#### Option C: Proton Mail Bridge (FREE with limitations)
1. Create ProtonMail account
2. Download Proton Mail Bridge (free tier available)
3. Use local SMTP settings

## 🔧 Configuration

### Update backup_config.json
```bash
cd /var/www/omcrm/scripts
nano backup_config.json
```

Update the email section:
```json
{
  "notifications": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "stanfordcapitalbackup@gmail.com",
      "password": "your-app-password-here",
      "to_addresses": ["your-main-email@domain.com"]
    }
  }
}
```

## 🧪 Test Email Notifications

```bash
cd /var/www/omcrm
python3 scripts/test_backup.py
```

## 📧 What You'll Receive

### Success Email:
```
Subject: Stanford Capital Backup Successful
Body:
Backup completed successfully!

Backup file: omcrm_backup_20240826_143022.sql.gz
Time: 2024-08-26 14:30:22
Size: 15.42 MB
```

### Failure Email:
```
Subject: Stanford Capital Backup Failed
Body:
Backup failed!

Error: Database connection timeout
Time: 2024-08-26 14:30:22
```

## 🔐 Security Best Practices

1. **Use App Passwords**: Never use main account passwords
2. **Separate Email**: Use dedicated backup email account
3. **Monitor Regularly**: Check backup emails daily
4. **Test Monthly**: Run test backups monthly
5. **Multiple Recipients**: Add multiple email addresses for redundancy

## 📅 Backup Schedule

The backup runs daily at 2 AM UTC via Docker Compose:
```yaml
backup:
  build: .
  container_name: omcrm_backup_service
  restart: always
  entrypoint: ["sh", "-c", "while true; do sleep 86400; python3 scripts/backup_system.py; done"]
```

## 🚨 Monitoring

Set up email rules to:
1. Move backup success emails to "Backups" folder
2. Forward backup failure emails to your phone
3. Create calendar reminders to check backup status weekly

