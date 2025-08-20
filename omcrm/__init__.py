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
    
    # Import and add RBAC functions to Jinja2 global namespace
    from omcrm.rbac import is_allowed, can_view_sidebar_item
    app.jinja_env.globals.update(is_allowed=is_allowed)
    app.jinja_env.globals.update(can_view_sidebar_item=can_view_sidebar_item)

    migrate.init_app(app, db)
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    # Initialize domain routing for production
    if os.getenv('FLASK_ENV') == 'production':
        from omcrm.domain_router import DomainRouter
        domain_router = DomainRouter(app)
    
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
            # Load all models to ensure they're registered with SQLAlchemy
            from omcrm.users.models import User, Role, Resource, Team
            from omcrm.leads.models import Lead, LeadSource, LeadStatus
            from omcrm.deals.models import Deal, DealStage, Product
            from omcrm.tasks.models import Task
            from omcrm.settings.models import AppConfig
            from omcrm.activities.models import Activity, ActivityType
            from omcrm.webtrader.models import TradingInstrument, InstrumentPrice
            from omcrm.transactions.models import Transaction
            from omcrm.comments.models import Comment
            
            # Create all tables
            db.create_all()
            
            # Check if we need to run the initial setup
            app_config = AppConfig.query.first()
            if not app_config:
                # No app config found, run the installer
                print("No app configuration found. Please run the installer first.")
                print("Visit: http://your-domain/install")
                return run_install(app)
            
            # Check if there are any users
            user_count = User.query.count()
            if user_count == 0:
                print("No users found. Please run the installer first.")
                print("Visit: http://your-domain/install")
                return run_install(app)
            
            print(f"✅ Database initialized successfully with {user_count} users")
            
        except Exception as e:
            print(f"❌ Database initialization error: {str(e)}")
            print("Running installer to fix database issues...")
            return run_install(app)

        @app.route('/clear_session')
        def clear_session():
            from flask import session
            session.clear()
            return redirect(url_for('main.home'))

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

        # ERROR HANDLERS DISABLED FOR DEBUGGING - ENABLE AFTER FIXING ISSUES
        # @app.errorhandler(404)
        # def page_not_found(e):
        #     return render_template('errors/404.html'), 404

        # @app.errorhandler(403)
        # def forbidden(e):
        #     return render_template('errors/403.html'), 403

        # @app.errorhandler(500)
        # def internal_server_error(e):
        #     return render_template('errors/500.html'), 500
      
        # # Handler for unauthorized access (when not logged in)
        # @app.errorhandler(401)
        # def unauthorized(e):
        #     return render_template('errors/401.html'), 401

        # # Catch AttributeError exceptions caused by user type mismatches
        # @app.errorhandler(AttributeError)
        # def handle_attribute_error(e):
        #     # Return 500 error page for attribute errors
        #     return render_template('errors/500.html'), 500
      
        # # Handler for all HTTP exceptions
        # @app.errorhandler(Exception)
        # def handle_exception(e):
        #     # Pass through HTTP errors
        #     if isinstance(e, HTTPException):
        #         code = e.code
        #         if code == 404:
        #             return render_template('errors/404.html'), 404
        #         elif code == 403:
        #             return render_template('errors/403.html'), 403
        #         elif code == 401:
        #             return render_template('errors/401.html'), 401
        #         else:
        #             return render_template('errors/500.html'), 500
        #     else:
        #         # For non-HTTP exceptions, return 500 error
        #         app.logger.error(f"Unhandled exception: {str(e)}")
        #         return render_template('errors/500.html'), 500
            
        # CATCH-ALL ROUTE DISABLED FOR DEBUGGING - ENABLE AFTER FIXING ISSUES
        # @app.route('/<path:path>')
        # def catch_all(path):
        #     # Always return 404 without any additional information
        #     return render_template('errors/404.html'), 404

    return app
