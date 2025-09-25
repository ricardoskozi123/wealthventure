#!/usr/bin/env python3
"""
Test Email Configuration (No Phone Required)
Test your backup email setup with Mail.com or other services
"""

import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

def test_mail_com():
    """Test Mail.com SMTP connection"""
    print("📧 Testing Mail.com SMTP...")
    
    try:
        # Test connection
        server = smtplib.SMTP('smtp.mail.com', 587)
        server.starttls()
        print("✅ SMTP connection successful")
        
        # You'll need to add your credentials here
        # server.login('yourbrandbackup@mail.com', 'your-password')
        
        server.quit()
        return True
        
    except Exception as e:
        print(f"❌ SMTP test failed: {e}")
        return False

def test_gmx():
    """Test GMX SMTP connection"""
    print("📧 Testing GMX SMTP...")
    
    try:
        server = smtplib.SMTP('mail.gmx.com', 587)
        server.starttls()
        print("✅ GMX SMTP connection successful")
        server.quit()
        return True
        
    except Exception as e:
        print(f"❌ GMX test failed: {e}")
        return False

def send_test_email(smtp_server, port, username, password, to_email):
    """Send a test backup notification email"""
    print(f"📤 Sending test email via {smtp_server}...")
    
    try:
        msg = MimeMultipart()
        msg['From'] = username
        msg['To'] = to_email
        msg['Subject'] = "Test Backup Notification"
        
        body = """
        This is a test backup notification email.
        
        If you receive this, your backup email system is working correctly!
        
        Backup details:
        - Time: Test run
        - Status: Success
        - File: test_backup.sql.gz
        - Size: 1.23 MB
        """
        
        msg.attach(MimeText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        print("✅ Test email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Email send failed: {e}")
        return False

def main():
    """Run email tests"""
    print("🧪 Email Configuration Test (No Phone Required)")
    print("=" * 60)
    
    print("\n📋 Available FREE Email Services (No Phone Required):")
    print("1. Mail.com - smtp.mail.com:587")
    print("2. GMX - mail.gmx.com:587") 
    print("3. ProtonMail - Requires Proton Mail Bridge")
    print("4. Tutanota - Requires paid plan for SMTP")
    
    print("\n🔧 To test your setup:")
    print("1. Create account at mail.com or gmx.com")
    print("2. Enable SMTP in email settings")
    print("3. Update backup_config.json with your credentials")
    print("4. Run: python3 scripts/test_backup.py")
    
    # Test connections
    print("\n📡 Testing SMTP connections...")
    test_mail_com()
    test_gmx()
    
    print("\n💡 Next Steps:")
    print("1. Choose an email service (Mail.com recommended)")
    print("2. Create account without phone verification")
    print("3. Enable SMTP access")
    print("4. Update backup_config.json")
    print("5. Test with: python3 scripts/test_backup.py")

if __name__ == "__main__":
    main()

