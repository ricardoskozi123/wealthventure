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
