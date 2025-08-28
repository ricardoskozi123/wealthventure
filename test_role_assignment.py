#!/usr/bin/env python3
"""
Test script to verify role assignment fix
Run this to test that multiple users can have the same role
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from omcrm.users.models import User, Role

def test_role_assignment():
    """Test that multiple users can have the same role"""
    app = create_app()
    
    with app.app_context():
        print("🧪 Testing Role Assignment Fix")
        print("=" * 40)
        
        # Get or create a test role
        test_role = Role.query.filter_by(name='test_agent').first()
        if not test_role:
            test_role = Role(name='test_agent')
            db.session.add(test_role)
            db.session.commit()
            print("✅ Created test role: test_agent")
        else:
            print("✅ Using existing test role: test_agent")
        
        # Get first two users for testing
        users = User.query.limit(2).all()
        
        if len(users) < 2:
            print("❌ Need at least 2 users in database for testing")
            return False
        
        user1, user2 = users[0], users[1]
        print(f"👤 User 1: {user1.get_name()}")
        print(f"👤 User 2: {user2.get_name()}")
        
        # Clear any existing roles
        user1.role_id = None
        user2.role_id = None
        db.session.commit()
        
        # Assign role to user1
        user1.role_id = test_role.id
        db.session.commit()
        print(f"✅ Assigned {test_role.name} to {user1.get_name()}")
        
        # Check user1 has the role
        user1_refreshed = User.query.get(user1.id)
        if user1_refreshed.role_id == test_role.id:
            print(f"✅ User1 has role: {user1_refreshed.role.name}")
        else:
            print(f"❌ User1 role assignment failed")
            return False
        
        # Assign same role to user2
        user2.role_id = test_role.id
        db.session.commit()
        print(f"✅ Assigned {test_role.name} to {user2.get_name()}")
        
        # Check BOTH users still have the role
        user1_refreshed = User.query.get(user1.id)
        user2_refreshed = User.query.get(user2.id)
        
        print("\n🔍 Final Check:")
        if user1_refreshed.role_id == test_role.id:
            print(f"✅ User1 ({user1_refreshed.get_name()}) still has role: {user1_refreshed.role.name}")
        else:
            print(f"❌ User1 ({user1_refreshed.get_name()}) lost the role!")
            return False
            
        if user2_refreshed.role_id == test_role.id:
            print(f"✅ User2 ({user2_refreshed.get_name()}) has role: {user2_refreshed.role.name}")
        else:
            print(f"❌ User2 ({user2_refreshed.get_name()}) doesn't have the role!")
            return False
        
        # Test the reverse relationship
        role_refreshed = Role.query.get(test_role.id)
        users_with_role = [u for u in User.query.all() if u.role_id == test_role.id]
        
        print(f"\n📊 Users with role '{test_role.name}': {len(users_with_role)}")
        for user in users_with_role:
            print(f"   - {user.get_name()}")
        
        print("\n🎉 SUCCESS: Multiple users can now have the same role!")
        return True

if __name__ == "__main__":
    success = test_role_assignment()
    sys.exit(0 if success else 1)
