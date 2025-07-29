from flask import Blueprint, session, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from flask import render_template, flash, url_for, redirect, request

from omcrm import db, bcrypt
from .forms import Register, Login
from .models import User
from omcrm.leads.models import Lead
from ..webtrader.models import TradingInstrument
from .models import Role, Resource

users = Blueprint('users', __name__)

@users.route("/login", methods=['GET', 'POST'])
def login():
    """Admin/Agent login route for CRM access"""
    # Clear any existing session data to avoid conflicts
    session.clear()
    
    # Set login type to admin/user
    session['login_type'] = 'admin'
    
    print(f"[DEBUG] Admin login route accessed. Session: {session}")
    
    if current_user.is_authenticated:
        if isinstance(current_user, Lead) and current_user.is_client:
            return redirect(url_for('client.dashboard'))
        return redirect(url_for('main.home'))

    form = Login()
    if form.validate_on_submit():
        # Only look for User objects (admins/agents), not Leads
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if not user.is_user_active:
                flash("User has not been granted access to the system! Please contact the system administrator", 'danger')
            elif not bcrypt.check_password_hash(user.password, form.password.data):
                flash('Invalid Password!', 'danger')
            else:
                # Successfully authenticated admin/agent
                print(f"[DEBUG] Admin login successful: {user.id}, {user.email}")
                login_user(user, remember=form.remember.data)
                print(f"[DEBUG] Current user after login: {current_user.id}, type: {type(current_user)}")
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('main.home'))
        else:
            flash('Invalid email or password', 'danger')

    # This is specifically for CRM admin/agent login
    return render_template("login.html", title="TradingCRM - Admin Login", form=form)

@users.route("/client/login", methods=['GET', 'POST'])
def client_login():
    """Client login route for client portal access"""
    # Clear any existing session data to avoid conflicts
    session.clear()
    
    # Set login type to client
    session['login_type'] = 'client'
    
    print(f"[DEBUG] Client login route accessed. Session: {session}")
    
    if current_user.is_authenticated:
        if isinstance(current_user, Lead) and current_user.is_client:
            return redirect(url_for('client.dashboard'))
        return redirect(url_for('main.home'))

    form = Login()
    if form.validate_on_submit():
        # Only look for Lead objects that are clients, not users
        client = Lead.query.filter_by(email=form.email.data, is_client=True).first()
        if client and client.check_password(form.password.data):
            if client.is_active:
                print(f"[DEBUG] Client login successful: {client.id}, {client.email}")
                
                # 🕒 NEW: Track login activity
                client.update_last_login()
                
                login_user(client, remember=form.remember.data)
                print(f"[DEBUG] Current user after login: {current_user.id}, type: {type(current_user)}, login_type: {session.get('login_type')}")
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('client.dashboard'))
            else:
                flash('This account is inactive. Please contact support.', 'danger')
        else:
            flash('Invalid email or password', 'danger')

    # Render client-specific login template
    return render_template("client_login.html", title="Trading Platform - Client Login", form=form)

@users.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = Register()
    
    # Check if any users exist - if not, this is the first user (admin)
    users_exist = User.query.first() is not None
    
    if request.method == 'POST':
        if form.validate_on_submit():
            hashed_pwd = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            
            # First registered user will always be admin
            is_admin_user = not users_exist or form.is_admin.data
            
            user = User(first_name=form.first_name.data, last_name=form.last_name.data,
                        email=form.email.data, is_admin=is_admin_user, is_first_login=False,
                        is_user_active=True, password=hashed_pwd)
            db.session.add(user)
            db.session.commit()
            
            # Create the default role if not exists
            if not Role.query.filter_by(name='agent').first():
                agent_role = Role(name='agent')
                
                # Add default resources and permissions
                leads_resource = Resource(name='leads', can_view=True, can_create=False, 
                                         can_edit=True, can_delete=False)
                agent_role.resources.append(leads_resource)
                
                deals_resource = Resource(name='deals', can_view=True, can_create=False, 
                                         can_edit=True, can_delete=False)
                agent_role.resources.append(deals_resource)
                
                db.session.add(agent_role)
                db.session.commit()
            
            flash('User has been created! You can now login', 'success')
            return redirect(url_for('users.login'))
        else:
            flash(f'Failed to register user!', 'danger')
            
    # Show admin checkbox only if the user is already logged in as admin
    form.is_admin.render_kw = {'disabled': not current_user.is_authenticated or not current_user.is_admin}
    
    return render_template("register.html", title="TradingCRM - Register New User", form=form, 
                          is_first_user=not users_exist)

@users.route("/logout")
def logout():
    print(f"[DEBUG] Logout route called. Current user: {current_user}")
    
    # OPTIMIZED: Simplified logout process for better performance
    user_type = 'client' if isinstance(current_user, Lead) and current_user.is_client else 'admin'
    
    # Check for admin impersonation (simplified)
    was_impersonating = 'admin_user_id' in session
    
    # Quick logout and session clear
    logout_user()
    session.clear()
    
    print(f"[DEBUG] Logout complete - user was {user_type}")
    
    # Simplified redirect logic
    if was_impersonating:
        flash('Returned to admin account.', 'info')
        return redirect(url_for('main.home'))
    elif user_type == 'client':
        return redirect(url_for('users.client_login'))
    else:
        return redirect(url_for('users.login'))

# @users.route("/add_instrument", methods=['GET', 'POST'])
# @login_required
# def add_instrument():
#     if request.method == 'POST':
#         symbol = request.form.get('symbol').upper()
#         name = request.form.get('name')
#         current_price = get_real_time_price(symbol)
#
#         new_instrument = TradingInstrument(symbol=symbol, name=name, current_price=current_price)
#         db.session.add(new_instrument)
#         db.session.commit()
#         flash('Instrument added successfully!', 'success')
#         return redirect(url_for('users.add_instrument'))
#
#     return render_template('add_instrument.html')
#
# @users.route("/update_instrument_prices")
# @login_required
# def update_instrument_prices():
#     instruments = TradingInstrument.query.all()
#     for instrument in instruments:
#         instrument.current_price = get_real_time_price(instrument.symbol)
#     db.session.commit()
#     return jsonify({'status': 'success'})

# 🔐 PASSWORD RESET ROUTES

@users.route("/forgot-password", methods=['GET', 'POST'])
def forgot_password():
    """Password reset request for both admin users and clients"""
    from .forms import PasswordResetRequestForm
    from omcrm.utils.password_reset import PasswordResetManager
    from omcrm.utils.email_service import EmailService, EmailTemplates
    from flask import current_app, request
    
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('main.home'))
    
    form = PasswordResetRequestForm()
    
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        
        # Check rate limiting
        if PasswordResetManager.is_rate_limited(email, max_attempts=5, hours=1):
            flash('Too many password reset attempts. Please try again later.', 'warning')
            return render_template('users/forgot_password.html', form=form, title='Forgot Password')
        
        # Create reset token
        brand_name = current_app.config.get('PLATFORM_NAME', 'OMCRM Trading')
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        result = PasswordResetManager.create_reset_token(
            email=email,
            expiry_minutes=30,
            ip_address=ip_address,
            brand_name=brand_name
        )
        
        if result['success']:
            # Generate reset link
            reset_link = url_for('users.reset_password', 
                               token=result['token'].token, 
                               _external=True)
            
            # Generate email template
            email_template = EmailTemplates.password_reset_template(
                user_name=result['user_name'],
                reset_link=reset_link,
                platform_name=brand_name,
                expiry_minutes=30
            )
            
            # Send email
            email_result = EmailService.send_email(
                to_email=email,
                subject=email_template['subject'],
                html_content=email_template['html'],
                text_content=email_template['text'],
                brand_name=brand_name
            )
            
            if email_result['success']:
                flash('A password reset link has been sent to your email address.', 'success')
            else:
                flash(f'Failed to send reset email: {email_result["message"]}', 'danger')
                # For debugging - remove in production
                print(f"Email send failed: {email_result}")
        else:
            if result['user_found']:
                flash(result['message'], 'warning')
            else:
                # Don't reveal if email exists or not for security
                flash('If an account with this email exists, a password reset link has been sent.', 'info')
        
        # Always redirect to prevent form resubmission
        return redirect(url_for('users.forgot_password'))
    
    return render_template('users/forgot_password.html', 
                         form=form, 
                         title='Forgot Password')


@users.route("/reset-password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    """Reset password using a valid token"""
    from .forms import PasswordResetForm
    from omcrm.utils.password_reset import PasswordResetManager
    from flask import current_app
    
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('main.home'))
    
    # Validate token first
    validation_result = PasswordResetManager.validate_reset_token(token)
    
    if not validation_result['success']:
        flash(validation_result['message'], 'danger')
        return redirect(url_for('users.forgot_password'))
    
    user = validation_result['user']
    reset_token = validation_result['token']
    
    form = PasswordResetForm()
    
    if form.validate_on_submit():
        # Reset the password
        reset_result = PasswordResetManager.reset_password(
            token_string=token,
            new_password=form.password.data
        )
        
        if reset_result['success']:
            flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
            
            # Redirect to appropriate login page based on user type
            if hasattr(user, 'is_client') and user.is_client:
                return redirect(url_for('users.client_login'))
            else:
                return redirect(url_for('users.login'))
        else:
            flash(f'Failed to reset password: {reset_result["message"]}', 'danger')
    
    # Prepare user info for template
    user_name = f"{user.first_name} {user.last_name}".strip()
    platform_name = current_app.config.get('PLATFORM_NAME', 'OMCRM Trading')
    
    return render_template('users/reset_password.html', 
                         form=form, 
                         user_name=user_name,
                         platform_name=platform_name,
                         title='Reset Password')


@users.route("/change-password", methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password for logged-in users"""
    from .forms import ChangePasswordForm
    from omcrm import bcrypt
    
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verify current password
        if not bcrypt.check_password_hash(current_user.password, form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('users/change_password.html', form=form, title='Change Password')
        
        # Update password
        try:
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            current_user.password = hashed_password
            db.session.commit()
            
            flash('Your password has been changed successfully.', 'success')
            return redirect(url_for('main.home'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to change password: {str(e)}', 'danger')
    
    return render_template('users/change_password.html', 
                         form=form, 
                         title='Change Password')


@users.route("/admin/test-email")
@login_required
def test_email_config():
    """Test email configuration (admin only)"""
    from omcrm.utils.email_service import EmailService
    from flask import current_app, jsonify
    
    # Check if user is admin
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.home'))
    
    brand_name = current_app.config.get('PLATFORM_NAME', 'OMCRM Trading')
    result = EmailService.test_smtp_connection(brand_name)
    
    if request.args.get('json'):
        return jsonify(result)
    
    if result['success']:
        flash(f'✅ Email configuration test successful: {result["message"]}', 'success')
    else:
        flash(f'❌ Email configuration test failed: {result["message"]}', 'danger')
    
    return redirect(url_for('settings.appconfig_index'))


@users.route("/admin_login", methods=['GET', 'POST'])
def admin_login():
    """Special admin login route for local development"""
    if current_user.is_authenticated:
        if isinstance(current_user, Lead) and current_user.is_client:
            return redirect(url_for('client.dashboard'))
        return redirect(url_for('main.home'))

    form = Login()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if not user.is_user_active:
                flash("User has not been granted access to the system! Please contact the system administrator", 'danger')
            elif not bcrypt.check_password_hash(user.password, form.password.data):
                flash('Invalid Password!', 'danger')
            else:
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                if next_page:
                    # Make sure next_page URL is safe (starts with /)
                    if not next_page.startswith('/'):
                        next_page = None
                return redirect(next_page or url_for('main.home'))
        else:
            flash('Invalid email or password', 'danger')

    # Renders the admin login template without redirection
    return render_template("login.html", title="TradingCRM - Admin Login", form=form)
