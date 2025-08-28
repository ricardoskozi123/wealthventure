from flask import render_template, abort, redirect, url_for, flash
from functools import wraps
from flask_login import current_user
from omcrm.users.models import Resource, Role
from omcrm.leads.models import Lead
from omcrm.deals.models import Deal


class NullRBACRowException(Exception):
    pass


class RBACActionNotFoundException(Exception):
    pass


def is_allowed(role_id, resource, action):
    row = Role.query \
        .with_entities(
            Role.id,
            Resource.can_view,
            Resource.can_edit,
            Resource.can_create,
            Resource.can_delete,
            Resource.can_impersonate) \
        .filter_by(id=role_id) \
        .join(Role.resources) \
        .filter_by(name=resource) \
        .first()

    if not row:
        raise NullRBACRowException

    if action == 'view':
        return row.can_view
    elif action == 'create':
        return row.can_create
    elif action == 'update':
        return row.can_edit
    elif action == 'remove':
        return row.can_delete
    elif action == 'impersonate':
        return row.can_impersonate
    else:
        raise RBACActionNotFoundException


# Decorator for user type safety
def user_type_safe(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if current user is a Lead (client) instead of a User (admin/staff)
        if isinstance(current_user._get_current_object(), Lead):
            # Clients are immediately redirected to their dashboard without seeing error page
            return redirect(url_for('client.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def check_access(resource, operation):
    def wrapper(function):
        @wraps(function)
        @user_type_safe  # Apply user type check first
        def decorator(*args, **kwargs):
            if current_user.is_admin:
                return function(*args, **kwargs)

            if not current_user.role:
                print(f"❌ User {current_user.email} has no role assigned")
                abort(403)  # Forbidden

            # Debug: Print user's role and resources
            print(f"🔍 Checking access for {current_user.email} to {resource} ({operation})")
            print(f"   Role: {current_user.role.name}")
            print(f"   Resources: {[res.name for res in current_user.role.resources]}")

            for res in current_user.role.resources:
                if resource == res.name:
                    print(f"   Found resource '{resource}': view={res.can_view}, create={res.can_create}, edit={res.can_edit}, delete={res.can_delete}")
                    
                    if operation == 'view' and res.can_view:
                        print(f"✅ Access granted for {operation}")
                        return function(*args, **kwargs)
                    elif operation == 'edit' and res.can_edit:
                        print(f"✅ Access granted for {operation}")
                        return function(*args, **kwargs)
                    elif operation == 'update' and res.can_edit:
                        print(f"✅ Access granted for {operation}")
                        return function(*args, **kwargs)
                    elif operation == 'create' and res.can_create:
                        print(f"✅ Access granted for {operation}")
                        return function(*args, **kwargs)
                    elif operation == 'delete' and res.can_delete:
                        print(f"✅ Access granted for {operation}")
                        return function(*args, **kwargs)
                    elif operation == 'remove' and res.can_delete:
                        print(f"✅ Access granted for {operation}")
                        return function(*args, **kwargs)
                    elif operation == 'impersonate' and res.can_impersonate:
                        print(f"✅ Access granted for {operation}")
                        return function(*args, **kwargs)
                    else:
                        print(f"❌ Operation '{operation}' not allowed for resource '{resource}'")
                        abort(403)  # Forbidden
            
            print(f"❌ Resource '{resource}' not found in user's role")
            abort(403)  # Forbidden
        return decorator
    return wrapper


def is_admin(function):
    @wraps(function)
    @user_type_safe  # Apply user type check first
    def decorator(*args, **kwargs):
        if current_user.is_admin:
            return function(*args, **kwargs)
        else:
            abort(403)  # Forbidden
    return decorator


def is_team_leader(function):
    @wraps(function)
    @user_type_safe  # Apply user type check first
    def decorator(*args, **kwargs):
        if current_user.is_admin or current_user.is_team_leader:
            return function(*args, **kwargs)
        else:
            abort(403)  # Forbidden
    return decorator


def get_visible_leads_query(base_query):
    """
    Apply team-based permissions to leads query.
    Managers with 'can_view_all_leads' permission can see all leads.
    Regular users see only their assigned leads.
    """
    if current_user.is_admin:
        return base_query
    
    # Check if user has permission to view all leads
    if current_user.role:
        for res in current_user.role.resources:
            if res.name == 'leads' and hasattr(res, 'can_view_all_leads') and res.can_view_all_leads:
                # Manager can see all leads
                return base_query
    
    # Regular user - filter by owner_id
    from omcrm.leads.models import Lead
    return base_query.filter(Lead.owner_id == current_user.id)


def get_visible_clients_query(base_query):
    """
    Apply team-based permissions to clients query.
    Managers with 'can_view_all_clients' permission can see all clients.
    Regular users see only their assigned clients.
    """
    if current_user.is_admin:
        return base_query
    
    # Check if user has permission to view all clients
    if current_user.role:
        for res in current_user.role.resources:
            if res.name == 'leads' and hasattr(res, 'can_view_all_clients') and res.can_view_all_clients:
                # Manager can see all clients
                return base_query
    
    # Regular user - filter by owner_id
    from omcrm.leads.models import Lead
    return base_query.filter(Lead.owner_id == current_user.id)


def get_visible_deals_query(base_query):
    """
    Apply team-based permissions to deals query.
    For now, follows the same logic as leads.
    """
    if current_user.is_admin:
        return base_query
        
    # Check if user has permission to view all leads (deals follow leads permissions)
    if current_user.role:
        for res in current_user.role.resources:
            if res.name == 'leads' and hasattr(res, 'can_view_all_leads') and res.can_view_all_leads:
                # Manager can see all deals
                return base_query
    
    # Regular user - filter by owner_id
    from omcrm.deals.models import Deal
    return base_query.filter(Deal.owner_id == current_user.id)


def can_impersonate_clients():
    """Check if current user can impersonate clients (admin or has impersonate permission on leads)"""
    # Allow all users to impersonate clients
    return True
    
    # Original code:
    # if current_user.is_admin:
    #     return True
    #     
    # if not current_user.role:
    #     return False
    #     
    # for res in current_user.role.resources:
    #     if res.name == 'leads' and res.can_impersonate:
    #         return True
    #         
    # return False


# 🔧 NEW: Sidebar Navigation Permission Helper
def can_view_sidebar_item(item_name):
    """
    Check if the current user can view a specific sidebar navigation item
    """
    if not current_user.is_authenticated:
        return False
        
    # Admins can see everything
    if getattr(current_user, 'is_admin', False):
        return True
        
    if not current_user.role:
        return False
        
    # Find the resource permission for this user's role
    resource = None
    for res in current_user.role.resources:
        if res.name == 'leads':  # We use 'leads' resource as the primary permission resource
            resource = res
            break
            
    if not resource:
        return False
        
    # Map sidebar items to permission attributes
    permission_map = {
        'dashboard': 'can_view_dashboard',
        'leads': 'can_view_leads', 
        'pipeline': 'can_view_pipeline',
        'activities': 'can_view_activities',
        'tasks': 'can_view_tasks',
        'lead_sources': 'can_view_lead_sources',
        'client_statuses': 'can_view_client_statuses',
        'trading_instruments': 'can_view_trading_instruments',
        'clients': 'can_view_clients_page',
        'reports': 'can_view_reports',
        'pipeline_stages': 'can_view_pipeline_stages',
        'transactions': 'can_view_transactions',
        'settings': 'can_view_settings'
    }
    
    permission_attr = permission_map.get(item_name)
    if not permission_attr:
        return True  # Default to showing if permission not mapped
        
    return getattr(resource, permission_attr, True)  # Default to True if attribute doesn't exist
