from flask import Blueprint
from flask_login import current_user, login_required
from flask import render_template, flash, url_for, redirect, request
from sqlalchemy.exc import IntegrityError

from omcrm.users.forms import UpdateProfile, UpdateRoleForm, NewRoleForm, UpdateUser, ResourceForm, NewTeamForm, UpdateTeamForm
from omcrm.users.utils import upload_avatar
from omcrm.users.models import User, Role, Resource, Team

from omcrm import db, bcrypt
from omcrm.rbac import check_access, is_admin

settings = Blueprint('settings', __name__)


@settings.route("/settings/profile", methods=['GET', 'POST'])
@login_required
def settings_profile():
    form = UpdateProfile()
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.picture.data:
                picture_file = upload_avatar(current_user, form.picture.data)
                current_user.avatar = picture_file
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.email = form.email.data
            db.session.commit()
            flash('Your account information has been successfully updated', 'success')
            return redirect(url_for('settings.settings_profile'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    return render_template("settings/profile.html", title="My Profile", form=form)


# get all users except the current one (admin)
@settings.route("/settings/staff")
@login_required
@check_access("staff", "view")
def settings_staff_list():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    users = User.query\
        .filter(User.id != current_user.id)\
        .order_by(User.id.asc())\
        .paginate(per_page=per_page, page=page)
    return render_template("settings/staff_list.html", title="User Management", users=users)


@settings.route("/settings/staff/<int:user_id>")
@login_required
@check_access("staff", "view")
def settings_staff_view(user_id):
    user = User.query.filter(User.id == user_id).first()
    return render_template("settings/staff_view.html", title="View Staff", user=user)


@settings.route("/settings/staff/edit/<int:user_id>", methods=['GET', 'POST'])
@login_required
@check_access("staff", "update")
def settings_staff_update(user_id):
    form = UpdateUser()
    user = User.query.filter(User.id == user_id).first()

    acl = Role.query\
        .with_entities(Role.id,
                       Resource.id,
                       Resource.name,
                       Resource.can_view,
                       Resource.can_create,
                       Resource.can_edit,
                       Resource.can_delete)\
        .filter_by(id=user.role_id)\
        .join(Role.resources)\
        .order_by(Resource.id.asc())\
        .all()

    if request.method == 'POST':
        if form.validate_on_submit():
            if form.picture.data:
                picture_file = upload_avatar(user, form.picture.data)
                user.avatar = picture_file
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.email = form.email.data
            user.role = form.role.data
            user.is_user_active = form.is_user_active.data
            user.is_first_login = form.is_first_login.data
            
            # Update password if provided
            if form.password.data:
                hashed_pwd = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
                user.password = hashed_pwd

            for permission in form.permissions:
                resource = Resource.query.filter_by(id=permission.resource_id.data).first()
                resource.can_view = permission.can_view.data
                resource.can_create = permission.can_create.data
                resource.can_edit = permission.can_edit.data
                resource.can_delete = permission.can_delete.data
                # Handle impersonate permission if it exists
                if hasattr(permission, 'can_impersonate'):
                    resource.can_impersonate = permission.can_impersonate.data
                # 🔧 Handle manager-level permissions
                if hasattr(permission, 'can_view_all_clients'):
                    resource.can_view_all_clients = permission.can_view_all_clients.data
                if hasattr(permission, 'can_view_all_leads'):
                    resource.can_view_all_leads = permission.can_view_all_leads.data
                
                # 🔧 NEW: Handle sidebar navigation permissions
                if hasattr(permission, 'can_view_dashboard'):
                    resource.can_view_dashboard = permission.can_view_dashboard.data
                if hasattr(permission, 'can_view_leads'):
                    resource.can_view_leads = permission.can_view_leads.data
                if hasattr(permission, 'can_view_pipeline'):
                    resource.can_view_pipeline = permission.can_view_pipeline.data
                if hasattr(permission, 'can_view_activities'):
                    resource.can_view_activities = permission.can_view_activities.data
                if hasattr(permission, 'can_view_tasks'):
                    resource.can_view_tasks = permission.can_view_tasks.data
                if hasattr(permission, 'can_view_lead_sources'):
                    resource.can_view_lead_sources = permission.can_view_lead_sources.data
                if hasattr(permission, 'can_view_client_statuses'):
                    resource.can_view_client_statuses = permission.can_view_client_statuses.data
                if hasattr(permission, 'can_view_trading_instruments'):
                    resource.can_view_trading_instruments = permission.can_view_trading_instruments.data
                if hasattr(permission, 'can_view_clients_page'):
                    resource.can_view_clients_page = permission.can_view_clients_page.data
                if hasattr(permission, 'can_view_reports'):
                    resource.can_view_reports = permission.can_view_reports.data
                if hasattr(permission, 'can_view_pipeline_stages'):
                    resource.can_view_pipeline_stages = permission.can_view_pipeline_stages.data
                if hasattr(permission, 'can_view_transactions'):
                    resource.can_view_transactions = permission.can_view_transactions.data
                if hasattr(permission, 'can_view_settings'):
                    resource.can_view_settings = permission.can_view_settings.data

            try:
                db.session.commit()
                flash('Staff member information has been successfully updated', 'success')
                return redirect(url_for('settings.settings_staff_view', user_id=user.id))
            except IntegrityError:
                db.session.rollback()
                form.email.errors = [f'Email \'{form.email.data}\' already exists!']
                flash('User update failed! Form has errors', 'danger')

        else:
            print(form.errors)
            flash('User update failed! Form has errors', 'danger')
    elif request.method == 'GET':
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.email.data = user.email
        if user.avatar:
            form.picture.data = user.avatar
        form.role.data = user.role
        form.is_user_active.data = user.is_user_active
        form.is_first_login.data = user.is_first_login

        for l in acl:
            resource_form = ResourceForm()
            resource_form.resource_id = l.id
            resource_form.name = l.name
            resource_form.can_view = l.can_view
            resource_form.can_create = l.can_create
            resource_form.can_edit = l.can_edit
            resource_form.can_delete = l.can_delete
            form.permissions.append_entry(resource_form)

    return render_template("settings/staff_update.html", title="Update Staff", form=form)


@settings.route("/settings/staff/new", methods=['GET', 'POST'])
@login_required
@check_access("staff", "create")
def settings_staff_new():
    form = UpdateUser()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User()
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.email = form.email.data
            
            # Set password: use provided password or default '123'
            password_to_use = form.password.data if form.password.data else '123'
            hashed_pwd = bcrypt.generate_password_hash(password_to_use).decode('utf-8')
            user.password = hashed_pwd
            
            if form.picture.data:
                picture_file = upload_avatar(user, form.picture.data)
                user.avatar = picture_file
            user.role = form.role.data
            user.is_user_active = form.is_user_active.data
            user.is_first_login = form.is_first_login.data

            db.session.add(user)
            db.session.commit()
            flash('User has been successfully created!', 'success')
            return redirect(url_for('settings.settings_staff_list'))
        else:
            print(form.errors)
            flash(f'Failed to register user!', 'danger')
    return render_template("settings/new_user.html", title="New Staff Member", form=form)


@settings.route("/settings/staff/del/<int:user_id>")
@login_required
@check_access("staff", "remove")
def settings_staff_remove(user_id):
    user_to_delete = User.query.filter(User.id == user_id).first()
    
    if not user_to_delete:
        flash('User not found!', 'danger')
        return redirect(url_for('settings.settings_staff_list'))
    
    # Prevent deletion of current user
    if user_to_delete.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('settings.settings_staff_list'))
    
    # Store user name for success message
    user_name = f"{user_to_delete.first_name} {user_to_delete.last_name}"
    
    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'User "{user_name}" has been successfully deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('settings.settings_staff_list'))


@settings.route("/settings/staff/del/<email>", methods=['DELETE'])
@login_required
@check_access("staff", "remove")
def settings_staff_remove_by_email(email):
    User.query.filter(User.email == email).delete()
    db.session.commit()
    flash('User removed successfully!', 'success')
    return redirect(url_for('main.home'))


@settings.route("/settings/email", methods=['GET', 'POST'])
@login_required
def email_settings():
    flash('Email settings saved', 'success')
    return redirect(url_for('main.home'))


@settings.route("/settings/roles")
@login_required
@check_access('staff', 'view')
def settings_roles_view():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    roles = Role.query\
        .filter(Role.name != 'admin')\
        .order_by(Role.id.asc())\
        .paginate(per_page=per_page, page=page)
    return render_template("settings/roles_list.html", title="Roles & Permissions", roles=roles)


@settings.route("/settings/role/new", methods=['GET', 'POST'])
@login_required
@check_access('staff', 'create')
def settings_roles_new():
    form = NewRoleForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            role = Role()
            role.name = form.name.data

            for permission in form.permissions:
                resource = Resource()
                resource.name = permission.form.name.data
                resource.can_view = permission.form.can_view.data
                resource.can_create = permission.form.can_create.data
                resource.can_edit = permission.form.can_edit.data
                resource.can_delete = permission.form.can_delete.data
                resource.can_impersonate = permission.form.can_impersonate.data if hasattr(permission.form, 'can_impersonate') else False
                # 🔧 Handle manager-level permissions
                resource.can_view_all_clients = permission.form.can_view_all_clients.data if hasattr(permission.form, 'can_view_all_clients') else False
                resource.can_view_all_leads = permission.form.can_view_all_leads.data if hasattr(permission.form, 'can_view_all_leads') else False
                
                # 🔧 NEW: Handle sidebar navigation permissions
                resource.can_view_dashboard = permission.form.can_view_dashboard.data if hasattr(permission.form, 'can_view_dashboard') else True
                resource.can_view_leads = permission.form.can_view_leads.data if hasattr(permission.form, 'can_view_leads') else True
                resource.can_view_pipeline = permission.form.can_view_pipeline.data if hasattr(permission.form, 'can_view_pipeline') else True
                resource.can_view_activities = permission.form.can_view_activities.data if hasattr(permission.form, 'can_view_activities') else True
                resource.can_view_tasks = permission.form.can_view_tasks.data if hasattr(permission.form, 'can_view_tasks') else True
                resource.can_view_lead_sources = permission.form.can_view_lead_sources.data if hasattr(permission.form, 'can_view_lead_sources') else False
                resource.can_view_client_statuses = permission.form.can_view_client_statuses.data if hasattr(permission.form, 'can_view_client_statuses') else False
                resource.can_view_trading_instruments = permission.form.can_view_trading_instruments.data if hasattr(permission.form, 'can_view_trading_instruments') else False
                resource.can_view_clients_page = permission.form.can_view_clients_page.data if hasattr(permission.form, 'can_view_clients_page') else True
                resource.can_view_reports = permission.form.can_view_reports.data if hasattr(permission.form, 'can_view_reports') else True
                resource.can_view_pipeline_stages = permission.form.can_view_pipeline_stages.data if hasattr(permission.form, 'can_view_pipeline_stages') else False
                resource.can_view_transactions = permission.form.can_view_transactions.data if hasattr(permission.form, 'can_view_transactions') else False
                resource.can_view_settings = permission.form.can_view_settings.data if hasattr(permission.form, 'can_view_settings') else True
                
                role.resources.append(resource)

            db.session.add(role)
            db.session.commit()

            flash('Role has been successfully created!', 'success')
            return redirect(url_for('settings.settings_roles_view'))
        else:
            flash('Failed to create new role!', 'danger')
    elif request.method == 'GET':
        resources = [
            ResourceForm(name='staff', can_view=False, can_create=False, can_edit=False, can_delete=False,
                        # Sidebar permissions - default values
                        can_view_dashboard=True, can_view_leads=True, can_view_pipeline=True,
                        can_view_activities=True, can_view_tasks=True, can_view_lead_sources=False,
                        can_view_client_statuses=False, can_view_trading_instruments=False,
                        can_view_clients_page=True, can_view_reports=True, can_view_pipeline_stages=False,
                        can_view_transactions=False, can_view_settings=True),
            ResourceForm(name='leads', can_view=True, can_create=True, can_edit=True, can_delete=True,
                        # Sidebar permissions - default values
                        can_view_dashboard=True, can_view_leads=True, can_view_pipeline=True,
                        can_view_activities=True, can_view_tasks=True, can_view_lead_sources=False,
                        can_view_client_statuses=False, can_view_trading_instruments=False,
                        can_view_clients_page=True, can_view_reports=True, can_view_pipeline_stages=False,
                        can_view_transactions=False, can_view_settings=True),
            ResourceForm(name='deals', can_view=True, can_create=True, can_edit=True, can_delete=True,
                        # Sidebar permissions - default values
                        can_view_dashboard=True, can_view_leads=True, can_view_pipeline=True,
                        can_view_activities=True, can_view_tasks=True, can_view_lead_sources=False,
                        can_view_client_statuses=False, can_view_trading_instruments=False,
                        can_view_clients_page=True, can_view_reports=True, can_view_pipeline_stages=False,
                        can_view_transactions=False, can_view_settings=True),
            ResourceForm(name='clients', can_view=True, can_create=True, can_edit=True, can_delete=True,
                        # Sidebar permissions - default values
                        can_view_dashboard=True, can_view_leads=True, can_view_pipeline=True,
                        can_view_activities=True, can_view_tasks=True, can_view_lead_sources=False,
                        can_view_client_statuses=False, can_view_trading_instruments=False,
                        can_view_clients_page=True, can_view_reports=True, can_view_pipeline_stages=False,
                        can_view_transactions=False, can_view_settings=True),
            ResourceForm(name='activities', can_view=True, can_create=True, can_edit=True, can_delete=True,
                        # Sidebar permissions - default values
                        can_view_dashboard=True, can_view_leads=True, can_view_pipeline=True,
                        can_view_activities=True, can_view_tasks=True, can_view_lead_sources=False,
                        can_view_client_statuses=False, can_view_trading_instruments=False,
                        can_view_clients_page=True, can_view_reports=True, can_view_pipeline_stages=False,
                        can_view_transactions=False, can_view_settings=True),
            ResourceForm(name='tasks', can_view=True, can_create=True, can_edit=True, can_delete=True,
                        # Sidebar permissions - default values
                        can_view_dashboard=True, can_view_leads=True, can_view_pipeline=True,
                        can_view_activities=True, can_view_tasks=True, can_view_lead_sources=False,
                        can_view_client_statuses=False, can_view_trading_instruments=False,
                        can_view_clients_page=True, can_view_reports=True, can_view_pipeline_stages=False,
                        can_view_transactions=False, can_view_settings=True),
            ResourceForm(name='reports', can_view=True, can_create=True, can_edit=True, can_delete=True,
                        # Sidebar permissions - default values
                        can_view_dashboard=True, can_view_leads=True, can_view_pipeline=True,
                        can_view_activities=True, can_view_tasks=True, can_view_lead_sources=False,
                        can_view_client_statuses=False, can_view_trading_instruments=False,
                        can_view_clients_page=True, can_view_reports=True, can_view_pipeline_stages=False,
                        can_view_transactions=False, can_view_settings=True),
            ResourceForm(name='transactions', can_view=True, can_create=True, can_edit=True, can_delete=True,
                        # Sidebar permissions - default values
                        can_view_dashboard=True, can_view_leads=True, can_view_pipeline=True,
                        can_view_activities=True, can_view_tasks=True, can_view_lead_sources=False,
                        can_view_client_statuses=False, can_view_trading_instruments=False,
                        can_view_clients_page=True, can_view_reports=True, can_view_pipeline_stages=False,
                        can_view_transactions=False, can_view_settings=True),
            ResourceForm(name='instruments', can_view=True, can_create=True, can_edit=True, can_delete=True,
                        # Sidebar permissions - default values
                        can_view_dashboard=True, can_view_leads=True, can_view_pipeline=True,
                        can_view_activities=True, can_view_tasks=True, can_view_lead_sources=False,
                        can_view_client_statuses=False, can_view_trading_instruments=False,
                        can_view_clients_page=True, can_view_reports=True, can_view_pipeline_stages=False,
                        can_view_transactions=False, can_view_settings=True)
        ]

        for resource in resources:
            form.permissions.append_entry(resource.data)
    return render_template("settings/role_new.html", title="Create New Role", form=form)


@settings.route("/settings/role/edit/<role_id>", methods=['GET', 'POST'])
@login_required
@check_access('staff', 'edit')
def settings_roles_update(role_id):
    role = Role.query.filter_by(id=role_id).first()
    form = UpdateRoleForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            role.name = form.name.data.lower()
            role.set_permissions(form.permissions)

            try:
                db.session.commit()
                flash('Role successfully created!', 'success')
                return redirect(url_for('settings.settings_roles_view'))
            except IntegrityError:
                db.session.rollback()
                if form.name.data == 'admin':
                    form.name.errors = [f'The role \'{form.name.data}\' is reserved by the system ! Please choose a different name']
                else:
                    form.name.errors = [f'The role \'{form.name.data}\' already exists ! Please choose a different name']
                flash('Failed to create new role!', 'danger')

        else:
            flash('Failed to create new role!', 'danger')
    elif request.method == 'GET':
        form.name.data = role.name
        for resource in role.resources:
            resource_form = ResourceForm()
            resource_form.name = resource.name
            resource_form.can_view = resource.can_view
            resource_form.can_create = resource.can_create
            resource_form.can_edit = resource.can_edit
            resource_form.can_delete = resource.can_delete
            
            # 🔧 Load manager permissions
            if hasattr(resource, 'can_impersonate'):
                resource_form.can_impersonate = resource.can_impersonate
            if hasattr(resource, 'can_view_all_clients'):
                resource_form.can_view_all_clients = resource.can_view_all_clients
            if hasattr(resource, 'can_view_all_leads'):
                resource_form.can_view_all_leads = resource.can_view_all_leads
                
            # 🔧 Load sidebar navigation permissions
            if hasattr(resource, 'can_view_dashboard'):
                resource_form.can_view_dashboard = resource.can_view_dashboard
            if hasattr(resource, 'can_view_leads'):
                resource_form.can_view_leads = resource.can_view_leads
            if hasattr(resource, 'can_view_pipeline'):
                resource_form.can_view_pipeline = resource.can_view_pipeline
            if hasattr(resource, 'can_view_activities'):
                resource_form.can_view_activities = resource.can_view_activities
            if hasattr(resource, 'can_view_tasks'):
                resource_form.can_view_tasks = resource.can_view_tasks
            if hasattr(resource, 'can_view_lead_sources'):
                resource_form.can_view_lead_sources = resource.can_view_lead_sources
            if hasattr(resource, 'can_view_client_statuses'):
                resource_form.can_view_client_statuses = resource.can_view_client_statuses
            if hasattr(resource, 'can_view_trading_instruments'):
                resource_form.can_view_trading_instruments = resource.can_view_trading_instruments
            if hasattr(resource, 'can_view_clients_page'):
                resource_form.can_view_clients_page = resource.can_view_clients_page
            if hasattr(resource, 'can_view_reports'):
                resource_form.can_view_reports = resource.can_view_reports
            if hasattr(resource, 'can_view_pipeline_stages'):
                resource_form.can_view_pipeline_stages = resource.can_view_pipeline_stages
            if hasattr(resource, 'can_view_transactions'):
                resource_form.can_view_transactions = resource.can_view_transactions
            if hasattr(resource, 'can_view_settings'):
                resource_form.can_view_settings = resource.can_view_settings
                
            form.permissions.append_entry(resource_form)

    return render_template("settings/role_update.html", title="Update Role", form=form)


@settings.route("/settings/roles/del/<role_id>")
@login_required
@check_access('staff', 'delete')
def settings_roles_remove(role_id):
    role = Role.query.filter_by(id=role_id).first()
    db.session.delete(role)
    db.session.commit()
    return redirect(url_for('settings.settings_roles_view'))


# just for testing
@settings.route("/settings/resource/create")
@login_required
@check_access('staff', 'create')
def create_resource():
    roles = Role.query \
        .filter(Role.name != 'admin') \
        .order_by(Role.id.asc())

    resources = [
        'staff', 'leads', 'deals', 'clients', 
        'activities', 'tasks', 'reports', 
        'transactions', 'instruments'
    ]

    for role in roles:
        for res in resources:
            resource = Resource()
            resource.name = res
            resource.can_view = False
            resource.can_create = False
            resource.can_edit = False
            resource.can_delete = False
            role.resources.append(resource)

    db.session.add(role)
    db.session.commit()


@settings.route("/settings/teams")
@login_required
@check_access('staff', 'view')
def settings_teams_view():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    teams = Team.query\
        .order_by(Team.id.asc())\
        .paginate(per_page=per_page, page=page)
    return render_template("settings/teams_list.html", title="Team Management", teams=teams)


@settings.route("/settings/team/<int:team_id>")
@login_required
@check_access('staff', 'view')
def settings_team_view(team_id):
    team = Team.get_by_id(team_id)
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('settings.settings_teams_view'))
    
    return render_template("settings/team_view.html", title="Team Details", team=team)


@settings.route("/settings/team/new", methods=['GET', 'POST'])
@login_required
@check_access('staff', 'create')
def settings_team_new():
    form = NewTeamForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            team = Team(
                name=form.name.data,
                description=form.description.data,
                leader=form.leader.data
            )
            
            # Add selected members to the team
            if form.members.data:
                for member in form.members.data:
                    if member != form.leader.data:  # Avoid adding the leader as a regular member
                        member.team = team
            
            db.session.add(team)
            db.session.commit()
            
            flash('Team has been successfully created!', 'success')
            return redirect(url_for('settings.settings_teams_view'))
        else:
            flash('Failed to create new team!', 'danger')
    
    return render_template("settings/team_new.html", title="Create New Team", form=form)


@settings.route("/settings/team/edit/<int:team_id>", methods=['GET', 'POST'])
@login_required
@check_access('staff', 'edit')
def settings_team_update(team_id):
    team = Team.get_by_id(team_id)
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('settings.settings_teams_view'))
    
    form = UpdateTeamForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            team.name = form.name.data
            team.description = form.description.data
            old_leader = team.leader
            team.leader = form.leader.data
            
            # Clear existing members
            for member in User.query.filter_by(team_id=team.id).all():
                member.team_id = None
            
            # Add selected members
            if form.members.data:
                for member in form.members.data:
                    if member != form.leader.data:  # Avoid adding the leader as a regular member
                        member.team = team
            
            db.session.commit()
            flash('Team has been successfully updated!', 'success')
            return redirect(url_for('settings.settings_team_view', team_id=team.id))
        else:
            flash('Failed to update team!', 'danger')
    elif request.method == 'GET':
        form.name.data = team.name
        form.description.data = team.description
        form.leader.data = team.leader
        form.members.data = team.members
    
    return render_template("settings/team_update.html", title="Update Team", form=form, team=team)


@settings.route("/settings/team/del/<int:team_id>")
@login_required
@check_access('staff', 'delete')
def settings_team_remove(team_id):
    team = Team.get_by_id(team_id)
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('settings.settings_teams_view'))
    
    # Remove team association from members
    for member in team.members:
        member.team_id = None
    
    db.session.delete(team)
    db.session.commit()
    flash('Team has been successfully deleted!', 'success')
    return redirect(url_for('settings.settings_teams_view'))


