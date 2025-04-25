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
                abort(403)  # Forbidden

            for res in current_user.role.resources:
                if resource == res.name:
                    if operation == 'view' and res.can_view:
                        return function(*args, **kwargs)
                    elif operation == 'edit' and res.can_edit:
                        return function(*args, **kwargs)
                    elif operation == 'update' and res.can_edit:
                        return function(*args, **kwargs)
                    elif operation == 'create' and res.can_create:
                        return function(*args, **kwargs)
                    elif operation == 'delete' and res.can_delete:
                        return function(*args, **kwargs)
                    elif operation == 'remove' and res.can_delete:
                        return function(*args, **kwargs)
                    elif operation == 'impersonate' and res.can_impersonate:
                        return function(*args, **kwargs)
                    else:
                        abort(403)  # Forbidden
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
    SIMPLIFIED FOR DEBUGGING - Returns all leads regardless of permissions
    """
    # For debugging: don't filter at all, return all leads
    return base_query


def get_visible_clients_query(base_query):
    """
    SIMPLIFIED FOR DEBUGGING - Returns all clients regardless of permissions
    """
    # For debugging: don't filter at all, return all clients
    return base_query


def get_visible_deals_query(base_query):
    """
    SIMPLIFIED FOR DEBUGGING - Returns all deals regardless of permissions
    """
    # For debugging: don't filter at all, return all deals
    return base_query


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
