#!/usr/bin/env python3
"""
Database Migration: Add Admin Password Field
Add _admin_password column to Lead table for admin-viewable passwords
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from sqlalchemy import text

def add_admin_password_field():
    """Add _admin_password column to Lead table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('lead')]
            
            if '_admin_password' not in columns:
                print("Adding _admin_password column...")
                db.session.execute(text('ALTER TABLE lead ADD COLUMN _admin_password VARCHAR(200)'))
            
            # Commit the schema changes
            db.session.commit()
            
            print("✅ Admin password field added successfully!")
            print("🔧 Passwords can now be viewed by admins after reset.")
            
        except Exception as e:
            print(f"❌ Error adding admin password field: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    add_admin_password_field() 