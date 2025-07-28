"""
Multi-Brand Email Service
Handles email sending with dynamic SMTP configuration per brand
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app, request, session
from omcrm.settings.models import AppConfig
from omcrm import db


class EmailService:
    """
    Dynamic email service that configures SMTP settings based on brand/context
    """
    
    @staticmethod
    def get_smtp_config(brand_name=None):
        """
        Get SMTP configuration for a specific brand or use default
        Priority: Brand DB config > App DB config > Environment variables > Defaults
        """
        # Try to get brand-specific configuration from database first
        if brand_name:
            # You can extend this to support brand-specific SMTP configs
            # For now, we'll use the app config but this is extensible
            pass
        
        # Get general app configuration from database
        app_config = AppConfig.query.first()
        
        if app_config and app_config.smtp_server:
            return {
                'smtp_server': app_config.smtp_server,
                'smtp_port': int(app_config.smtp_port) if app_config.smtp_port else 587,
                'smtp_encryption': app_config.smtp_encryption or 'TLS',
                'sender_name': app_config.sender_name or 'OMCRM Trading',
                'sender_email': app_config.sender_email,
                'smtp_username': app_config.sender_email,  # Usually same as sender email
                'smtp_password': os.environ.get('SMTP_PASSWORD'),  # Always from env for security
                'smtp_charset': app_config.smtp_charset or 'utf-8'
            }
        
        # Fallback to environment variables
        return {
            'smtp_server': os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.environ.get('MAIL_PORT', 587)),
            'smtp_encryption': 'TLS',
            'sender_name': os.environ.get('MAIL_SENDER_NAME', current_app.config.get('PLATFORM_NAME', 'OMCRM Trading')),
            'sender_email': os.environ.get('MAIL_USERNAME'),
            'smtp_username': os.environ.get('MAIL_USERNAME'),
            'smtp_password': os.environ.get('MAIL_PASSWORD'),
            'smtp_charset': 'utf-8'
        }
    
    @staticmethod
    def send_email(to_email, subject, html_content, text_content=None, brand_name=None, attachments=None):
        """
        Send email using dynamic SMTP configuration
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            html_content (str): HTML email content
            text_content (str): Plain text email content (optional)
            brand_name (str): Brand name for SMTP config selection (optional)
            attachments (list): List of file paths to attach (optional)
        
        Returns:
            dict: {'success': bool, 'message': str, 'config_used': dict}
        """
        try:
            # Get SMTP configuration
            smtp_config = EmailService.get_smtp_config(brand_name)
            
            # Validate required configuration
            if not smtp_config.get('sender_email'):
                return {
                    'success': False,
                    'message': 'No sender email configured. Please configure SMTP settings.',
                    'config_used': smtp_config
                }
            
            if not smtp_config.get('smtp_password'):
                return {
                    'success': False,
                    'message': 'No SMTP password configured. Please set SMTP_PASSWORD environment variable.',
                    'config_used': smtp_config
                }
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{smtp_config['sender_name']} <{smtp_config['sender_email']}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain', smtp_config['smtp_charset'])
                msg.attach(text_part)
            
            # Add HTML content
            if html_content:
                html_part = MIMEText(html_content, 'html', smtp_config['smtp_charset'])
                msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for file_path in attachments:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
            
            # Connect to SMTP server and send email
            if smtp_config['smtp_encryption'].upper() == 'SSL':
                server = smtplib.SMTP_SSL(smtp_config['smtp_server'], smtp_config['smtp_port'])
            else:
                server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
                if smtp_config['smtp_encryption'].upper() == 'TLS':
                    server.starttls()
            
            # Login and send
            server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
            text = msg.as_string()
            server.sendmail(smtp_config['sender_email'], to_email, text)
            server.quit()
            
            return {
                'success': True,
                'message': f'Email sent successfully to {to_email}',
                'config_used': {k: v for k, v in smtp_config.items() if k != 'smtp_password'}  # Don't return password
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to send email: {str(e)}',
                'config_used': {k: v for k, v in smtp_config.items() if k != 'smtp_password'}
            }
    
    @staticmethod
    def test_smtp_connection(brand_name=None):
        """
        Test SMTP connection without sending an email
        
        Args:
            brand_name (str): Brand name for SMTP config selection (optional)
        
        Returns:
            dict: {'success': bool, 'message': str, 'config_used': dict}
        """
        try:
            smtp_config = EmailService.get_smtp_config(brand_name)
            
            if not smtp_config.get('sender_email') or not smtp_config.get('smtp_password'):
                return {
                    'success': False,
                    'message': 'SMTP configuration incomplete',
                    'config_used': {k: v for k, v in smtp_config.items() if k != 'smtp_password'}
                }
            
            # Test connection
            if smtp_config['smtp_encryption'].upper() == 'SSL':
                server = smtplib.SMTP_SSL(smtp_config['smtp_server'], smtp_config['smtp_port'])
            else:
                server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
                if smtp_config['smtp_encryption'].upper() == 'TLS':
                    server.starttls()
            
            server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
            server.quit()
            
            return {
                'success': True,
                'message': 'SMTP connection successful',
                'config_used': {k: v for k, v in smtp_config.items() if k != 'smtp_password'}
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'SMTP connection failed: {str(e)}',
                'config_used': {k: v for k, v in smtp_config.items() if k != 'smtp_password'}
            }


class EmailTemplates:
    """
    Email template manager for different types of emails
    """
    
    @staticmethod
    def password_reset_template(user_name, reset_link, platform_name, expiry_minutes=30):
        """
        Generate password reset email template
        
        Args:
            user_name (str): User's name
            reset_link (str): Password reset link
            platform_name (str): Brand/platform name
            expiry_minutes (int): Link expiry time in minutes
        
        Returns:
            dict: {'html': str, 'text': str, 'subject': str}
        """
        subject = f"Password Reset - {platform_name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background-color: #0a0a0f; color: #ffffff; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #00d4aa 0%, #00f5ff 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: rgba(255, 255, 255, 0.05); padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #00d4aa, #00f5ff); color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; font-weight: 600; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding: 20px; text-align: center; color: rgba(255, 255, 255, 0.7); font-size: 14px; }}
                .warning {{ background: rgba(255, 107, 107, 0.1); border-left: 4px solid #ff6b6b; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; color: white;">🔐 Password Reset</h1>
                    <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.9);">{platform_name}</p>
                </div>
                <div class="content">
                    <h2>Hello {user_name},</h2>
                    <p>You have requested to reset your password for your {platform_name} account.</p>
                    <p>Click the button below to reset your password:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset My Password</a>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Important:</strong>
                        <ul style="margin: 10px 0;">
                            <li>This link will expire in {expiry_minutes} minutes</li>
                            <li>If you didn't request this reset, please ignore this email</li>
                            <li>Never share this link with anyone</li>
                        </ul>
                    </div>
                    
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: rgba(255,255,255,0.1); padding: 10px; border-radius: 5px; font-family: monospace;">
                        {reset_link}
                    </p>
                    
                    <p style="margin-top: 30px;">Best regards,<br>The {platform_name} Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>If you need help, contact our support team.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset - {platform_name}
        
        Hello {user_name},
        
        You have requested to reset your password for your {platform_name} account.
        
        Please visit the following link to reset your password:
        {reset_link}
        
        Important:
        - This link will expire in {expiry_minutes} minutes
        - If you didn't request this reset, please ignore this email
        - Never share this link with anyone
        
        Best regards,
        The {platform_name} Team
        
        This is an automated message. Please do not reply to this email.
        """
        
        return {
            'html': html_content,
            'text': text_content,
            'subject': subject
        }
    
    @staticmethod
    def welcome_email_template(user_name, login_link, platform_name, temp_password=None):
        """
        Generate welcome email template for new clients
        """
        subject = f"Welcome to {platform_name} - Your Trading Account is Ready!"
        
        password_section = ""
        if temp_password:
            password_section = f"""
            <div class="warning">
                <strong>🔑 Your Temporary Login Details:</strong><br>
                <strong>Password:</strong> {temp_password}<br>
                <em>Please change this password after your first login.</em>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background-color: #0a0a0f; color: #ffffff; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #00d4aa 0%, #00f5ff 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: rgba(255, 255, 255, 0.05); padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #00d4aa, #00f5ff); color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; font-weight: 600; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding: 20px; text-align: center; color: rgba(255, 255, 255, 0.7); font-size: 14px; }}
                .warning {{ background: rgba(255, 193, 7, 0.1); border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; color: white;">🎉 Welcome to {platform_name}!</h1>
                </div>
                <div class="content">
                    <h2>Hello {user_name},</h2>
                    <p>Welcome to {platform_name}! Your trading account has been successfully created.</p>
                    
                    {password_section}
                    
                    <div style="text-align: center;">
                        <a href="{login_link}" class="button">Access Your Account</a>
                    </div>
                    
                    <p>Start your trading journey with our advanced tools and real-time market data.</p>
                    
                    <p style="margin-top: 30px;">Best regards,<br>The {platform_name} Team</p>
                </div>
                <div class="footer">
                    <p>Need help? Contact our support team anytime.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return {
            'html': html_content,
            'subject': subject
        } 