# OMCRM - Trading CRM System

OMCRM is a CRM system designed for managing leads, clients, and trading operations. The system includes both an admin/agent interface and a client-facing WebTrader platform.

## Features

- Lead management with conversion to clients
- Integrated WebTrader platform for clients
- Transaction management (deposits/withdrawals)
- Team-based permissions and role-based access control
- API for external lead imports
- Trading simulation with dynamic charts

## Local Development

1. Clone the repository:
   ```
   git clone https://github.com/your-username/omcrm.git
   cd omcrm
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```
   flask db upgrade
   ```

4. Run the application:
   ```
   python manage.py run
   ```

5. Access the application at `http://127.0.0.1:5000`

## Deployment

### GitHub-based Deployment

1. Push your changes to GitHub:
   ```
   git add .
   git commit -m "Your commit message"
   git push
   ```

2. On your server, clone the repository:
   ```
   git clone https://github.com/your-username/omcrm.git /var/www/omcrm
   ```

3. Follow the deployment steps in `deployment_steps.md`

### Using the Deployment Script

1. Run the deployment script:
   ```
   python deploy.py user@your-server-ip
   ```

2. The script will:
   - Create a deployment package (omcrm_deploy.tar.gz)
   - Upload it to your server
   - Provide instructions for completing the deployment

3. Complete the deployment by following the steps provided by the script

## Project Structure

- `omcrm/` - Main application package
  - `api/` - API routes and functionality
  - `client/` - Client-facing routes and templates
  - `deals/` - Deal management 
  - `leads/` - Lead management
  - `rbac/` - Role-based access control
  - `settings/` - Application settings
  - `transactions/` - Financial transactions
  - `users/` - User management
  - `webtrader/` - Trading platform
- `migrations/` - Database migration scripts
- `manage.py` - Management script
- `wsgi.py` - WSGI entry point for production
- `deployment_steps.md` - Deployment guide

## License

This project is for demonstration purposes only.

## Support

For support, please contact the system administrator.

# OMCRM

A full-featured Customer Relationship Management system built with 
Flask, Python as well as other tools that are required to build a stable and asynchronous web application.

![alt text](https://i.ibb.co/BsWm9Kf/omcrm-demo1.gif)

## Instructions to run the app

Below is the list that contains both database-level and module-level instructions.

OMCRM contains the following modules (along with the
percentage of completion):

- Dashboard page with sales reports. (completed)
- Leads management module. (completed)
- Clients management module. (completed)
- Accounts management module. (completed)
- Contacts management module. (completed)
- Tasks management module. (completed)
- Deals management. (completed)
- User and role-based system. (completed)
- User teams management. (completed)
- System settings (e.g. update email SMTP). (completed)
- Data export / import. (completed)
- Installation system. (completed)
- WebTrader integration for client trading accounts. (completed)

Additional features that need to be implemented:

- Multiple language support.
- Advanced search with saved searches.
- Kanban view for tasks, leads, deals.
- Gmail / Outlook sync.
- Document management with versioning.
- Lead / Client activity history.
- Calendar view.
- Mobile apps.
- Telegram integration.
- SMS tool.
- Live chat functionality.

## Installation and Configuration

To install and configure OMCRM on your system:

1. Clone the repository:

```
git clone https://github.com/yourusername/OMCRM.git
```

2. Create a virtual environment (Linux/macOS):

```
virtualenv -p python3 omcrm
source omcrm/bin/activate
```

Or on Windows:
```
python -m venv venv
.\venv\Scripts\activate
```

3. Navigate to the application directory:
```
cd omcrm
```

4. Install the required packages:
```
pip install -r requirements.txt
```

5. Initialize the database:
```
flask db init
flask db migrate
flask db upgrade
```

6. Run the application:
```
python run.py
```

7. Navigate to http://localhost:5000 in your browser.

## System Requirements

- Python 3.6+
- Flask 2.0+
- SQLAlchemy 1.4+
- PostgreSQL (recommended for production) or SQLite (for development)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Screenshots

![Dashboard](https://example.com/dashboard.png)
![Leads](https://example.com/leads.png)
![Deals](https://example.com/deals.png)
![WebTrader](https://example.com/webtrader.png)



