from .config_vars import *
import os

class Config(object):
    DEBUG = False
    TESTING = False
    RBAC_USE_WHITE = True
    PYTHON_VER_MIN_REQUIRED = '3.5.0'
    SECRET_KEY = SECRET_KEY
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = SECRET_KEY
    PLATFORM_NAME = PLATFORM_NAME

# Use the same simple config for everything - no complexity!
DevelopmentConfig = Config
TestConfig = Config  
ProductionConfig = Config





