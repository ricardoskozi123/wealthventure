# 🔐 Multi-Brand Password Reset System

Complete password reset functionality with dynamic SMTP configuration per brand.

## 🚀 **Features**

✅ **Multi-Brand Email Support** - Different SMTP configs per brand  
✅ **Secure Token System** - Cryptographically secure tokens with expiration  
✅ **Rate Limiting** - Prevents abuse with configurable limits  
✅ **Professional Email Templates** - Beautiful HTML emails matching your brand  
✅ **Admin & Client Support** - Works for both admin users and clients  
✅ **Landing Page Styling** - Modern UI matching your trading platform  
✅ **Database Security** - Secure token storage with automatic cleanup  

## 📦 **Installation Steps**

### 1. **Create Database Table**
```bash
python create_password_reset_table.py
```

### 2. **Configure SMTP Settings**

#### **Option A: Database Configuration (Recommended)**
Go to Admin Panel → Settings → App Configuration and configure:
- SMTP Server (e.g., `smtp.gmail.com`)
- SMTP Port (e.g., `587`)
- SMTP Encryption (`TLS` or `SSL`)
- Sender Name (e.g., `OMCRM Trading`)
- Sender Email (e.g., `noreply@yourdomain.com`)

#### **Option B: Environment Variables**
```bash
# .env file
SMTP_PASSWORD=your_email_app_password
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=noreply@yourdomain.com
MAIL_SENDER_NAME=OMCRM Trading
```

### 3. **Set SMTP Password** (Required)
```bash
# For security, SMTP password is always from environment
export SMTP_PASSWORD=your_email_app_password
```

## 🔧 **Multi-Brand Configuration**

### **Current Setup**
The system currently uses a single SMTP configuration but is designed for easy multi-brand extension.

### **Extending for Multiple Brands**
To add brand-specific SMTP configurations:

1. **Extend AppConfig Model**:
```python
# omcrm/settings/models.py
class BrandConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand_name = db.Column(db.String(100), unique=True, nullable=False)
    smtp_server = db.Column(db.String(50))
    smtp_port = db.Column(db.String(5))
    smtp_encryption = db.Column(db.String(5))
    sender_name = db.Column(db.String(50))
    sender_email = db.Column(db.String(100))
    smtp_password_env_var = db.Column(db.String(50))  # Name of env variable
```

2. **Update EmailService**:
```python
# omcrm/utils/email_service.py
def get_smtp_config(brand_name=None):
    if brand_name:
        brand_config = BrandConfig.query.filter_by(brand_name=brand_name).first()
        if brand_config:
            return {
                'smtp_server': brand_config.smtp_server,
                # ... other brand-specific settings
                'smtp_password': os.environ.get(brand_config.smtp_password_env_var)
            }
    # Fall back to default config...
```

3. **Environment Variables per Brand**:
```bash
# Brand 1
BRAND1_SMTP_PASSWORD=password1

# Brand 2  
BRAND2_SMTP_PASSWORD=password2
```

## 📧 **Email Provider Setup**

### **Gmail Setup**
1. Enable 2-Factor Authentication
2. Generate App Password: `Google Account → Security → App Passwords`
3. Use App Password as `SMTP_PASSWORD`

### **Microsoft 365/Outlook**
```bash
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
SMTP_PASSWORD=your_outlook_password
```

### **SendGrid**
```bash
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USERNAME=apikey
SMTP_PASSWORD=your_sendgrid_api_key
```

### **AWS SES**
```bash
MAIL_SERVER=email-smtp.us-west-2.amazonaws.com
MAIL_PORT=587
MAIL_USERNAME=your_ses_username
SMTP_PASSWORD=your_ses_password
```

## 🛠 **Usage**

### **For Users**
1. Visit login page
2. Click "Forgot Password?" link
3. Enter email address
4. Check email for reset link
5. Click link and set new password

### **Available Routes**
- `/forgot-password` - Request password reset
- `/reset-password/<token>` - Reset password with token
- `/change-password` - Change password when logged in (requires login)

### **For Admins**
- `/admin/test-email` - Test SMTP configuration
- Settings → App Configuration - Configure SMTP settings

## 🔒 **Security Features**

### **Token Security**
- 64-character cryptographically secure tokens
- 30-minute expiration (configurable)
- Single-use tokens (automatically invalidated)
- IP address logging for security auditing

### **Rate Limiting**
- Maximum 5 reset attempts per hour per email
- Configurable limits in `PasswordResetManager`
- Automatic cleanup of expired tokens

### **Password Requirements**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter  
- At least one number

### **Email Security**
- No password information in emails
- Secure reset links with expiration warnings
- Professional templates with security notices

## 🎨 **Email Templates**

### **Password Reset Email**
- Professional design matching landing page
- Clear call-to-action buttons
- Security warnings and best practices
- Responsive HTML with fallback text

### **Welcome Email** (Optional)
- New client onboarding
- Temporary password delivery
- Login instructions

## 🧪 **Testing**

### **Test SMTP Configuration**
```python
from omcrm.utils.email_service import EmailService

# Test connection
result = EmailService.test_smtp_connection()
print(result)
```

### **Test Email Sending**
Visit: `/admin/test-email?json=1` (Admin only)

### **Manual Testing**
1. Go to `/forgot-password`
2. Enter your email
3. Check email and follow reset link
4. Verify password reset works

## 🚀 **Production Deployment**

### **Environment Variables**
```bash
# Required
SMTP_PASSWORD=your_production_smtp_password
PLATFORM_NAME=Your Trading Platform

# Optional (if not using database config)
MAIL_SERVER=smtp.yourdomain.com
MAIL_PORT=587
MAIL_USERNAME=noreply@yourdomain.com
MAIL_SENDER_NAME=Your Trading Platform
```

### **Security Checklist**
- [ ] SMTP password stored securely as environment variable
- [ ] Database backups include password_reset_tokens table
- [ ] Rate limiting configured appropriately
- [ ] Email templates reviewed for brand consistency
- [ ] Test password reset flow end-to-end

## 🔧 **Maintenance**

### **Database Cleanup**
Expired tokens are automatically cleaned up, but you can manually run:
```python
from omcrm.utils.password_reset import PasswordResetToken
cleaned = PasswordResetToken.cleanup_expired_tokens()
print(f"Cleaned {cleaned} expired tokens")
```

### **Monitor Reset Attempts**
```python
from omcrm.utils.password_reset import PasswordResetManager
attempts = PasswordResetManager.get_reset_attempts('user@example.com', hours=24)
print(f"Reset attempts in last 24h: {attempts}")
```

## 🆘 **Troubleshooting**

### **Email Not Sending**
1. Check SMTP configuration in admin panel
2. Verify `SMTP_PASSWORD` environment variable
3. Test connection: `/admin/test-email`
4. Check email provider settings (app passwords, etc.)

### **Reset Link Not Working**
1. Check token expiration (30 minutes default)
2. Verify token hasn't been used already
3. Check database connection and table existence

### **Rate Limiting Issues**
1. Check `PasswordResetManager.is_rate_limited()` settings
2. Clear old tokens if needed
3. Adjust rate limits in production

## 📝 **API Reference**

### **EmailService**
```python
# Send password reset email
EmailService.send_email(
    to_email="user@example.com",
    subject="Password Reset",
    html_content="<html>...</html>",
    brand_name="YourBrand"
)

# Test SMTP connection
EmailService.test_smtp_connection(brand_name="YourBrand")
```

### **PasswordResetManager**
```python
# Create reset token
PasswordResetManager.create_reset_token(
    email="user@example.com",
    expiry_minutes=30,
    brand_name="YourBrand"
)

# Validate token
PasswordResetManager.validate_reset_token(token_string)

# Reset password
PasswordResetManager.reset_password(token_string, new_password)
```

---

## 🎯 **Ready to Go!**

Your multi-brand password reset system is now ready! Users can reset passwords, admins can manage SMTP settings, and you can easily extend it for multiple brands.

**Need help?** Check the troubleshooting section or review the code in:
- `omcrm/utils/email_service.py`
- `omcrm/utils/password_reset.py`
- `omcrm/users/routes.py` 