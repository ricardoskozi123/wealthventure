# OMCRM + WebTrader VPS Deployment Guide

This guide explains how to deploy your OMCRM application with WebTrader to a VPS for testing.

## Prerequisites

- A VPS with Ubuntu 20.04 or newer
- SSH access to your VPS
- Domain name (optional, but recommended)
- Basic knowledge of Linux commands

## Step 1: Set Up Your VPS

1. Connect to your VPS via SSH:
   ```
   ssh username@your-server-ip
   ```

2. Update the system:
   ```
   sudo apt update && sudo apt upgrade -y
   ```

3. Install required dependencies:
   ```
   sudo apt install -y python3 python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv git nginx
   ```

4. Install PostgreSQL (recommended for production):
   ```
   sudo apt install -y postgresql postgresql-contrib
   ```

## Step 2: Create a Database (PostgreSQL)

1. Log in to PostgreSQL:
   ```
   sudo -u postgres psql
   ```

2. Create a database and user:
   ```sql
   CREATE DATABASE omcrm;
   CREATE USER omuser WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE omcrm TO omuser;
   \q
   ```

## Step 3: Clone the Repository

1. Navigate to where you want to store the application:
   ```
   cd /var/www
   ```

2. Clone your repository:
   ```
   sudo git clone https://github.com/yourusername/omcrm.git
   ```

3. Set ownership:
   ```
   sudo chown -R $USER:$USER /var/www/omcrm
   ```

## Step 4: Set Up Python Environment

1. Create a virtual environment:
   ```
   cd /var/www/omcrm
   python3 -m venv venv
   ```

2. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install additional packages needed for the WebTrader:
   ```
   pip install yfinance plotly alpaca-trade-api
   ```

## Step 5: Configure the Application

1. Create a configuration file:
   ```
   cp omcrm/config_vars.example omcrm/config_vars.py
   ```

2. Edit the configuration file:
   ```
   nano omcrm/config_vars.py
   ```

3. Update the configuration with your database details:
   ```python
   # Database configuration
   SQLALCHEMY_DATABASE_URI = 'postgresql://omuser:your_secure_password@localhost/omcrm'
   
   # Secret key
   SECRET_KEY = 'generate_a_secure_random_key'
   
   # Email configuration
   MAIL_SERVER = 'smtp.example.com'
   MAIL_PORT = 587
   MAIL_USE_TLS = True
   MAIL_USERNAME = 'your_email@example.com'
   MAIL_PASSWORD = 'your_email_password'
   ```

## Step 6: Initialize the Database

1. From the application root directory, create the database schema:
   ```
   flask db upgrade
   ```

2. (Optional) Create an admin user if your app doesn't have a registration page:
   ```
   python manage.py create_admin --email admin@example.com --password your_secure_password
   ```

## Step 7: Configure Gunicorn

1. Create a systemd service file:
   ```
   sudo nano /etc/systemd/system/omcrm.service
   ```

2. Add the following content:
   ```
   [Unit]
   Description=OMCRM Gunicorn instance
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/omcrm
   Environment="PATH=/var/www/omcrm/venv/bin"
   ExecStart=/var/www/omcrm/venv/bin/gunicorn --workers 3 --bind unix:omcrm.sock -m 007 run:app

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```
   sudo systemctl start omcrm
   sudo systemctl enable omcrm
   ```

## Step 8: Configure Nginx for Domain Separation

We'll configure Nginx to handle two different domains:
- `crm.example.com` - For admin/agent access to the CRM system
- `example.com` - For client access to the trading platform

1. Create an Nginx server block for the CRM subdomain:
   ```
   sudo nano /etc/nginx/sites-available/crm.example.com
   ```

2. Add the following configuration:
   ```nginx
   server {
       listen 80;
       server_name crm.example.com;  # CRM subdomain for admins/agents

       location = /favicon.ico { access_log off; log_not_found off; }
       
       location /static/ {
           root /var/www/omcrm;
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/var/www/omcrm/omcrm.sock;
       }
   }
   ```

3. Create an Nginx server block for the main domain (client access):
   ```
   sudo nano /etc/nginx/sites-available/example.com
   ```

4. Add the following configuration:
   ```nginx
   server {
       listen 80;
       server_name example.com www.example.com;  # Main domain for clients

       location = /favicon.ico { access_log off; log_not_found off; }
       
       location /static/ {
           root /var/www/omcrm;
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/var/www/omcrm/omcrm.sock;
       }
   }
   ```

5. Enable the configurations:
   ```
   sudo ln -s /etc/nginx/sites-available/crm.example.com /etc/nginx/sites-enabled/
   sudo ln -s /etc/nginx/sites-available/example.com /etc/nginx/sites-enabled/
   ```

6. Test Nginx configuration:
   ```
   sudo nginx -t
   ```

7. Restart Nginx:
   ```
   sudo systemctl restart nginx
   ```

## Step 9: Configure DNS Records

Set up your DNS records to point to your server:

1. Create an A record for your main domain (`example.com`) pointing to your server IP.
2. Create a CNAME record for the CRM subdomain (`crm.example.com`) pointing to your main domain.

Wait for DNS propagation (can take from a few minutes to 24 hours).

## Step 10: Configure Firewall (Optional)

1. Allow Nginx through the firewall:
   ```
   sudo ufw allow 'Nginx Full'
   sudo ufw enable
   ```

## Step 11: Set Up SSL (Optional but Recommended)

1. Install Certbot:
   ```
   sudo apt install -y certbot python3-certbot-nginx
   ```

2. Obtain SSL certificates for both domains:
   ```
   sudo certbot --nginx -d example.com -d www.example.com
   sudo certbot --nginx -d crm.example.com
   ```

3. Follow the prompts to complete the SSL setup.

## Step 12: Test Your Deployment

1. Visit your websites in a browser:
   ```
   http://example.com        # Client portal 
   http://crm.example.com    # Admin/agent CRM
   ```

2. Check for any errors in the logs:
   ```
   sudo journalctl -u omcrm.service
   sudo tail -f /var/log/nginx/error.log
   ```

## Local Development Login

When running the application locally with `python manage.py run`, the application will run on `http://127.0.0.1:5000`. In this local environment, you can:

1. Access the admin/agent login directly at:
   ```
   http://127.0.0.1:5000/admin_login
   ```
   This special route bypasses domain checking for local development.

2. Access the client login at:
   ```
   http://127.0.0.1:5000/client/login
   ```
   
3. Regular `/login` route will redirect to the client login on localhost.

**Note:** The application now includes special handling for localhost that disables domain-based routing for easier local development.

### Simulating Domains Locally (Optional)

To test the domain separation locally, you can modify your hosts file:

1. Edit your hosts file:
   - Windows: `C:\Windows\System32\drivers\etc\hosts`
   - macOS/Linux: `/etc/hosts`

2. Add these entries:
   ```
   127.0.0.1    example.local
   127.0.0.1    crm.example.local
   ```

3. Run the application and access:
   - `http://example.local:5000` - For client access
   - `http://crm.example.local:5000` - For admin/agent access

## Troubleshooting

- **Application not loading**: Check Gunicorn logs using `sudo journalctl -u omcrm.service`
- **Static files not loading**: Verify Nginx configuration and file permissions
- **Database connection issues**: Ensure PostgreSQL is running and credentials are correct
- **Permission errors**: Check file ownership and permissions
- **Domain routing issues**: Check that your Nginx configuration is correctly set up for both domains

## Maintenance

- **Updating the application**:
  ```
  cd /var/www/omcrm
  git pull
  source venv/bin/activate
  pip install -r requirements.txt
  flask db upgrade  # if there are database changes
  sudo systemctl restart omcrm  # restart the application
  ```

- **Backing up the database**:
  ```
  pg_dump -U omuser omcrm > omcrm_backup_$(date +%Y%m%d).sql
  ```

## Security Considerations

- Keep your system and packages updated
- Use strong passwords for all services
- Configure a firewall to limit access
- Set up fail2ban to prevent brute force attacks
- Regularly back up your database and configuration 

# Docker Deployment Guide

This guide provides instructions for deploying the application using Docker and docker-compose.

## Prerequisites

- Docker installed on your server
- Docker Compose installed on your server
- Access to your server via SSH or terminal

## Deployment Steps

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd letstrythis
```

### 2. Configuration

Edit the `.env` file to set your production environment variables:

```
FLASK_APP=run.py
FLASK_ENV=production
FLASK_DEBUG=0  # Set to 0 in production
SECRET_KEY=<your-secure-random-key>
DATABASE_URI=sqlite:///instance/site.db
ALPHA_VANTAGE_API_KEY=<your-api-key>
```

For security in production, make sure to:
- Generate a strong SECRET_KEY
- Set FLASK_DEBUG=0
- Provide actual API keys

### 3. Build and Start the Docker Containers

```bash
docker-compose up -d --build
```

This command will:
- Build the Docker image for your Flask application
- Start the Flask application container
- Start the Nginx container as a reverse proxy

### 4. Verify the Deployment

Your application should now be running at:
- http://your-server-ip

To check container logs:
```bash
# For the Flask app
docker logs letstrythis_app

# For Nginx
docker logs letstrythis_nginx
```

### 5. Managing the Application

#### Stopping the containers
```bash
docker-compose down
```

#### Restarting the containers
```bash
docker-compose restart
```

#### Viewing logs
```bash
docker-compose logs
```

#### Updating the application
```bash
git pull  # Pull latest changes
docker-compose up -d --build  # Rebuild and restart containers
```

## Nginx Configuration

The Nginx configuration is in `nginx/app.conf`. 

If you need to use HTTPS:
1. Uncomment the HTTPS section in the config
2. Add your SSL certificates to the appropriate location
3. Restart the nginx container

## Database Backup

To backup the SQLite database:

```bash
docker exec letstrythis_app bash -c "sqlite3 /app/instance/site.db .dump > /app/backup/backup_\$(date +%Y%m%d_%H%M%S).sql"
```

## Troubleshooting

### Container fails to start
Check the logs:
```bash
docker logs letstrythis_app
```

### Nginx returns 502 Bad Gateway
Ensure the Flask application is running:
```bash
docker ps  # Check if letstrythis_app is running
```

### Static files not loading
Verify volume mounts:
```bash
docker inspect letstrythis_nginx  # Check Mounts section
```

## Security Considerations

For a production deployment:

1. Set `FLASK_DEBUG=0` in the `.env` file
2. Use HTTPS (enable the commented section in nginx config)
3. Use a strong, unique SECRET_KEY
4. Consider using environment-specific secrets management
5. Regularly update dependencies and the base Docker images
