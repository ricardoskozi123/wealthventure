#!/usr/bin/env python3
"""
Database Migration: Add Plain Password Field
Add plain_password column to Lead table for business requirements
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from sqlalchemy import text

def add_plain_password_field():
    """Add plain_password column to Lead table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('lead')]
            
            if 'plain_password' not in columns:
                print("Adding plain_password column...")
                db.session.execute(text('ALTER TABLE lead ADD COLUMN plain_password VARCHAR(100)'))
            
            # Commit the schema changes
            db.session.commit()
            
            print("✅ Plain password field added successfully!")
            print("🔧 Passwords will now be stored as plain text for business use.")
            
        except Exception as e:
            print(f"❌ Error adding plain password field: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    add_plain_password_field() 