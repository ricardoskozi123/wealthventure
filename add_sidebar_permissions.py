#!/usr/bin/env python3
"""
Database Migration: Add Sidebar Navigation Permissions
Add comprehensive sidebar navigation permission columns to Resource table
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from sqlalchemy import text

def add_sidebar_permissions():
    """Add sidebar navigation permission columns to Resource table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check which columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('resource')]
            
            # List of new sidebar permission columns
            sidebar_permissions = [
                ('can_view_dashboard', 'TRUE'),
                ('can_view_leads', 'TRUE'),
                ('can_view_pipeline', 'TRUE'),
                ('can_view_activities', 'TRUE'),
                ('can_view_tasks', 'TRUE'),
                ('can_view_lead_sources', 'FALSE'),
                ('can_view_client_statuses', 'FALSE'),
                ('can_view_trading_instruments', 'FALSE'),
                ('can_view_clients_page', 'TRUE'),
                ('can_view_reports', 'TRUE'),
                ('can_view_pipeline_stages', 'FALSE'),
                ('can_view_transactions', 'FALSE'),
                ('can_view_settings', 'TRUE')
            ]
            
            # Add missing columns
            for column_name, default_value in sidebar_permissions:
                if column_name not in columns:
                    print(f"Adding {column_name} column...")
                    db.session.execute(text(f'ALTER TABLE resource ADD COLUMN {column_name} BOOLEAN DEFAULT {default_value} NOT NULL'))
                else:
                    print(f"{column_name} column already exists.")
            
            # Commit the schema changes
            db.session.commit()
            
            print("✅ All sidebar permission columns added successfully!")
            print("🎯 Sidebar navigation now has comprehensive permission control:")
            print("   - Dashboard, Leads, Pipeline, Activities, Tasks")
            print("   - Lead Sources, Client Statuses, Trading Instruments")
            print("   - Clients, Reports, Pipeline Stages")
            print("   - Transactions, Settings")
            print("")
            print("🔧 Admin users will see all items by default.")
            print("📋 Configure permissions in Settings > User Roles & Permissions")
            
        except Exception as e:
            print(f"❌ Error adding sidebar permission columns: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    add_sidebar_permissions() 