from flask import request, session
from flask_login import current_user
from sqlalchemy import text
from omcrm.users.models import User
from omcrm.leads.models import Lead
from datetime import datetime, timedelta


class CommonFilters:

    @staticmethod
    def set_owner(filters, module, key):
        if not module or not filters or not key:
            return None

        if request.method == 'POST':
            if current_user.is_admin:
                if filters.assignees.data:
                    owner = text('%s.owner_id=%d' % (module, filters.assignees.data.id))
                    session[key] = filters.assignees.data.id
                else:
                    session.pop(key, None)
                    owner = True
            else:
                # Check if user has permission to view all clients/leads
                can_view_all = False
                if current_user.role:
                    for res in current_user.role.resources:
                        # For clients, check can_view_all_clients on leads resource
                        # For leads, check can_view_all_leads on leads resource
                        if res.name == 'leads':
                            if (module == 'Lead' and hasattr(res, 'can_view_all_clients') and res.can_view_all_clients) or \
                               (module == 'Lead' and hasattr(res, 'can_view_all_leads') and res.can_view_all_leads):
                                can_view_all = True
                                break
                
                if can_view_all:
                    # User can see all - don't filter by owner
                    if filters.assignees.data:
                        owner = text('%s.owner_id=%d' % (module, filters.assignees.data.id))
                        session[key] = filters.assignees.data.id
                    else:
                        session.pop(key, None)
                        owner = True
                else:
                    # Regular user - filter by owner
                    owner = text('%s.owner_id=%d' % (module, current_user.id))
                    session[key] = current_user.id
        else:
            if key in session:
                owner = text('%s.owner_id=%d' % (module, session[key]))
                filters.assignees.data = User.get_by_id(session[key])
            else:
                # Check if user has permission to view all
                can_view_all = False
                if current_user.is_admin:
                    can_view_all = True
                elif current_user.role:
                    for res in current_user.role.resources:
                        if res.name == 'leads':
                            if (module == 'Lead' and hasattr(res, 'can_view_all_clients') and res.can_view_all_clients) or \
                               (module == 'Lead' and hasattr(res, 'can_view_all_leads') and res.can_view_all_leads):
                                can_view_all = True
                                break
                
                owner = True if can_view_all else text('%s.owner_id=%d' % (module, current_user.id))
        return owner


    @staticmethod
    def set_clients(filters, module, key):
        if not module or not filters or not key:
            return None

        client = True
        if request.method == 'POST':
            if filters.clients.data:
                client = text('%s.client_id=%d' % (module, filters.clients.data.id))
                session[key] = filters.clients.data.id
            else:
                session.pop(key, None)
        else:
            if key in session:
                client = text('%s.client_id=%d' % (module, session[key]))
                filters.clients.data = Lead.get_by_id(session[key])
        return client

    @staticmethod
    def set_search(filters, key):
        search = None
        if request.method == 'POST':
            search = filters.txt_search.data
            session[key] = search

        if key in session:
            filters.txt_search.data = session[key]
            search = session[key]
        return search

def timeago(date_time):
    """
    Returns a human-readable string representing how long ago a datetime was.
    """
    now = datetime.utcnow()
    diff = now - date_time
    
    if diff < timedelta(seconds=10):
        return "just now"
    elif diff < timedelta(minutes=1):
        return f"{diff.seconds} seconds ago"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif diff < timedelta(days=30):
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif diff < timedelta(days=365):
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
