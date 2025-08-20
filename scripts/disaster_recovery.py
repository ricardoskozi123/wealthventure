#!/usr/bin/env python3
"""
Disaster Recovery Script for OMCRM Trading Platform
Enables rapid deployment to new servers in case of emergency
"""

import os
import sys
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
import shutil
import tempfile

class DisasterRecovery:
    """Handles disaster recovery operations"""
    
    def __init__(self, config_file="disaster_recovery_config.json"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        
    def load_config(self, config_file):
        """Load disaster recovery configuration"""
        config_path = Path(__file__).parent / config_file
        
        default_config = {
            "backup_sources": {
                "digitalocean": {
                    "enabled": True,
                    "space": "omcrm-backups",
                    "region": "nyc3",
                    "access_key": "",
                    "secret_key": ""
                },
                "aws_s3": {
                    "enabled": False,
                    "bucket": "omcrm-backups",
                    "region": "us-east-1",
                    "access_key": "",
                    "secret_key": ""
                }
            },
            "new_server": {
                "hostname": "",
                "username": "root",
                "ssh_key_path": "~/.ssh/id_rsa",
                "docker_compose_url": "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64"
            },
            "domains": {
                "client_domain": "investmentprohub.com",
                "crm_subdomain": "crm.investmentprohub.com",
                "temp_ip": "NEW_SERVER_IP"
            },
            "ssl": {
                "email": "admin@investmentprohub.com",
                "use_staging": False
            },
            "notifications": {
                "email": {
                    "enabled": True,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "to_addresses": []
                }
            }
        }
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)
        else:
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default disaster recovery config: {config_path}")
        
        return default_config
    
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("disaster_recovery.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def deploy_to_new_server(self, server_ip, ssh_key_path=None):
        """Deploy the entire platform to a new server"""
        try:
            self.logger.info(f"Starting disaster recovery deployment to {server_ip}")
            
            # Step 1: Setup new server
            self.setup_new_server(server_ip, ssh_key_path)
            
            # Step 2: Download and restore latest backup
            backup_file = self.download_latest_backup()
            
            # Step 3: Deploy application code
            self.deploy_application_code(server_ip, ssh_key_path)
            
            # Step 4: Setup SSL certificates
            self.setup_ssl_certificates(server_ip, ssh_key_path)
            
            # Step 5: Restore database
            self.restore_database(server_ip, ssh_key_path, backup_file)
            
            # Step 6: Start services
            self.start_services(server_ip, ssh_key_path)
            
            # Step 7: Verify deployment
            if self.verify_deployment(server_ip):
                self.logger.info("✅ Disaster recovery deployment successful!")
                self.send_notification(f"Disaster recovery completed successfully. New server: {server_ip}")
                return True
            else:
                self.logger.error("❌ Deployment verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Disaster recovery failed: {str(e)}")
            self.send_notification(f"Disaster recovery failed: {str(e)}")
            return False
    
    def setup_new_server(self, server_ip, ssh_key_path):
        """Setup new server with required dependencies"""
        self.logger.info("Setting up new server...")
        
        ssh_key = ssh_key_path or self.config["new_server"]["ssh_key_path"]
        
        # Install Docker and Docker Compose
        setup_commands = [
            "apt-get update",
            "apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release",
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg",
            'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null',
            "apt-get update",
            "apt-get install -y docker-ce docker-ce-cli containerd.io",
            "systemctl start docker",
            "systemctl enable docker",
            f"curl -L {self.config['new_server']['docker_compose_url']} -o /usr/local/bin/docker-compose",
            "chmod +x /usr/local/bin/docker-compose",
            "apt-get install -y postgresql-client-common postgresql-client",
            "mkdir -p /opt/omcrm"
        ]
        
        for cmd in setup_commands:
            self.run_ssh_command(server_ip, cmd, ssh_key)
    
    def download_latest_backup(self):
        """Download the latest backup from configured storage"""
        self.logger.info("Downloading latest backup...")
        
        # For now, implement DigitalOcean Spaces download
        if self.config["backup_sources"]["digitalocean"]["enabled"]:
            return self.download_from_digitalocean()
        elif self.config["backup_sources"]["aws_s3"]["enabled"]:
            return self.download_from_s3()
        else:
            raise Exception("No backup source configured")
    
    def download_from_digitalocean(self):
        """Download latest backup from DigitalOcean Spaces"""
        import boto3
        
        do_config = self.config["backup_sources"]["digitalocean"]
        session = boto3.session.Session()
        client = session.client(
            's3',
            region_name=do_config["region"],
            endpoint_url=f'https://{do_config["region"]}.digitaloceanspaces.com',
            aws_access_key_id=do_config["access_key"],
            aws_secret_access_key=do_config["secret_key"]
        )
        
        # List backups and get the latest
        response = client.list_objects_v2(Bucket=do_config["space"], Prefix="backups/")
        if not response.get('Contents'):
            raise Exception("No backups found in DigitalOcean Spaces")
        
        # Sort by last modified and get the latest
        latest_backup = sorted(response['Contents'], key=lambda x: x['LastModified'])[-1]
        backup_key = latest_backup['Key']
        
        # Download to temporary file
        temp_file = Path(tempfile.gettempdir()) / Path(backup_key).name
        client.download_file(do_config["space"], backup_key, str(temp_file))
        
        self.logger.info(f"Downloaded backup: {backup_key}")
        return temp_file
    
    def deploy_application_code(self, server_ip, ssh_key_path):
        """Deploy application code to new server"""
        self.logger.info("Deploying application code...")
        
        ssh_key = ssh_key_path or self.config["new_server"]["ssh_key_path"]
        
        # Create deployment package
        deployment_files = [
            "docker-compose.yml",
            "nginx/multi_domain.conf",
            "omcrm/",
            "scripts/",
            "requirements.txt",
            "Dockerfile"
        ]
        
        # Copy files to server
        for file_path in deployment_files:
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    self.run_local_command(f"scp -i {ssh_key} -r {file_path} root@{server_ip}:/opt/omcrm/")
                else:
                    self.run_local_command(f"scp -i {ssh_key} {file_path} root@{server_ip}:/opt/omcrm/")
        
        # Create environment configuration
        env_config = f"""
CLIENT_DOMAIN={self.config['domains']['client_domain']}
CRM_SUBDOMAIN={self.config['domains']['crm_subdomain']}
SECRET_KEY=omcrm-disaster-recovery-{datetime.now().strftime('%Y%m%d')}
FLASK_ENV=production
DATABASE_URL=postgresql://omcrm_user:omcrm_password_2024@db:5432/omcrm_trading
"""
        
        # Write environment file on server
        self.run_ssh_command(server_ip, f'echo "{env_config}" > /opt/omcrm/.env', ssh_key)
    
    def setup_ssl_certificates(self, server_ip, ssh_key_path):
        """Setup SSL certificates using Let's Encrypt"""
        self.logger.info("Setting up SSL certificates...")
        
        ssh_key = ssh_key_path or self.config["new_server"]["ssh_key_path"]
        ssl_config = self.config["ssl"]
        
        # Install Certbot
        certbot_commands = [
            "apt-get install -y certbot",
            "mkdir -p /opt/omcrm/ssl/investmentprohub.com"
        ]
        
        for cmd in certbot_commands:
            self.run_ssh_command(server_ip, cmd, ssh_key)
        
        # Get certificates for both domains
        staging_flag = "--staging" if ssl_config["use_staging"] else ""
        domains = [
            self.config["domains"]["client_domain"],
            self.config["domains"]["crm_subdomain"]
        ]
        
        for domain in domains:
            cert_cmd = f"certbot certonly --standalone --email {ssl_config['email']} --agree-tos --no-eff-email {staging_flag} -d {domain}"
            self.run_ssh_command(server_ip, cert_cmd, ssh_key)
            
            # Copy certificates to nginx directory
            self.run_ssh_command(server_ip, f"cp /etc/letsencrypt/live/{domain}/fullchain.pem /opt/omcrm/ssl/investmentprohub.com/cert.pem", ssh_key)
            self.run_ssh_command(server_ip, f"cp /etc/letsencrypt/live/{domain}/privkey.pem /opt/omcrm/ssl/investmentprohub.com/key.pem", ssh_key)
    
    def restore_database(self, server_ip, ssh_key_path, backup_file):
        """Restore database from backup"""
        self.logger.info("Restoring database...")
        
        ssh_key = ssh_key_path or self.config["new_server"]["ssh_key_path"]
        
        # Copy backup file to server
        self.run_local_command(f"scp -i {ssh_key} {backup_file} root@{server_ip}:/opt/omcrm/")
        
        # Start database container first
        self.run_ssh_command(server_ip, "cd /opt/omcrm && docker-compose up -d db", ssh_key)
        
        # Wait for database to be ready
        self.run_ssh_command(server_ip, "sleep 30", ssh_key)
        
        # Restore backup
        backup_filename = Path(backup_file).name
        if backup_filename.endswith('.gz'):
            restore_cmd = f"cd /opt/omcrm && gunzip -c {backup_filename} | docker-compose exec -T db psql -U omcrm_user -d omcrm_trading"
        else:
            restore_cmd = f"cd /opt/omcrm && docker-compose exec -T db psql -U omcrm_user -d omcrm_trading < {backup_filename}"
        
        self.run_ssh_command(server_ip, restore_cmd, ssh_key)
    
    def start_services(self, server_ip, ssh_key_path):
        """Start all services"""
        self.logger.info("Starting services...")
        
        ssh_key = ssh_key_path or self.config["new_server"]["ssh_key_path"]
        
        # Copy nginx config and start all services
        commands = [
            "cd /opt/omcrm",
            "cp nginx/multi_domain.conf nginx/app.conf",
            "docker-compose down",
            "docker-compose build --no-cache",
            "docker-compose up -d"
        ]
        
        for cmd in commands:
            self.run_ssh_command(server_ip, cmd, ssh_key)
    
    def verify_deployment(self, server_ip):
        """Verify that the deployment is working"""
        self.logger.info("Verifying deployment...")
        
        # Simple health check
        try:
            import requests
            response = requests.get(f"http://{server_ip}", timeout=30)
            return response.status_code == 200
        except:
            return False
    
    def run_ssh_command(self, server_ip, command, ssh_key_path):
        """Run command on remote server via SSH"""
        ssh_cmd = f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no root@{server_ip} '{command}'"
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.logger.error(f"SSH command failed: {command}")
            self.logger.error(f"Error: {result.stderr}")
            raise Exception(f"SSH command failed: {result.stderr}")
        
        return result.stdout
    
    def run_local_command(self, command):
        """Run command locally"""
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.logger.error(f"Local command failed: {command}")
            self.logger.error(f"Error: {result.stderr}")
            raise Exception(f"Local command failed: {result.stderr}")
        
        return result.stdout
    
    def send_notification(self, message):
        """Send notification about disaster recovery status"""
        try:
            if self.config["notifications"]["email"]["enabled"]:
                self.send_email_notification(message)
        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")
    
    def send_email_notification(self, message):
        """Send email notification"""
        import smtplib
        from email.mime.text import MimeText
        
        email_config = self.config["notifications"]["email"]
        
        msg = MimeText(message)
        msg['Subject'] = "OMCRM Disaster Recovery Update"
        msg['From'] = email_config["username"]
        msg['To'] = ", ".join(email_config["to_addresses"])
        
        with smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"]) as server:
            server.starttls()
            server.login(email_config["username"], email_config["password"])
            server.send_message(msg)

def main():
    """Main disaster recovery function"""
    if len(sys.argv) < 2:
        print("Usage: python disaster_recovery.py <new_server_ip> [ssh_key_path]")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    ssh_key_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    dr = DisasterRecovery()
    success = dr.deploy_to_new_server(server_ip, ssh_key_path)
    
    if success:
        print(f"✅ Disaster recovery completed! Your platform is now running on {server_ip}")
        print(f"🌐 Update your DNS records to point to {server_ip}")
        print(f"📧 Check your email for detailed deployment report")
    else:
        print("❌ Disaster recovery failed. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 