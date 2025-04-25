"""
Script to update admin roles with the new impersonate permission
"""
from flask import Flask
from omcrm import db, create_app
from omcrm.users.models import Resource, Role
from sqlalchemy import text

def update_admin_permissions():
    """Updates all admin roles to have the impersonate permission"""
    app = create_app()
    with app.app_context():
        try:
            # Check if the column exists
            db.session.execute(text("SELECT can_impersonate FROM resource LIMIT 1"))
            print("Column exists, updating permissions...")
        except Exception as e:
            print(f"Column doesn't exist yet or another error occurred: {e}")
            print("Please run the database migration first.")
            return

        # Get admin role(s)
        admin_roles = Role.query.filter(Role.name.ilike('%admin%')).all()
        
        if not admin_roles:
            print("No admin roles found")
            return

        print(f"Found {len(admin_roles)} admin role(s):")
        for role in admin_roles:
            print(f"- {role.name}")
            
            # Update each resource for this role to have impersonate permission
            resources = role.resources
            for resource in resources:
                if resource.name == 'leads' or resource.name == 'clients':
                    resource.can_impersonate = True
                    print(f"  Updated {resource.name} to have impersonate permission")
                    
        # Commit changes
        db.session.commit()
        print("Updated admin roles successfully!")

if __name__ == "__main__":
    update_admin_permissions() 