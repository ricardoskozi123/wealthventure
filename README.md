# 💰 Wealth Venture - Professional Trading Platform

A comprehensive trading and wealth management platform built with Flask, featuring real-time market data, portfolio management, client relationship management (CRM), and advanced trading tools.

## 🌟 Features

### Trading Platform
- **Real-time Market Data**: Live price feeds for stocks, crypto, forex
- **Advanced Charting**: Professional trading charts with technical indicators
- **Portfolio Management**: Track investments, profits, and performance
- **Trade Execution**: Simulated trading environment with real market data
- **Risk Management**: Stop-loss, take-profit, and position sizing tools

### Client Management (CRM)
- **Lead Management**: Track prospects and convert to clients
- **Deal Pipeline**: Manage investment opportunities and deals
- **Client Dashboard**: Dedicated client portal with trading access
- **Activity Tracking**: Log all client interactions and communications
- **Task Management**: Assign and track follow-up tasks

### Admin Features
- **User Management**: Role-based access control (Admin, Agent, Client)
- **Reporting**: Comprehensive analytics and performance reports
- **Settings Management**: Platform configuration and customization
- **Activity Logs**: Audit trail for all platform activities
- **Multi-domain Support**: Separate admin and client domains

### Security
- **IP Whitelisting**: Restrict admin access to authorized IPs
- **Role-based Permissions**: Granular access control
- **Secure Authentication**: Password hashing and session management
- **CSRF Protection**: Cross-site request forgery prevention

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- SQLite (default) or PostgreSQL
- Modern web browser

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/wealth-venture.git
   cd wealth-venture
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.template .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   python manage.py db upgrade
   python run_setup.py  # Creates sample data
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

7. **Access the platform**
   - Main site: http://localhost:5000
   - Admin login: http://localhost:5000/login
   - Client login: http://localhost:5000/client/login

## 📁 Project Structure

```
wealth-venture/
├── omcrm/                 # Main application package
│   ├── templates/         # HTML templates
│   ├── static/           # CSS, JS, images
│   ├── users/            # User management
│   ├── leads/            # Lead/client management
│   ├── deals/            # Deal pipeline
│   ├── webtrader/        # Trading platform
│   ├── activities/       # Activity tracking
│   ├── tasks/            # Task management
│   └── main/             # Main routes
├── migrations/           # Database migrations
├── scripts/             # Deployment scripts
├── nginx/               # Nginx configurations
├── requirements.txt     # Python dependencies
├── run.py              # Application entry point
└── config.py           # Configuration settings
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Platform Settings
PLATFORM_NAME=Wealth Venture
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite:///dev.db

# Domains (for multi-domain setup)
CLIENT_DOMAIN=wealth-venture.com
CRM_SUBDOMAIN=crm.wealth-venture.com

# Email (optional)
MAIL_SERVER=smtp.example.com
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password

# API Keys (optional)
ALPHA_VANTAGE_API_KEY=your-api-key
```

## 🐳 Docker Deployment

### Quick Docker Setup

```bash
# Build and run with Docker Compose
docker-compose up -d

# The platform will be available at:
# - Main site: http://localhost
# - Admin: http://localhost/login
```

### Production Deployment

For production deployment with SSL and custom domains:

```bash
# Configure domains in deploy_with_domains.sh
./deploy_with_domains.sh
```

## 👥 Default Users

After running the setup, default users are created:

- **Admin**: admin@example.com / password123
- **Agent**: agent@example.com / password123
- **Client**: client@example.com / password123

⚠️ **Important**: Change these passwords in production!

## 🎨 Customization

### Branding
- Update `PLATFORM_NAME` in environment variables
- Modify templates in `omcrm/templates/`
- Update CSS in `omcrm/static/css/`

### Features
- Add new modules in `omcrm/`
- Create database migrations with Flask-Migrate
- Extend the API in `omcrm/api/`

## 📊 Trading Features

### Market Data
- Real-time price feeds
- Historical data analysis
- Multiple asset classes (stocks, crypto, forex)
- Technical indicators

### Portfolio Management
- Position tracking
- P&L calculations
- Performance analytics
- Risk metrics

### Client Portal
- Personal trading dashboard
- Account statements
- Trade history
- Market research

## 🔐 Security Features

### Access Control
- Role-based permissions (RBAC)
- IP whitelisting for admin access
- Session management
- CSRF protection

### Data Protection
- Password hashing
- Secure session cookies
- SQL injection prevention
- XSS protection

## 📈 Analytics & Reporting

### Admin Reports
- User activity analytics
- Trading performance metrics
- Revenue tracking
- Lead conversion rates

### Client Reports
- Portfolio performance
- Trade history
- Account statements
- Tax reporting

## 🛠️ Development

### Running Tests
```bash
python -m pytest tests/
```

### Database Migrations
```bash
# Create new migration
python manage.py db migrate -m "Description"

# Apply migrations
python manage.py db upgrade
```

### Adding New Features
1. Create new module in `omcrm/`
2. Add routes and templates
3. Update database models
4. Create migration
5. Add tests

## 📝 API Documentation

The platform includes a REST API for external integrations:

- `/api/leads` - Lead management
- `/api/deals` - Deal pipeline
- `/api/activities` - Activity tracking
- `/api/users` - User management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation in `/docs`
- Review the deployment guides

## 🚀 Roadmap

### Upcoming Features
- Mobile app (React Native)
- Advanced algorithmic trading
- Social trading features
- Cryptocurrency staking
- DeFi integrations
- AI-powered market analysis

---

**Wealth Venture** - Empowering your financial future through technology.