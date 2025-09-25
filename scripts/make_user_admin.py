#!/usr/bin/env python3
"""
Quick script to make a user admin by email
Usage: python3 scripts/make_user_admin.py user@email.com
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omcrm import create_app, db
from omcrm.users.models import User

def make_user_admin(email):
    """Make a user admin by email"""
    app = create_app()
    
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ User with email '{email}' not found")
            return False
        
        if user.is_admin:
            print(f"✅ User '{user.get_name()}' ({email}) is already an admin")
            return True
        
        # Make user admin
        user.is_admin = True
        db.session.commit()
        
        print(f"🎉 SUCCESS: '{user.get_name()}' ({email}) is now an admin!")
        print(f"   They now have full access to:")
        print(f"   - Activities, Transactions, Reports")
        print(f"   - All settings and management features")
        print(f"   - All client and lead management")
        return True

def list_all_users():
    """List all users and their admin status"""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        print("👥 All Users:")
        print("=" * 50)
        
        for user in users:
            status = "👑 ADMIN" if user.is_admin else "👤 User"
            role_name = user.role.name if user.role else "No Role"
            print(f"{status} - {user.get_name()} ({user.email}) - Role: {role_name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/make_user_admin.py <email>")
        print("   or: python3 scripts/make_user_admin.py --list")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_all_users()
    else:
        email = sys.argv[1]
        success = make_user_admin(email)
        sys.exit(0 if success else 1)


