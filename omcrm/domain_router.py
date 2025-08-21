"""
SIMPLIFIED Domain routing for OMCRM Trading Platform
"""

from flask import request, redirect, session, g
import os

class DomainRouter:
    """
    SIMPLIFIED domain router - only handles basic login redirects
    """
    
    def __init__(self, app=None):
        self.app = app
        self.client_domain = os.environ.get('CLIENT_DOMAIN', 'investmentprohub.com')
        self.crm_subdomain = os.environ.get('CRM_SUBDOMAIN', 'crm.investmentprohub.com')
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the domain router with Flask app"""
        app.before_request(self.route_request)
    
    def route_request(self):
        """SIMPLIFIED routing - only handle login redirects"""
        host = request.host.lower()
        path = request.path
        
        # Skip routing for static files and API endpoints
        if path.startswith(('/static', '/socket.io', '/api')):
            return None
        
        # Set domain context
        if host.startswith('crm.'):
            g.domain_type = 'crm'
            session['domain_type'] = 'crm'
        else:
            g.domain_type = 'client'
            session['domain_type'] = 'client'
        
        # ONLY handle login redirects - nothing else!
        if path == '/login':
            if host.startswith('crm.'):
                # On CRM domain - stay for admin login
                return None
            else:
                # On client domain - redirect to client login
                return redirect('/client/login')
        
        # Let everything else through - no more blocking!
        return None

# Keep these for compatibility
def get_login_redirect_url():
    """Get the appropriate login URL based on current domain"""
    host = request.host.lower()
    if host.startswith('crm.'):
        return '/login'  # Admin login
    else:
        return '/client/login'  # Client login

def get_appropriate_domain_url(route_type='current'):
    """Get URL for appropriate domain based on route type"""
    client_domain = os.environ.get('CLIENT_DOMAIN', 'investmentprohub.com')
    crm_subdomain = os.environ.get('CRM_SUBDOMAIN', 'crm.investmentprohub.com')
    
    if route_type == 'admin':
        return f"https://{crm_subdomain}"
    elif route_type == 'client':
        return f"https://{client_domain}"
    else:
        host = request.host.lower()
        if host.startswith('crm.'):
            return f"https://{crm_subdomain}"
        else:
            return f"https://{client_domain}"

def is_route_allowed(path):
    """Always allow routes - no more restrictions"""
    return True