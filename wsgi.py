#!/usr/bin/env python3
"""
WSGI entry point for production deployment
This file is used by Gunicorn to serve the application
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Add the project directory to the Python path
project_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_dir)

# Import the app
from run import app as application

# Configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')

file_handler = RotatingFileHandler('logs/omcrm.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)

application.logger.addHandler(file_handler)
application.logger.setLevel(logging.INFO)
application.logger.info('OMCRM startup')

# This is the WSGI entry point
if __name__ == "__main__":
    application.run() 
