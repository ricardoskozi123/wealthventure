from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FieldList, FormField, HiddenField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

from .models import User, Role, Resource, Team


class Register(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name',
                            validators=[DataRequired(message='Please enter the last name'), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(
                            message='Email address is mandatory'),
                            Email(message='Please enter a valid email address e.g. abc@yourcompany.com')])
    password = PasswordField('Password',
                             validators=[DataRequired(message='Password is mandatory')])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(
                                         message='Confirm Password is mandatory'),
                                         EqualTo('password', 'Passwords do not match')])
    is_admin = BooleanField('Set Admin')
    submit = SubmitField('Next: Setup Company Details')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists! Please choose a different one')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already exists! Please choose a different one')


class Login(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateProfile(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name',
                            validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    picture = FileField('Update Avatar', validators=[FileAllowed(['jpg', 'jpeg', 'png'])])
    submit = SubmitField('Update')


class ResourceForm(FlaskForm):
    resource_id = HiddenField('Resource ID')
    name = StringField('Resource Name',
                       validators=[DataRequired(message='Resource name is mandatory')])
    can_view = BooleanField('View')
    can_create = BooleanField('Create')
    can_edit = BooleanField('Update')
    can_delete = BooleanField('Delete')
    can_impersonate = BooleanField('Impersonate')
    # 🔧 Manager-level permissions
    can_view_all_clients = BooleanField('View All Clients (Manager)')
    can_view_all_leads = BooleanField('View All Leads (Manager)')
    
    # 🔧 NEW: Sidebar Navigation Permissions
    can_view_dashboard = BooleanField('Dashboard')
    can_view_leads = BooleanField('Leads')
    can_view_pipeline = BooleanField('Pipeline')
    can_view_activities = BooleanField('Activities')
    can_view_tasks = BooleanField('Tasks')
    can_view_lead_sources = BooleanField('Lead Sources')
    can_view_client_statuses = BooleanField('Client Statuses')
    can_view_trading_instruments = BooleanField('Trading Instruments')
    can_view_clients_page = BooleanField('Clients')
    can_view_reports = BooleanField('Reports')
    can_view_pipeline_stages = BooleanField('Pipeline Stages')
    can_view_transactions = BooleanField('Transactions')
    can_view_settings = BooleanField('Settings')


class NewRoleForm(FlaskForm):
    name = StringField('Role Name',
                       validators=[DataRequired(message='Role name is mandatory')])
    permissions = FieldList(FormField(ResourceForm), min_entries=0)
    submit = SubmitField('Update Role')

    def validate_name(self, name):
        if name.data == 'admin':
            raise ValidationError(f'Role name \'{name.data}\' is reserved by the system! Please choose a different name')
        role = Role.get_by_name(name=name.data)
        if role:
            raise ValidationError(f'The role {role.name} already exists! Please choose a different name')


class UpdateRoleForm(FlaskForm):
    name = StringField('Role Name',
                       validators=[DataRequired(message='Role name is mandatory')])
    permissions = FieldList(FormField(ResourceForm), min_entries=0)
    submit = SubmitField('Update Role')


class UpdateUser(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name',
                            validators=[DataRequired(message='Please enter the last name'), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(
                            message='Email address is mandatory'),
                            Email(message='Please enter a valid email address e.g. abc@yourcompany.com')])
    password = PasswordField('Password', description='Leave empty to keep current password or set a new password')
    picture = FileField('Update Avatar',
                        validators=[FileAllowed(['jpg', 'jpeg', 'png'])])
    role = QuerySelectField(query_factory=lambda: Role.query, get_pk=lambda a: a.id,
                            get_label='name', allow_blank=False,
                            validators=[DataRequired(message='Role assignment is mandatory')])
    is_admin = BooleanField('Set Admin')
    is_user_active = BooleanField('Set Active')
    is_first_login = BooleanField('User Should Change Password on Login')
    permissions = FieldList(FormField(ResourceForm), min_entries=0)
    submit = SubmitField('Update Staff Member')

    # def validate_email(self, email):
    #     user = User.query.filter_by(email=email.data).first()
    #     if user:
    #         raise ValidationError(f'Email {email.data} already exists! Please choose a different one')


class NewTeamForm(FlaskForm):
    name = StringField('Team Name', validators=[DataRequired('Team name is mandatory')])
    description = TextAreaField('Description')
    leader = QuerySelectField('Team Leader', 
                            query_factory=lambda: User.query.filter_by(is_user_active=True), 
                            get_pk=lambda a: a.id,
                            get_label=User.get_label, 
                            allow_blank=False,
                            validators=[DataRequired(message='Team leader is mandatory')])
    members = QuerySelectMultipleField('Team Members',
                                query_factory=lambda: User.query.filter_by(is_user_active=True), 
                                get_pk=lambda a: a.id,
                                get_label=User.get_label, 
                                allow_blank=True)
    submit = SubmitField('Create Team')


class UpdateTeamForm(FlaskForm):
    name = StringField('Team Name', validators=[DataRequired('Team name is mandatory')])
    description = TextAreaField('Description')
    leader = QuerySelectField('Team Leader', 
                            query_factory=lambda: User.query.filter_by(is_user_active=True), 
                            get_pk=lambda a: a.id,
                            get_label=User.get_label, 
                            allow_blank=False,
                            validators=[DataRequired(message='Team leader is mandatory')])
    members = QuerySelectMultipleField('Team Members',
                                query_factory=lambda: User.query.filter_by(is_user_active=True), 
                                get_pk=lambda a: a.id,
                                get_label=User.get_label, 
                                allow_blank=True)
    submit = SubmitField('Update Team')


class PasswordResetRequestForm(FlaskForm):
    """Form for requesting a password reset"""
    email = StringField('Email Address',
                        validators=[
                            DataRequired(message="Email address is required."),
                            Email(message="Please enter a valid email address."),
                            Length(max=120, message="Email address must be less than 120 characters.")
                        ],
                        render_kw={
                            "placeholder": "Enter your email address",
                            "class": "form-control",
                            "autocomplete": "email"
                        })
    submit = SubmitField('Send Reset Link', render_kw={"class": "btn btn-primary"})


class PasswordResetForm(FlaskForm):
    """Form for resetting password with a valid token"""
    password = PasswordField('New Password',
                            validators=[
                                DataRequired(message="Password is required."),
                                Length(min=8, max=128, message="Password must be between 8 and 128 characters."),
                                Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
                                      message="Password must contain at least one lowercase letter, one uppercase letter, and one number.")
                            ],
                            render_kw={
                                "placeholder": "Enter your new password",
                                "class": "form-control",
                                "autocomplete": "new-password"
                            })
    
    confirm_password = PasswordField('Confirm New Password',
                                   validators=[
                                       DataRequired(message="Please confirm your password."),
                                       EqualTo('password', message="Passwords must match.")
                                   ],
                                   render_kw={
                                       "placeholder": "Confirm your new password",
                                       "class": "form-control",
                                       "autocomplete": "new-password"
                                   })
    
    submit = SubmitField('Reset Password', render_kw={"class": "btn btn-success"})


class ChangePasswordForm(FlaskForm):
    """Form for changing password when logged in"""
    current_password = PasswordField('Current Password',
                                   validators=[DataRequired(message="Current password is required.")],
                                   render_kw={
                                       "placeholder": "Enter your current password",
                                       "class": "form-control",
                                       "autocomplete": "current-password"
                                   })
    
    new_password = PasswordField('New Password',
                               validators=[
                                   DataRequired(message="New password is required."),
                                   Length(min=8, max=128, message="Password must be between 8 and 128 characters."),
                                   Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
                                         message="Password must contain at least one lowercase letter, one uppercase letter, and one number.")
                               ],
                               render_kw={
                                   "placeholder": "Enter your new password",
                                   "class": "form-control",
                                   "autocomplete": "new-password"
                               })
    
    confirm_new_password = PasswordField('Confirm New Password',
                                       validators=[
                                           DataRequired(message="Please confirm your new password."),
                                           EqualTo('new_password', message="Passwords must match.")
                                       ],
                                       render_kw={
                                           "placeholder": "Confirm your new password",
                                           "class": "form-control",
                                           "autocomplete": "new-password"
                                       })
    
    submit = SubmitField('Change Password', render_kw={"class": "btn btn-primary"})
