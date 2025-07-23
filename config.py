import os
from datetime import timedelta

class Config:
    # Secret key for securing sessions and tokens
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')
    
    # Database configuration - SQLite pointing to dev.db with crypto instruments
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Mail configuration (generic settings for demo)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'user@example.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'password')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')
    
    # API Keys 
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY', 'demo')

    # Flask-Login remember cookie duration
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    
    # Upload folder for files
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'omcrm', 'static', 'uploads')
    
    # Maximum content length for uploads (16MB)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Demo mode settings
    DEMO_MODE = True
    DEMO_RESET_INTERVAL = 24  # Hours

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # In production, set this to a proper PostgreSQL or MySQL connection
    # but for now, keep SQLite for simplicity
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'  # Updated to use dev.db 