from flask import Flask
from flask_migrate import Migrate, stamp
from omcrm import db, create_app

app = create_app()
migrate = Migrate(app, db)

with app.app_context():
    # Mark the migration as complete (at the head revision)
    stamp('head')
    print("Migration marked as complete at 'head' revision") 