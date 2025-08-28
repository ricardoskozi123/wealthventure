#!/usr/bin/env python3
"""
Bulk admin assignment script
Make multiple users admin at once
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omcrm import create_app, db
from omcrm.users.models import User

def bulk_make_admin(emails):
    """Make multiple users admin"""
    app = create_app()
    
    with app.app_context():
        success_count = 0
        
        print("🚀 Bulk Admin Assignment")
        print("=" * 40)
        
        for email in emails:
            user = User.query.filter_by(email=email.strip()).first()
            
            if not user:
                print(f"❌ User '{email}' not found")
                continue
            
            if user.is_admin:
                print(f"⚠️  User '{user.get_name()}' ({email}) is already admin")
                continue
            
            # Make user admin
            user.is_admin = True
            success_count += 1
            print(f"✅ Made '{user.get_name()}' ({email}) admin")
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n🎉 SUCCESS: Made {success_count} users admin!")
        print("   They now have full platform access!")

# List of emails to make admin
ADMIN_EMAILS = [
    # Add your user emails here
    # "user1@example.com",
    # "user2@example.com",
    # "manager@example.com",
]

if __name__ == "__main__":
    if not ADMIN_EMAILS:
        print("📝 Edit this script and add emails to ADMIN_EMAILS list")
        print("Example:")
        print('ADMIN_EMAILS = ["user1@domain.com", "user2@domain.com"]')
        sys.exit(1)
    
    print(f"Making {len(ADMIN_EMAILS)} users admin...")
    bulk_make_admin(ADMIN_EMAILS)
