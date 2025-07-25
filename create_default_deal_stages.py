#!/usr/bin/env python3
"""
Database Setup: Create Default Deal Stages
Ensure "In Progress" and other essential deal stages exist
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from omcrm.deals.models import DealStage

def create_default_deal_stages():
    """Create default deal stages if they don't exist"""
    app = create_app()
    
    with app.app_context():
        try:
            # List of default stages to create
            default_stages = [
                {'stage_name': 'In Progress', 'display_order': 1, 'close_type': None},
                {'stage_name': 'Qualified', 'display_order': 2, 'close_type': None},
                {'stage_name': 'Proposal', 'display_order': 3, 'close_type': None},
                {'stage_name': 'Negotiation', 'display_order': 4, 'close_type': None},
                {'stage_name': 'Deal Won', 'display_order': 5, 'close_type': 'won'},
                {'stage_name': 'Deal Lost', 'display_order': 6, 'close_type': 'lost'},
            ]
            
            stages_created = 0
            
            for stage_data in default_stages:
                # Check if stage already exists
                existing_stage = DealStage.query.filter_by(stage_name=stage_data['stage_name']).first()
                
                if not existing_stage:
                    new_stage = DealStage(
                        stage_name=stage_data['stage_name'],
                        display_order=stage_data['display_order'],
                        close_type=stage_data['close_type']
                    )
                    db.session.add(new_stage)
                    stages_created += 1
                    print(f"Created stage: {stage_data['stage_name']}")
                else:
                    print(f"Stage already exists: {stage_data['stage_name']}")
            
            # Commit all changes
            db.session.commit()
            
            if stages_created > 0:
                print(f"✅ Created {stages_created} new deal stages!")
            else:
                print("✅ All default deal stages already exist!")
                
            print("🔧 Deal creation will now default to 'In Progress' stage.")
            
        except Exception as e:
            print(f"❌ Error creating deal stages: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    create_default_deal_stages() 