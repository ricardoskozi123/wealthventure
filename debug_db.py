import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Print environment variables
print("FLASK_ENV:", os.environ.get('FLASK_ENV'))
print("SQLALCHEMY_DATABASE_URI:", os.environ.get('SQLALCHEMY_DATABASE_URI'))

# Create a minimal app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@db:5432/omcrm')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Test the database connection
with app.app_context():
    try:
        result = db.engine.execute("SELECT 1")
        print("Database connection successful:", list(result)[0][0])
    except Exception as e:
        print("Database connection failed:", str(e)) 