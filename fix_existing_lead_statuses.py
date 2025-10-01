#!/usr/bin/env python3
"""
Fix Existing Lead Statuses
This script helps migrate existing leads that have a default status to "No Status" (NULL)
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from omcrm.leads.models import Lead, LeadStatus

def fix_lead_statuses():
    """Fix existing leads that have default status"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get all lead statuses ordered by ID (first one is likely the default)
            statuses = LeadStatus.query.order_by(LeadStatus.id).all()
            
            if not statuses:
                print("No lead statuses found in database.")
                return
            
            print("Current Lead Statuses:")
            for i, status in enumerate(statuses):
                lead_count = Lead.query.filter_by(lead_status_id=status.id).count()
                print(f"  {i+1}. {status.status_name} (ID: {status.id}) - {lead_count} leads")
            
            # Count leads with no status
            no_status_count = Lead.query.filter_by(lead_status_id=None).count()
            print(f"  No Status (NULL) - {no_status_count} leads")
            
            print("\nWhich status should be converted to 'No Status'?")
            print("This is typically the first status that was auto-assigned to leads.")
            print("Enter the number (1-{}), or 0 to cancel:".format(len(statuses)))
            
            try:
                choice = int(input().strip())
                if choice == 0:
                    print("Operation cancelled.")
                    return
                elif choice < 1 or choice > len(statuses):
                    print("Invalid choice.")
                    return
                
                # Get the selected status
                selected_status = statuses[choice - 1]
                leads_to_update = Lead.query.filter_by(lead_status_id=selected_status.id).all()
                
                print(f"\nFound {len(leads_to_update)} leads with status '{selected_status.status_name}'")
                
                if len(leads_to_update) == 0:
                    print("No leads to update.")
                    return
                
                # Show some examples
                print("Examples of leads that will be updated:")
                for i, lead in enumerate(leads_to_update[:5]):
                    print(f"  - {lead.first_name} {lead.last_name} ({lead.email})")
                    if i == 4 and len(leads_to_update) > 5:
                        print(f"  ... and {len(leads_to_update) - 5} more")
                        break
                
                confirm = input(f"\nAre you sure you want to set these {len(leads_to_update)} leads to 'No Status'? (y/N): ").strip().lower()
                
                if confirm == 'y' or confirm == 'yes':
                    # Update the leads
                    updated_count = 0
                    for lead in leads_to_update:
                        lead.lead_status_id = None
                        updated_count += 1
                    
                    db.session.commit()
                    print(f"Successfully updated {updated_count} leads to 'No Status'.")
                else:
                    print("Operation cancelled.")
                    
            except ValueError:
                print("Invalid input. Please enter a number.")
                return
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    fix_lead_statuses()
