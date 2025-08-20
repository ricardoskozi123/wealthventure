#!/usr/bin/env python3
"""
Automated Database Backup System for OMCRM Trading Platform
Supports multiple storage backends: AWS S3, Google Cloud, Azure, DigitalOcean Spaces, Local
"""

import os
import sys
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
import logging
from pathlib import Path
import boto3
from google.cloud import storage as gcs
from azure.storage.blob import BlobServiceClient
import ftplib
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import json

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class BackupManager:
    """Manages database backups with multiple storage options"""
    
    def __init__(self, config_file="backup_config.json"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        
    def load_config(self, config_file):
        """Load backup configuration"""
        config_path = Path(__file__).parent / config_file
        
        # Default configuration
        default_config = {
            "database": {
                "type": "postgresql",  # postgresql, mysql, sqlite
                "host": "localhost",
                "port": 5432,
                "name": "omcrm_trading",
                "user": "omcrm_user",
                "password": "omcrm_password_2024"
            },
            "storage": {
                "primary": "local",  # local, s3, gcs, azure, digitalocean
                "backup_location": "/app/backup",
                "retention_days": 30,
                "compress": True
            },
            "aws_s3": {
                "enabled": False,
                "bucket": "omcrm-backups",
                "region": "us-east-1",
                "access_key": "",
                "secret_key": ""
            },
            "google_cloud": {
                "enabled": False,
                "bucket": "omcrm-backups",
                "credentials_path": ""
            },
            "azure": {
                "enabled": False,
                "container": "omcrm-backups",
                "connection_string": ""
            },
            "digitalocean": {
                "enabled": False,
                "space": "omcrm-backups",
                "region": "nyc3",
                "access_key": "",
                "secret_key": ""
            },
            "ftp": {
                "enabled": False,
                "host": "",
                "username": "",
                "password": "",
                "directory": "/backups"
            },
            "notifications": {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "to_addresses": []
                },
                "webhook": {
                    "enabled": False,
                    "url": ""
                }
            }
        }
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                # Merge with defaults
                default_config.update(loaded_config)
        else:
            # Create default config file
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default config file: {config_path}")
        
        return default_config
    
    def setup_logging(self):
        """Setup logging for backup operations"""
        log_dir = Path("/app/logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "backup.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def create_backup(self):
        """Create database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"omcrm_backup_{timestamp}"
        
        try:
            # Create backup directory
            backup_dir = Path(self.config["storage"]["backup_location"])
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            db_config = self.config["database"]
            
            if db_config["type"] == "postgresql":
                backup_file = self.backup_postgresql(backup_dir, backup_name, db_config)
            elif db_config["type"] == "mysql":
                backup_file = self.backup_mysql(backup_dir, backup_name, db_config)
            elif db_config["type"] == "sqlite":
                backup_file = self.backup_sqlite(backup_dir, backup_name, db_config)
            else:
                raise ValueError(f"Unsupported database type: {db_config['type']}")
            
            # Compress backup if enabled
            if self.config["storage"]["compress"]:
                backup_file = self.compress_backup(backup_file)
            
            # Upload to configured storage backends
            self.upload_backup(backup_file)
            
            # Clean old backups
            self.cleanup_old_backups()
            
            # Send notifications
            self.send_notifications(backup_file, success=True)
            
            self.logger.info(f"Backup completed successfully: {backup_file.name}")
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            self.send_notifications(None, success=False, error=str(e))
            raise
    
    def backup_postgresql(self, backup_dir, backup_name, db_config):
        """Create PostgreSQL backup using pg_dump"""
        backup_file = backup_dir / f"{backup_name}.sql"
        
        # Set environment variables for pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config['password']
        
        cmd = [
            'pg_dump',
            '-h', db_config['host'],
            '-p', str(db_config['port']),
            '-U', db_config['user'],
            '-d', db_config['name'],
            '--no-password',
            '--verbose',
            '--clean',
            '--if-exists',
            '--create',
            '-f', str(backup_file)
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")
        
        self.logger.info(f"PostgreSQL backup created: {backup_file}")
        return backup_file
    
    def backup_mysql(self, backup_dir, backup_name, db_config):
        """Create MySQL backup using mysqldump"""
        backup_file = backup_dir / f"{backup_name}.sql"
        
        cmd = [
            'mysqldump',
            '-h', db_config['host'],
            '-P', str(db_config['port']),
            '-u', db_config['user'],
            f'-p{db_config["password"]}',
            '--single-transaction',
            '--routines',
            '--triggers',
            db_config['name']
        ]
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"mysqldump failed: {result.stderr}")
        
        self.logger.info(f"MySQL backup created: {backup_file}")
        return backup_file
    
    def backup_sqlite(self, backup_dir, backup_name, db_config):
        """Create SQLite backup"""
        # For SQLite, we need to find the database file
        # Check common locations
        possible_paths = [
            f"/app/{db_config['name']}",
            f"/app/instance/{db_config['name']}",
            f"/app/dev.db",
            f"/app/instance/site.db"
        ]
        
        db_path = None
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                break
        
        if not db_path:
            raise FileNotFoundError("SQLite database file not found")
        
        backup_file = backup_dir / f"{backup_name}.db"
        shutil.copy2(db_path, backup_file)
        
        self.logger.info(f"SQLite backup created: {backup_file}")
        return backup_file
    
    def compress_backup(self, backup_file):
        """Compress backup file using gzip"""
        compressed_file = Path(str(backup_file) + '.gz')
        
        with open(backup_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original file
        backup_file.unlink()
        
        self.logger.info(f"Backup compressed: {compressed_file}")
        return compressed_file
    
    def upload_backup(self, backup_file):
        """Upload backup to configured storage backends"""
        if self.config["aws_s3"]["enabled"]:
            self.upload_to_s3(backup_file)
        
        if self.config["google_cloud"]["enabled"]:
            self.upload_to_gcs(backup_file)
        
        if self.config["azure"]["enabled"]:
            self.upload_to_azure(backup_file)
        
        if self.config["digitalocean"]["enabled"]:
            self.upload_to_digitalocean(backup_file)
        
        if self.config["ftp"]["enabled"]:
            self.upload_to_ftp(backup_file)
    
    def upload_to_s3(self, backup_file):
        """Upload backup to AWS S3"""
        try:
            s3_config = self.config["aws_s3"]
            s3_client = boto3.client(
                's3',
                aws_access_key_id=s3_config["access_key"],
                aws_secret_access_key=s3_config["secret_key"],
                region_name=s3_config["region"]
            )
            
            key = f"backups/{backup_file.name}"
            s3_client.upload_file(str(backup_file), s3_config["bucket"], key)
            self.logger.info(f"Backup uploaded to S3: s3://{s3_config['bucket']}/{key}")
            
        except Exception as e:
            self.logger.error(f"S3 upload failed: {str(e)}")
    
    def upload_to_gcs(self, backup_file):
        """Upload backup to Google Cloud Storage"""
        try:
            gcs_config = self.config["google_cloud"]
            client = gcs.Client.from_service_account_json(gcs_config["credentials_path"])
            bucket = client.bucket(gcs_config["bucket"])
            
            blob_name = f"backups/{backup_file.name}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(backup_file))
            
            self.logger.info(f"Backup uploaded to GCS: gs://{gcs_config['bucket']}/{blob_name}")
            
        except Exception as e:
            self.logger.error(f"GCS upload failed: {str(e)}")
    
    def upload_to_azure(self, backup_file):
        """Upload backup to Azure Blob Storage"""
        try:
            azure_config = self.config["azure"]
            blob_client = BlobServiceClient.from_connection_string(azure_config["connection_string"])
            
            blob_name = f"backups/{backup_file.name}"
            with open(backup_file, "rb") as data:
                blob_client.get_blob_client(
                    container=azure_config["container"],
                    blob=blob_name
                ).upload_blob(data, overwrite=True)
            
            self.logger.info(f"Backup uploaded to Azure: {azure_config['container']}/{blob_name}")
            
        except Exception as e:
            self.logger.error(f"Azure upload failed: {str(e)}")
    
    def upload_to_digitalocean(self, backup_file):
        """Upload backup to DigitalOcean Spaces"""
        try:
            do_config = self.config["digitalocean"]
            session = boto3.session.Session()
            client = session.client(
                's3',
                region_name=do_config["region"],
                endpoint_url=f'https://{do_config["region"]}.digitaloceanspaces.com',
                aws_access_key_id=do_config["access_key"],
                aws_secret_access_key=do_config["secret_key"]
            )
            
            key = f"backups/{backup_file.name}"
            client.upload_file(str(backup_file), do_config["space"], key)
            self.logger.info(f"Backup uploaded to DO Spaces: {do_config['space']}/{key}")
            
        except Exception as e:
            self.logger.error(f"DigitalOcean Spaces upload failed: {str(e)}")
    
    def upload_to_ftp(self, backup_file):
        """Upload backup to FTP server"""
        try:
            ftp_config = self.config["ftp"]
            with ftplib.FTP(ftp_config["host"]) as ftp:
                ftp.login(ftp_config["username"], ftp_config["password"])
                ftp.cwd(ftp_config["directory"])
                
                with open(backup_file, 'rb') as f:
                    ftp.storbinary(f'STOR {backup_file.name}', f)
            
            self.logger.info(f"Backup uploaded to FTP: {ftp_config['host']}/{backup_file.name}")
            
        except Exception as e:
            self.logger.error(f"FTP upload failed: {str(e)}")
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        try:
            backup_dir = Path(self.config["storage"]["backup_location"])
            retention_days = self.config["storage"]["retention_days"]
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for backup_file in backup_dir.glob("omcrm_backup_*"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()
                    self.logger.info(f"Removed old backup: {backup_file.name}")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
    
    def send_notifications(self, backup_file, success=True, error=None):
        """Send backup notifications"""
        if self.config["notifications"]["email"]["enabled"]:
            self.send_email_notification(backup_file, success, error)
    
    def send_email_notification(self, backup_file, success, error):
        """Send email notification about backup status"""
        try:
            email_config = self.config["notifications"]["email"]
            
            msg = MimeMultipart()
            msg['From'] = email_config["username"]
            msg['To'] = ", ".join(email_config["to_addresses"])
            
            if success:
                msg['Subject'] = "OMCRM Backup Successful"
                body = f"""
                Backup completed successfully!
                
                Backup file: {backup_file.name if backup_file else 'N/A'}
                Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                Size: {backup_file.stat().st_size / 1024 / 1024:.2f} MB
                """
            else:
                msg['Subject'] = "OMCRM Backup Failed"
                body = f"""
                Backup failed!
                
                Error: {error}
                Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
            
            msg.attach(MimeText(body, 'plain'))
            
            with smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"]) as server:
                server.starttls()
                server.login(email_config["username"], email_config["password"])
                server.send_message(msg)
            
            self.logger.info("Email notification sent")
            
        except Exception as e:
            self.logger.error(f"Email notification failed: {str(e)}")

def main():
    """Main backup function"""
    backup_manager = BackupManager()
    backup_manager.create_backup()

if __name__ == "__main__":
    main() 