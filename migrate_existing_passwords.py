#!/usr/bin/env python3
"""
Database Migration: Handle Existing Passwords
Check existing clients and provide info about juhu column population
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from omcrm.leads.models import Lead

def check_existing_passwords():
    """Check existing client passwords and juhu column status"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get all clients
            clients = Lead.query.filter_by(is_client=True).all()
            
            if not clients:
                print("📋 No clients found in the system.")
                return
            
            total_clients = len(clients)
            clients_with_juhu = 0
            clients_without_juhu = 0
            
            print(f"📊 Found {total_clients} clients in the system:")
            print("-" * 50)
            
            for client in clients:
                has_juhu = bool(client.juhu)
                has_password = bool(client._password)
                
                if has_juhu:
                    clients_with_juhu += 1
                    status = "✅ Ready (has viewable password)"
                else:
                    clients_without_juhu += 1
                    if has_password:
                        status = "⚠️  Has login password, but needs reset for viewing"
                    else:
                        status = "❌ No password set"
                
                print(f"📋 {client.first_name} {client.last_name} ({client.email}): {status}")
            
            print("-" * 50)
            print(f"📈 Summary:")
            print(f"   ✅ Clients with viewable passwords: {clients_with_juhu}")
            print(f"   ⚠️  Clients needing password reset: {clients_without_juhu}")
            
            if clients_without_juhu > 0:
                print("\n💡 Note: Clients without viewable passwords need their passwords reset")
                print("   to populate the 'juhu' column for business viewing.")
                print("   They can still login with their existing passwords.")
            
        except Exception as e:
            print(f"❌ Error checking passwords: {str(e)}")

if __name__ == '__main__':
    check_existing_passwords() 