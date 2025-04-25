from flask_wtf.csrf import CSRFProtect, generate_csrf

csrf = CSRFProtect()

def init_csrf(app):
    csrf.init_app(app)
    
    # Make csrf token available globally to templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf()) 
