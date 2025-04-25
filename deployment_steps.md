# Quick Deployment Guide for OMCRM to Linux VPS

This guide provides a simplified deployment process for your OMCRM application to a Linux VPS.

## Step 1: Prepare Your Server

Connect to your VPS and install requirements:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv git nginx

# Install PostgreSQL (optional, you can use SQLite for testing)
sudo apt install -y postgresql postgresql-contrib
```

## Step 2: Set Up Database (Optional for PostgreSQL)

```bash
# Create PostgreSQL database and user
sudo -u postgres psql -c "CREATE DATABASE omcrm;"
sudo -u postgres psql -c "CREATE USER omuser WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE omcrm TO omuser;"
```

## Step 3: Deploy Your Application

```bash
# Create directory for the application
sudo mkdir -p /var/www/omcrm
sudo chown -R $USER:$USER /var/www/omcrm

# Clone or transfer your application
# Option 1: Use scp to transfer your files
cd /path/to/your/local/project
tar -czf omcrm.tar.gz .
scp omcrm.tar.gz username@your-vps-ip:/var/www/omcrm/

# On the server:
cd /var/www/omcrm
tar -xzf omcrm.tar.gz
```

## Step 4: Set Up Python Environment

```bash
# Create and activate virtual environment
cd /var/www/omcrm
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn  # Make sure gunicorn is installed
```

## Step 5: Configure Database

If using SQLite (for testing):
```bash
# Use the existing dev.db file or initialize a new one
flask db upgrade
```

If using PostgreSQL:
```bash
# Edit config to use PostgreSQL
# Update the DATABASE_URL in your config
export DATABASE_URL="postgresql://omuser:your_secure_password@localhost/omcrm"
flask db upgrade
```

## Step 6: Test Your Application

```bash
# Run the application directly to test
python run.py
```

## Step 7: Set Up Gunicorn Service

```bash
# Create a systemd service file
sudo nano /etc/systemd/system/omcrm.service
```

Add this content:
```
[Unit]
Description=OMCRM Gunicorn Web Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/omcrm
Environment="PATH=/var/www/omcrm/venv/bin"
ExecStart=/var/www/omcrm/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
# Change permissions 
sudo chown -R www-data:www-data /var/www/omcrm

# Start and enable the service
sudo systemctl start omcrm
sudo systemctl enable omcrm
```

## Step 8: Configure Nginx as Reverse Proxy

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/omcrm
```

Add this content:
```
server {
    listen 80;
    server_name your_domain_or_ip;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /var/www/omcrm;
    }

    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://localhost:8000;
    }
}
```

```bash
# Enable the site and restart Nginx
sudo ln -s /etc/nginx/sites-available/omcrm /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

## Step 9: Set Up Firewall (Optional)

```bash
# Configure firewall
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable
```

## Step 10: Set Up SSL with Let's Encrypt (Optional)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your_domain.com
```

## Troubleshooting

1. Check the application logs:
```bash
sudo journalctl -u omcrm
```

2. Check Nginx logs:
```bash
sudo tail -f /var/log/nginx/error.log
```

3. Test Gunicorn directly:
```bash
cd /var/www/omcrm
source venv/bin/activate
gunicorn --bind 0.0.0.0:8000 wsgi:application
``` 