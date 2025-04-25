"""
Deployment configuration file for OMCRM+WebTrader
This file contains production-ready settings for deploying the application to a VPS.
Copy and modify these settings according to your environment.
"""

import os
from datetime import timedelta

# Basic application config
DEBUG = False
TESTING = False
SECRET_KEY = 'generate_a_long_random_string_for_production'  # Change this!
PERMANENT_SESSION_LIFETIME = timedelta(days=1)

# Database configuration
# For PostgreSQL (recommended for production)
SQLALCHEMY_DATABASE_URI = 'postgresql://omuser:your_secure_password@localhost/omcrm'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False

# Email configuration
MAIL_SERVER = 'smtp.example.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'your_email@example.com'
MAIL_PASSWORD = 'your_email_password'  # Use environment variable in production
MAIL_DEFAULT_SENDER = ('OMCRM', 'noreply@example.com')
MAIL_DEBUG = False

# WebTrader API keys
# Replace with your actual API keys
ALPHAVANTAGE_API_KEY = 'your_alphavantage_api_key'
FINNHUB_API_KEY = 'your_finnhub_api_key'

# Security settings
SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing cookies
REMEMBER_COOKIE_SECURE = True
REMEMBER_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_DURATION = timedelta(days=30)

# File uploads
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_TO_FILE = True
LOG_FILENAME = '/var/log/omcrm/app.log'  # Make sure this directory exists and is writable

# Cache settings
CACHE_TYPE = 'SimpleCache'
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes

# Rate limiting
RATELIMIT_ENABLED = True
RATELIMIT_DEFAULTS_PER_METHOD = True
RATELIMIT_HEADERS_ENABLED = True 
