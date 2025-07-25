#!/usr/bin/env python3
"""
Database Migration: Add Lead Attribution Fields
Add funnel_name and affiliate_id columns to Lead table for better tracking
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from sqlalchemy import text

def add_lead_attribution_fields():
    """Add funnel_name and affiliate_id columns to Lead table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('lead')]
            
            if 'funnel_name' not in columns:
                print("Adding funnel_name column...")
                db.session.execute(text('ALTER TABLE lead ADD COLUMN funnel_name VARCHAR(100)'))
                
            if 'affiliate_id' not in columns:
                print("Adding affiliate_id column...")
                db.session.execute(text('ALTER TABLE lead ADD COLUMN affiliate_id VARCHAR(100)'))
            
            # Commit the schema changes
            db.session.commit()
            
            print("✅ Lead attribution fields added successfully!")
            print("🔧 You can now track funnel_name and affiliate_id for leads.")
            
        except Exception as e:
            print(f"❌ Error adding lead attribution fields: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    add_lead_attribution_fields() 