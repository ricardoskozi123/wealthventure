from flask import Flask, render_template, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
import os
from datetime import datetime
from werkzeug.exceptions import HTTPException
from sqlalchemy import MetaData
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

from .config import DevelopmentConfig, TestConfig, ProductionConfig
from .csrf import init_csrf

# Create instances
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)

# encryptor handle
bcrypt = Bcrypt()

migrate = Migrate()
# manage user login
login_manager = LoginManager()

# Initialize Socket.IO
socketio = SocketIO()

# function name of the login route that
# tells the path which facilitates authentication
login_manager.login_view = 'users.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Custom login redirection based on request
def unauthorized_handler():
    from flask import request, render_template
    return render_template('errors/401.html'), 401

def run_install(app_ctx):
    from omcrm.install.routes import install
    app_ctx.register_blueprint(install)
    return app_ctx

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__, instance_relative_config=True)

    if os.getenv('FLASK_ENV') == 'development':
        config_obj = DevelopmentConfig()
    elif os.getenv('FLASK_ENV') == 'production':
        config_obj = ProductionConfig()
        # Ensure debug is turned off in production
        app.debug = False 
        app.testing = False
    elif os.getenv('FLASK_ENV') == 'testing':
        config_obj = TestConfig()
    else:
        # Default to development config if no environment is specified
        config_obj = config_class()

    app.config.from_object(config_obj)
    app.url_map.strict_slashes = False
    app.jinja_env.globals.update(zip=zip)

    migrate.init_app(app, db)
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    # Initialize Socket.IO with the app (only if not disabled)
    if not os.getenv('DISABLE_SOCKETIO'):
        socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    else:
        print("⚠️  Socket.IO disabled - running in simplified mode")
    
    # Set the custom unauthorized handler
    login_manager.unauthorized_handler(unauthorized_handler)
    init_csrf(app)  # Initialize CSRF protection

    # custom template filters
    from omcrm.common.filters import timeago
    app.jinja_env.filters['timeago'] = timeago

    with app.app_context():
        try:
           # # Ensure database directory exists
            #db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
           # if db_path and not os.path.exists(os.path.dirname(db_path)) and os.path.dirname(db_path):
           #     os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Create all tables first
            db.create_all()
            
            # check if the config table exists, otherwise run install
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if not inspector.has_table('app_config'):
                return run_install(app)
            else:
                from omcrm.settings.models import AppConfig
                row = AppConfig.query.first()
                if not row:
                    print("No AppConfig found - running installation...")
                    return run_install(app)
        except Exception as e:
            print(f"Database initialization error: {e}")
            print("Running installation...")
            return run_install(app)

        # application is installed so extends the config
        from omcrm.settings.models import AppConfig, Currency, TimeZone
        app_cfg = AppConfig.query.first()
        app.config['def_currency'] = Currency.get_currency_by_id(app_cfg.default_currency)
        app.config['def_tz'] = TimeZone.get_tz_by_id(app_cfg.default_timezone)

        # Import all models to ensure they are registered with SQLAlchemy
        # Order is important to avoid circular imports
        from omcrm.users.models import User, Team, Role, Resource
        from omcrm.leads.models import Lead, LeadSource, LeadStatus, Comment
        # from omcrm.accounts.models import Account - Removed
        # from omcrm.contacts.models import Contact - Removed
        from omcrm.deals.models import Deal, DealStage
        from omcrm.tasks.models import Task, TaskStatus, TaskPriority
        from omcrm.settings.models import Currency, TimeZone
        from omcrm.webtrader.models import TradingInstrument, Trade
        from omcrm.activities.models import Activity

        # Create the database tables and perform automatic migrations
        db.create_all()
        
        # Check if TradingInstrument table exists but last_updated column doesn't
        inspector = db.inspect(db.engine)
        if 'trading_instrument' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('trading_instrument')]
            if 'last_updated' not in columns:
                # Add the column
                db.engine.execute('ALTER TABLE trading_instrument ADD COLUMN last_updated DATETIME')
                
                # Update existing instruments with current timestamp
                now = datetime.utcnow()
                instruments = TradingInstrument.query.all()
                for instrument in instruments:
                    instrument.last_updated = now
                db.session.commit()
                app.logger.info("Added last_updated column to TradingInstrument table")

        # Check and handle different domains/subdomains
        @app.before_request
        def handle_domains():
            from flask import request, redirect, url_for
            
            # Extract the domain/host from the request
            host = request.host.lower()
            
            # Skip for static file requests and special admin login route
            if request.path.startswith('/static/') or request.path == '/admin_login':
                return None
                
            # For local development (localhost/127.0.0.1)
            if host == '127.0.0.1:5000' or host == 'localhost:5000':
                # Special case to allow local development without domain routing
                return None
                
            # If accessing the CRM subdomain (crm.example.com)
            if host.startswith('crm.'):
                # If trying to access client routes from CRM subdomain, redirect to main site
                if request.path.startswith('/client/') and not request.path.startswith('/client/login'):
                    # Extract the main domain (remove 'crm.' prefix)
                    main_domain = host[4:]  # Skip 'crm.'
                    # Only redirect if this isn't a local development environment
                    if main_domain not in ['127.0.0.1:5000', 'localhost:5000']:
                        return redirect(f"http://{main_domain}{request.path}")
                    
                # If accessing client login from CRM subdomain, redirect to admin login
                if request.path == '/client/login':
                    return redirect(url_for('users.login'))
            
            # If accessing the main domain (example.com)
            elif not host.startswith('crm.'):
                # If trying to access admin routes, redirect to CRM subdomain
                if (request.path == '/login' or
                    request.path.startswith('/users/') or
                    request.path.startswith('/leads/') or
                    request.path.startswith('/deals/') or
                    request.path.startswith('/settings/') or
                    request.path.startswith('/reports/') or
                    request.path == '/'):
                    
                    # If not explicitly trying to access client login, redirect to client login
                    if request.path == '/login':
                        return redirect(url_for('users.client_login'))
                    
                    # Only redirect to CRM subdomain if not in local development
                    if host not in ['127.0.0.1:5000', 'localhost:5000']:
                        return redirect(f"http://crm.{host}{request.path}")
            
            # For all other cases, proceed normally
            return None

        # include the routes
        from omcrm.main.routes import main
        from omcrm.users.routes import users
        from omcrm.leads.routes import leads
        from omcrm.deals.routes import deals
        from omcrm.settings.routes import settings
        from omcrm.settings.app_routes import app_config
        from omcrm.reports.routes import reports
        from omcrm.webtrader.routes import webtrader
        from omcrm.client.routes import client
        from omcrm.tasks import tasks
        from omcrm.transactions.routes import transactions
        from omcrm.api.routes import api
        from omcrm.activities.routes import activities
        from omcrm.comments import comments
        # register routes with blueprint

        app.register_blueprint(main)
        app.register_blueprint(users)
        app.register_blueprint(settings)
        app.register_blueprint(app_config)
        app.register_blueprint(leads)
        app.register_blueprint(deals)
        app.register_blueprint(reports)
        app.register_blueprint(webtrader, url_prefix='/webtrader')
        app.register_blueprint(client)
        app.register_blueprint(tasks)
        app.register_blueprint(transactions)
        app.register_blueprint(api)
        app.register_blueprint(activities)
        app.register_blueprint(comments)

        # Add a context processor to provide common variables to all templates
        @app.context_processor
        def inject_now():
            from datetime import datetime
            return {'now': datetime.utcnow()}

      #  # Register error handlers
        @app.errorhandler(404)
        def page_not_found(e):
            return render_template('errors/404.html'), 404

        @app.errorhandler(403)
        def forbidden(e):
            return render_template('errors/403.html'), 403

        @app.errorhandler(500)
        def internal_server_error(e):
            return render_template('errors/500.html'), 500
      
        # Handler for unauthorized access (when not logged in)
        @app.errorhandler(401)
        def unauthorized(e):
            return render_template('errors/401.html'), 401

      #  # Catch AttributeError exceptions caused by user type mismatches
        @app.errorhandler(AttributeError)
        def handle_attribute_error(e):
            # Return 500 error page for attribute errors
            return render_template('errors/500.html'), 500
      
      #  # Handler for all HTTP exceptions
        @app.errorhandler(Exception)
        def handle_exception(e):
            # Pass through HTTP errors
            if isinstance(e, HTTPException):
                code = e.code
                if code == 404:
                    return render_template('errors/404.html'), 404
                elif code == 403:
                    return render_template('errors/403.html'), 403
                elif code == 401:
                    return render_template('errors/401.html'), 401
                else:
                    return render_template('errors/500.html'), 500
            else:
                # For non-HTTP exceptions, return 500 error
                app.logger.error(f"Unhandled exception: {str(e)}")
                return render_template('errors/500.html'), 500
            
        # Catch-all route handler as the last route to handle any unmatched routes
        @app.route('/<path:path>')
        def catch_all(path):
            # Always return 404 without any additional information
            return render_template('errors/404.html'), 404

    return app
