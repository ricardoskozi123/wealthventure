"""
Domain-based routing middleware for OMCRM Trading Platform
Handles routing between client domain (investmentprohub.com) and CRM subdomain (crm.investmentprohub.com)
"""

from flask import request, redirect, url_for, session
from urllib.parse import urlparse
import os

class DomainRouter:
    """
    Middleware for handling domain-based routing between client and admin interfaces
    """
    
    def __init__(self, app=None):
        self.app = app
        self.client_domain = os.environ.get('CLIENT_DOMAIN', 'investmentprohub.com')
        self.crm_subdomain = os.environ.get('CRM_SUBDOMAIN', 'crm.investmentprohub.com')
        
        # For development/testing
        self.dev_domains = ['127.0.0.1', 'localhost', '84.32.188.252']
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the domain router with Flask app"""
        app.before_request(self.route_request)
    
    def is_dev_environment(self, host):
        """Check if we're in development environment"""
        return any(dev_host in host for dev_host in self.dev_domains)
    
    def get_domain_type(self, host):
        """Determine if request is for CRM or client domain"""
        if self.is_dev_environment(host):
            return 'dev'
        
        if host.startswith('crm.') or host == self.crm_subdomain:
            return 'crm'
        elif host == self.client_domain or host.startswith('www.'):
            return 'client'
        else:
            return 'unknown'
    
    def route_request(self):
        """Main routing logic executed before each request"""
        host = request.host.lower()
        path = request.path
        domain_type = self.get_domain_type(host)
        
        # Skip routing for static files and API endpoints
        if path.startswith(('/static', '/api', '/socket.io')):
            return None
        
        # Skip routing in development
        if domain_type == 'dev':
            return None
        
        # Admin/CRM routes should only be accessible on CRM subdomain
        admin_routes = ['/login', '/register', '/admin', '/settings', '/users', 
                       '/leads', '/deals', '/reports', '/activities', '/tasks',
                       '/transactions']
        
        # Client routes should only be accessible on main domain
        client_routes = ['/client', '/webtrader']
        
        is_admin_route = any(path.startswith(route) for route in admin_routes)
        is_client_route = any(path.startswith(route) for route in client_routes)
        
        # Handle domain routing
        if domain_type == 'crm':
            # On CRM subdomain - allow admin routes, redirect client routes
            if is_client_route:
                return redirect(f"https://{self.client_domain}{path}")
            # Set session flag for admin interface
            session['domain_type'] = 'crm'
            
        elif domain_type == 'client':
            # On client domain - allow client routes, redirect admin routes to CRM
            if is_admin_route and path != '/client/login':
                return redirect(f"https://{self.crm_subdomain}{path}")
            # Set session flag for client interface
            session['domain_type'] = 'client'
            
            # Redirect /login to /client/login on client domain
            if path == '/login':
                return redirect(url_for('users.client_login'))
        
        return None

def get_login_redirect_url():
    """Get the appropriate login URL based on current domain"""
    host = request.host.lower()
    
    # Development environment
    if any(dev_host in host for dev_host in ['127.0.0.1', 'localhost', '84.32.188.252']):
        return '/login'  # Default admin login for dev
    
    # Production environment
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
        # Return current domain
        host = request.host.lower()
        if host.startswith('crm.'):
            return f"https://{crm_subdomain}"
        else:
            return f"https://{client_domain}" 