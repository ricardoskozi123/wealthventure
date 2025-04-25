from .config_vars import *
import os


class Config(object):
    DEBUG = False
    TESTING = False
    RBAC_USE_WHITE = True
    PYTHON_VER_MIN_REQUIRED = '3.5.0'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = "csrf-secret-key"


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = DEV_SECRET_KEY
    # Use SQLite instead of PostgreSQL for easier setup
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'dev.db')
    # Original PostgreSQL connection string:
    # SQLALCHEMY_DATABASE_URI = f'postgresql://{DEV_DB_USER}:{DEV_DB_PASS}@{DEV_DB_HOST}/{DEV_DB_NAME}'


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = TEST_SECRET_KEY
    SQLALCHEMY_DATABASE_URI = f'postgresql://{TEST_DB_USER}:{TEST_DB_PASS}@{TEST_DB_HOST}/{TEST_DB_NAME}'


class ProductionConfig(Config):
    SECRET_KEY = SECRET_KEY
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}'





