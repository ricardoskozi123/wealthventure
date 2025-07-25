#!/usr/bin/env python3
"""
Database Migration: Add Juhu Column
Add 'juhu' column to Lead table for plain text password storage with obscure naming
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from sqlalchemy import text

def add_juhu_column():
    """Add 'juhu' column to Lead table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('lead')]
            
            if 'juhu' not in columns:
                print("Adding 'juhu' column...")
                db.session.execute(text('ALTER TABLE lead ADD COLUMN juhu VARCHAR(100)'))
            else:
                print("'juhu' column already exists.")
            
            # Commit the schema changes
            db.session.commit()
            
            print("✅ 'juhu' column added successfully!")
            print("🔧 Passwords will now be stored in the obscure 'juhu' column for business viewing.")
            print("🔐 Login authentication still uses secure bcrypt hashing.")
            
        except Exception as e:
            print(f"❌ Error adding 'juhu' column: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    add_juhu_column() 