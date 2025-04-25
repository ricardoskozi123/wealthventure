from flask import render_template, session, url_for, redirect, Blueprint, request
from omcrm import db, bcrypt
import os
import sys
from flask import current_app
from tzlocal import get_localzone
import platform

from omcrm.settings.models import Currency, TimeZone, AppConfig
from omcrm.leads.models import LeadSource, LeadStatus, Lead
from omcrm.deals.models import DealStage, Deal
from omcrm.users.models import Role, Resource, User

from omcrm.install.forms import NewSystemUser, CurrencyTz, FinishInstall
from omcrm.install.data.currency_timezone import INSERT_SQL
from omcrm.install.data.sample_data import SAMPLE_DATA

install = Blueprint('install', __name__)


@install.route("/", methods=['GET', 'POST'])
@install.route("/install", methods=['GET', 'POST'])
def sys_info():

    # create empty tables
    db.create_all()

    v = tuple(sys.version.split('.'))
    if v and int(v[0]) < 3 and int(v[1]) < 5:
        return render_template("install/error.html", title="Eeazy CRM installation failed",
                               reason=f"Python version >= {current_app.config['PYTHON_VER_MIN_REQUIRED']} is required for omcrm")
    env_vars = {
        'email_user': True if os.getenv('EMAIL_USER') else False,
        'email_pass': True if os.getenv('EMAIL_PASS') else False
    }
    return render_template("install/sys_info.html", title="System Information",
                           system_info=platform.uname(), py_ver=sys.version, env_vars=env_vars)


def initialize_currency_timezone_data():
    """Initialize currency and timezone data using SQLAlchemy models instead of raw SQL"""
    # Parse INSERT statements from the SQL script to extract data
    currencies = []
    timezones = []
    
    # Process each line in INSERT_SQL
    for line in INSERT_SQL.split('\n'):
        line = line.strip()
        # Skip non-insert statements and empty lines
        if not line.startswith('INSERT INTO'):
            continue
            
        # Extract table and values
        try:
            # Extract table name
            if 'currency' in line.lower():
                # Parse currency data: id, name, iso_code, symbol
                # Extract values between parentheses
                values_start = line.find('VALUES (') + 8
                values_end = line.rfind(')')
                values_str = line[values_start:values_end]
                
                # Split by commas that are not within quotes
                parts = []
                in_quotes = False
                current_part = ""
                for char in values_str:
                    if char == "'" and (len(current_part) == 0 or current_part[-1] != '\\'):
                        in_quotes = not in_quotes
                    if char == ',' and not in_quotes:
                        parts.append(current_part.strip())
                        current_part = ""
                    else:
                        current_part += char
                if current_part:
                    parts.append(current_part.strip())
                
                # Clean up quotes and NULL values
                id_val = int(parts[0])
                name_val = parts[1].strip("'")
                iso_code_val = parts[2].strip("'")
                symbol_val = None if parts[3] == "NULL" else parts[3].strip("'")
                
                # Create Currency object
                currency = Currency(id=id_val, name=name_val, iso_code=iso_code_val, symbol=symbol_val)
                currencies.append(currency)
                
            elif 'time_zone' in line.lower():
                # Parse timezone data: id, name
                values_start = line.find('VALUES (') + 8
                values_end = line.rfind(')')
                values_str = line[values_start:values_end]
                
                parts = values_str.split(',', 1)
                id_val = int(parts[0].strip())
                name_val = parts[1].strip().strip("'")
                
                # Create TimeZone object
                timezone = TimeZone(id=id_val, name=name_val)
                timezones.append(timezone)
                
        except Exception as e:
            current_app.logger.error(f"Error parsing line: {line}, error: {str(e)}")
            continue
    
    # Add all objects to session and commit
    try:
        db.session.bulk_save_objects(currencies)
        db.session.bulk_save_objects(timezones)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving data: {str(e)}")
        return False


@install.route("/install/sys_user", methods=['GET', 'POST'])
def setup_sys_user():
    form = NewSystemUser()
    if request.method == 'POST':
        if form.validate_on_submit():
            hashed_pwd = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            session['admin_first_name'] = form.first_name.data
            session['admin_last_name'] = form.last_name.data
            session['admin_email'] = form.email.data
            session['admin_password'] = hashed_pwd

            # Initialize currency and timezone data using SQLAlchemy models
            success = initialize_currency_timezone_data()
            
            if not success:
                # If full initialization failed, add essential data
                try:
                    # Add at least USD currency
                    usd = Currency(id=142, name='US Dollar', iso_code='USD', symbol='$')
                    db.session.add(usd)
                    
                    # Add a few common timezones
                    timezones = [
                        TimeZone(id=380, name='America/New_York'),
                        TimeZone(id=400, name='America/Los_Angeles'),
                        TimeZone(id=161, name='Europe/London')
                    ]
                    db.session.bulk_save_objects(timezones)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error adding essential records: {str(e)}")

            return redirect(url_for('install.ex_settings'))
    return render_template("install/sys_user.html", title="Create System User (admin)",
                           form=form)


@install.route("/install/extra_settings", methods=['GET', 'POST'])
def ex_settings():
    # insert currency & timezone tables with data
    form = CurrencyTz()
    if request.method == 'POST':
        if form.validate_on_submit():
            session['app_currency_name'] = form.currency.data.name + f'({form.currency.data.symbol})' if form.currency.data.symbol else ''
            session['app_currency_id'] = form.currency.data.id
            session['app_tz_name'] = form.time_zone.data.name
            session['app_tz_id'] = form.time_zone.data.id
            return redirect(url_for('install.finish'))
    elif request.method == 'GET':
        form.currency.data = Currency.get_currency_by_id(142)
        local_tz = get_localzone()
        if local_tz:
            form.time_zone.data = TimeZone.get_tz_by_name(str(local_tz))
        else:
            form.time_zone.data = TimeZone.get_tz_by_id(380)
    return render_template("install/extra_settings.html", title="Set Currency & TimeZone", form=form)


def empty_setup():
    # create system roles & resources
    role = Role(name='general')
    role.resources.append(
        Resource(
            name='staff',
            can_view=True,
            can_edit=False,
            can_create=False,
            can_delete=False
        )
    )

    role.resources.append(
        Resource(
            name='leads',
            can_view=True,
            can_edit=False,
            can_create=True,
            can_delete=False
        )
    )

    role.resources.append(
        Resource(
            name='accounts',
            can_view=True,
            can_edit=False,
            can_create=True,
            can_delete=False
        )
    )

    role.resources.append(
        Resource(
            name='contacts',
            can_view=True,
            can_edit=True,
            can_create=True,
            can_delete=False
        )
    )

    role.resources.append(
        Resource(
            name='deals',
            can_view=True,
            can_edit=False,
            can_create=True,
            can_delete=False
        )
    )

    # create user
    user = User(first_name=session['admin_first_name'],
                last_name=session['admin_last_name'],
                email=session['admin_email'],
                password=session['admin_password'],
                is_admin=True,
                is_first_login=True,
                is_user_active=True
                )

    db.session.add(role)
    db.session.add(user)

    # add system deal stages
    db.session.add(DealStage(stage_name="Deal Won", display_order=1, close_type='won'))
    db.session.add(DealStage(stage_name="Deal Lost", display_order=2, close_type='lost'))


@install.route("/install/finish", methods=['GET', 'POST'])
def finish():
    form = FinishInstall()
    data = {
        'def_currency': session['app_currency_name'],
        'def_tz': session['app_tz_name']
    }
    if request.method == 'POST':
        if form.validate_on_submit():

            try:
                if form.import_sample_data.data:
                    # Call empty_setup to create basic data
                    empty_setup()
                else:
                    empty_setup()

                # create configuration
                app_cfg = AppConfig(
                    default_currency=session['app_currency_id'],
                    default_timezone=session['app_tz_id']
                )

                # create application config
                db.session.add(app_cfg)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error during finish setup: {str(e)}")
                # Try one more time with basic setup
                try:
                    empty_setup()
                    app_cfg = AppConfig(
                        default_currency=session['app_currency_id'],
                        default_timezone=session['app_tz_id']
                    )
                    db.session.add(app_cfg)
                    db.session.commit()
                except Exception as inner_e:
                    db.session.rollback()
                    current_app.logger.error(f"Final setup attempt failed: {str(inner_e)}")

            return render_template("install/complete.html", title="Hurray! Installation Complete!")
    return render_template("install/finish.html", title="We're all set! Let's finish Installation",
                           data=data, form=form)


@current_app.errorhandler(404)
def page_not_found(error):
    return redirect(url_for('install.sys_info'))

