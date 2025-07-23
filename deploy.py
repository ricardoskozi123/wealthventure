#!/usr/bin/env python3
"""
Deployment script for the application
This script handles the deployment process and can be run manually or via CI/CD
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/deployment.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def run_command(command, cwd=None):
    """Run a shell command and return its output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {command}")
        logging.error(f"Error: {e.stderr}")
        raise

def backup_database():
    """Create a backup of the database"""
    backup_dir = "backup"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/backup_{timestamp}.sql"
    
    try:
        run_command(f"sqlite3 instance/site.db .dump > {backup_file}")
        logging.info(f"Database backed up to {backup_file}")
    except Exception as e:
        logging.error(f"Database backup failed: {e}")

def deploy():
    """Main deployment function"""
    try:
        # 1. Backup database
        backup_database()
        
        # 2. Pull latest changes
        logging.info("Pulling latest changes...")
        run_command("git pull origin main")
        
        # 3. Stop existing containers
        logging.info("Stopping existing containers...")
        run_command("docker-compose down")
        
        # 4. Build and start new containers
        logging.info("Building and starting new containers...")
        run_command("docker-compose up -d --build")
        
        # 5. Verify deployment
        logging.info("Verifying deployment...")
        containers = run_command("docker ps")
        logging.info(f"Running containers:\n{containers}")
        
        logging.info("Deployment completed successfully!")
        
    except Exception as e:
        logging.error(f"Deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    deploy() 