#!/usr/bin/env python3
"""
Database Migration: Add Manager Permissions
Add can_view_all_clients and can_view_all_leads columns to Resource table
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from omcrm.users.models import Resource
from sqlalchemy import text

def add_manager_permissions():
    """Add manager permission columns to Resource table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('resource')]
            
            if 'can_view_all_clients' not in columns:
                print("Adding can_view_all_clients column...")
                # Use text() wrapper for raw SQL and session.execute()
                db.session.execute(text('ALTER TABLE resource ADD COLUMN can_view_all_clients BOOLEAN DEFAULT FALSE NOT NULL'))
                
            if 'can_view_all_leads' not in columns:
                print("Adding can_view_all_leads column...")
                # Use text() wrapper for raw SQL and session.execute()
                db.session.execute(text('ALTER TABLE resource ADD COLUMN can_view_all_leads BOOLEAN DEFAULT FALSE NOT NULL'))
            
            # Commit the schema changes
            db.session.commit()
            
            # Update existing resources to have these permissions set to False by default
            resources = Resource.query.all()
            for resource in resources:
                if not hasattr(resource, 'can_view_all_clients'):
                    resource.can_view_all_clients = False
                if not hasattr(resource, 'can_view_all_leads'):
                    resource.can_view_all_leads = False
            
            db.session.commit()
            print("✅ Manager permissions added successfully!")
            print("🔧 You can now assign 'View All Clients' and 'View All Leads' permissions to manager roles.")
            
        except Exception as e:
            print(f"❌ Error adding manager permissions: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    add_manager_permissions() 