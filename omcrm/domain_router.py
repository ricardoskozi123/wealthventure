"""
Domain-based routing middleware for OMCRM Trading Platform
Handles routing between client domain (investmentprohub.com) and CRM subdomain (crm.investmentprohub.com)
"""

from flask import request, redirect, url_for, session, g
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
        
        # Define route permissions
        self.admin_only_routes = [
            '/admin', '/settings', '/users', '/leads', '/deals', 
            '/reports', '/activities', '/tasks', '/transactions'
        ]
        
        self.client_only_routes = [
            '/client', '/webtrader'
        ]
        
        # Routes that admins can access on client domain (for managing clients)
        self.admin_accessible_client_routes = [
            '/clients',  # Admin can view client list
            '/webtrader/instruments',  # Admin can manage instruments
            '/webtrader/list_instruments',  # Admin can list instruments
            '/api'  # Admin can use API endpoints
        ]
        
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
    
    def is_admin_route(self, path):
        """Check if path is an admin-only route"""
        return any(path.startswith(route) for route in self.admin_only_routes)
    
    def is_client_route(self, path):
        """Check if path is a client-only route"""
        return any(path.startswith(route) for route in self.client_only_routes)
    
    def is_admin_accessible_client_route(self, path):
        """Check if admin can access this client domain route"""
        return any(path.startswith(route) for route in self.admin_accessible_client_routes)
    
    def route_request(self):
        """Main routing logic executed before each request"""
        host = request.host.lower()
        path = request.path
        domain_type = self.get_domain_type(host)
        
        # Skip routing for static files and API endpoints
        if path.startswith(('/static', '/socket.io')):
            return None
        
        # Skip routing in development
        if domain_type == 'dev':
            return None
        
        # Set domain context for the application
        g.domain_type = domain_type
        g.is_client_domain = (domain_type == 'client')
        g.is_crm_domain = (domain_type == 'crm')
        
        # Handle domain routing
        if domain_type == 'client':
            # On client domain (investmentprohub.com)
            
            # IMPORTANT: Redirect /login to /client/login
            if path == '/login':
                return redirect('/client/login')
            
            # Admin-only routes should redirect to CRM subdomain
            if self.is_admin_route(path):
                return redirect(f"https://{self.crm_subdomain}{path}")
            
            # Set session flag for client interface
            session['domain_type'] = 'client'
            session['allowed_routes'] = self.client_only_routes + self.admin_accessible_client_routes
            
        elif domain_type == 'crm':
            # On CRM subdomain (crm.investmentprohub.com)
            
            # Pure client routes should redirect to main domain
            if self.is_client_route(path) and not self.is_admin_accessible_client_route(path):
                return redirect(f"https://{self.client_domain}{path}")
            
            # Set session flag for admin interface
            session['domain_type'] = 'crm'
            session['allowed_routes'] = self.admin_only_routes + self.admin_accessible_client_routes
        
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

def is_route_allowed(path):
    """Check if current route is allowed based on domain"""
    allowed_routes = session.get('allowed_routes', [])
    return any(path.startswith(route) for route in allowed_routes)