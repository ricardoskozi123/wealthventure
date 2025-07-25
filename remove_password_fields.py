#!/usr/bin/env python3
"""
Database Migration: Remove Unnecessary Password Fields
Remove _admin_password and plain_password columns from Lead table
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from sqlalchemy import text

def remove_password_fields():
    """Remove unnecessary password fields from Lead table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns exist and remove them
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('lead')]
            
            removed_count = 0
            
            if '_admin_password' in columns:
                print("Removing _admin_password column...")
                db.session.execute(text('ALTER TABLE lead DROP COLUMN _admin_password'))
                removed_count += 1
            
            if 'plain_password' in columns:
                print("Removing plain_password column...")
                db.session.execute(text('ALTER TABLE lead DROP COLUMN plain_password'))
                removed_count += 1
            
            # Commit the schema changes
            db.session.commit()
            
            if removed_count > 0:
                print(f"✅ Removed {removed_count} unnecessary password field(s)!")
            else:
                print("✅ No unnecessary password fields found to remove.")
                
            print("🔧 Password system simplified - only secure hashed passwords remain.")
            
        except Exception as e:
            print(f"❌ Error removing password fields: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    remove_password_fields() 