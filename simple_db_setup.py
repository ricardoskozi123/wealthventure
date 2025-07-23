import os
import sys
import sqlite3
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Define database path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'site.db')

# Create the db file
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)
conn.close()
print(f"Created empty database at {DB_PATH}")

# Create a simple Flask app with SQLite
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Import all models
from omcrm.tasks.models import Task, TaskComment
from omcrm.users.models import User, Team, Role, Resource
from omcrm.leads.models import Lead, LeadSource, LeadStatus, Comment
from omcrm.deals.models import Deal, DealStage
from omcrm.settings.models import AppConfig, Currency, TimeZone
from omcrm.webtrader.models import TradingInstrument, Trade
from omcrm.activities.models import Activity

# Create tables
with app.app_context():
    db.create_all()
    print("Created all database tables successfully!")
    
    # Create default app config if it doesn't exist
    from omcrm.settings.models import AppConfig
    if not AppConfig.query.first():
        default_config = AppConfig(
            app_name='OpenCRM',
            default_currency=1,  # USD
            default_timezone=1,  # UTC
            created_on=datetime.utcnow()
        )
        db.session.add(default_config)
        db.session.commit()
        print("Created default app configuration")
    
print("Database setup complete!") 