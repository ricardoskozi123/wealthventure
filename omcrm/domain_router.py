"""
SIMPLIFIED Domain routing for OMCRM Trading Platform
"""

from flask import request, redirect, session, g, abort
import os

class DomainRouter:
    """
    SIMPLIFIED domain router - handles login redirects and admin IP whitelist
    """
    
    def __init__(self, app=None):
        self.app = app
        self.client_domain = os.environ.get('CLIENT_DOMAIN', 'investmentprohub.com')
        self.crm_subdomain = os.environ.get('CRM_SUBDOMAIN', 'crm.investmentprohub.com')
        
        # Admin IP Whitelist - Add your trusted IPs here
        self.admin_whitelist_ips = [
            '127.0.0.1',
            'localhost',
            '84.32.188.252',
              '84.32.191.249',  # Your current VPS IP
            # Add more trusted IPs below:
            # '192.168.1.100',  # Your office IP
            # '203.0.113.0/24', # Your office network (CIDR notation)
        ]
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the domain router with Flask app"""
        app.before_request(self.route_request)
    
    def get_client_ip(self):
        """Get the real client IP address"""
        # Check for forwarded IPs first (nginx/proxy)
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr
    
    def is_admin_ip_allowed(self):
        """Check if current IP is allowed for admin access"""
        client_ip = self.get_client_ip()
        
        # Always allow localhost/development
        if client_ip in ['127.0.0.1', '::1', 'localhost']:
            return True
        
        # Check against whitelist
        for allowed_ip in self.admin_whitelist_ips:
            if client_ip == allowed_ip:
                return True
            # You can add CIDR range checking here if needed
        
        return False
    
    def route_request(self):
        """SIMPLIFIED routing - handle login redirects and IP whitelist"""
        host = request.host.lower()
        path = request.path
        
        # Skip routing for static files and API endpoints
        if path.startswith(('/static', '/socket.io', '/api')):
            return None
        
        # Set domain context
        if host.startswith('crm.'):
            g.domain_type = 'crm'
            session['domain_type'] = 'crm'
            
            # 🔐 SECURITY: Check IP whitelist for admin routes
            if path.startswith(('/login', '/admin', '/settings', '/users', '/leads', '/deals', '/reports', '/activities', '/tasks', '/transactions', '/clients')):
                if not self.is_admin_ip_allowed():
                    print(f"🚫 Admin access denied for IP: {self.get_client_ip()}")
                    abort(403)  # Forbidden
        else:
            g.domain_type = 'client'
            session['domain_type'] = 'client'
        
        # Handle login redirects
        if path == '/login':
            if host.startswith('crm.'):
                # On CRM domain - check IP whitelist first
                if not self.is_admin_ip_allowed():
                    print(f"🚫 Admin login blocked for IP: {self.get_client_ip()}")
                    abort(403)  # Forbidden
                # IP is allowed - stay for admin login
                return None
            else:
                # On client domain - redirect to client login
                return redirect('/client/login')
        
        # Let everything else through
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