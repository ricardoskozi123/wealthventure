from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask import request

csrf = CSRFProtect()

def init_csrf(app):
    # Configure CSRF to exempt API routes
    def csrf_exempt_api():
        return request.path.startswith('/api/')
    
    csrf.init_app(app)
    csrf.exempt(csrf_exempt_api)
    
    # Make csrf token available globally to templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf()) 
