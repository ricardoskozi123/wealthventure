from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from omcrm.activities.models import Activity
from omcrm.leads.models import Lead
from omcrm.users.models import User
from omcrm.rbac import is_admin, check_access

activities = Blueprint('activities', __name__)


@activities.route("/admin/activities")
@login_required
@check_access('activities', 'view')
def activities_list():
    """Display all activities for admins"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    action_type = request.args.get('action_type', None)
    
    # Build query with optional filtering
    query = Activity.query
    if action_type:
        query = query.filter_by(action_type=action_type)
    
    # Get all activities
    activities_pagination = query.order_by(Activity.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    # Get related users and leads for display - improved data fetching
    user_ids = [a.user_id for a in activities_pagination.items if a.user_id is not None]
    lead_ids = [a.lead_id for a in activities_pagination.items if a.lead_id is not None]
    
    # Fetch users and leads more robustly
    users = {}
    if user_ids:
        users = {user.id: user for user in User.query.filter(User.id.in_(user_ids)).all()}
    
    leads = {}
    if lead_ids:
        leads = {lead.id: lead for lead in Lead.query.filter(Lead.id.in_(lead_ids)).all()}
    
    # Debug info for missing users
    missing_users = [uid for uid in user_ids if uid not in users]
    if missing_users:
        print(f"⚠️  Missing users: {missing_users}")
    
    return render_template("admin/activities.html",
                          title="Activity Log",
                          activities=activities_pagination,
                          users=users,
                          leads=leads)


@activities.route("/admin/activities/lead/<int:lead_id>")
@login_required
def lead_activities(lead_id):
    """Display activities for a specific lead"""
    lead = Lead.query.get_or_404(lead_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get activities for this lead
    activities_pagination = Activity.query.filter_by(lead_id=lead_id).order_by(
        Activity.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get related users for display
    user_ids = [a.user_id for a in activities_pagination.items if a.user_id is not None]
    users = {user.id: user for user in User.query.filter(User.id.in_(user_ids)).all()}
    
    return render_template("admin/lead_activities.html",
                          title=f"Activities for {lead.first_name} {lead.last_name}",
                          lead=lead,
                          activities=activities_pagination,
                          users=users)


@activities.route("/admin/activities/user/<int:user_id>")
@login_required
@check_access('activities', 'view')
def user_activities(user_id):
    """Display activities performed by a specific user"""
    user = User.query.get_or_404(user_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get activities for this user
    activities_pagination = Activity.query.filter_by(user_id=user_id).order_by(
        Activity.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get related leads for display
    lead_ids = [a.lead_id for a in activities_pagination.items if a.lead_id is not None]
    leads = {lead.id: lead for lead in Lead.query.filter(Lead.id.in_(lead_ids)).all()}
    
    return render_template("admin/user_activities.html",
                          title=f"Activities by {user.username}",
                          user=user,
                          activities=activities_pagination,
                          leads=leads)


@activities.route("/api/recent_activities")
@login_required
def recent_activities_api():
    """API endpoint to get recent activities, for AJAX calls"""
    limit = request.args.get('limit', 10, type=int)
    lead_id = request.args.get('lead_id', None, type=int)
    user_id = request.args.get('user_id', None, type=int)
    
    query = Activity.query
    
    if lead_id:
        query = query.filter_by(lead_id=lead_id)
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    # Regular users can only see activities related to their assigned leads
    if not current_user.is_admin:
        # Get leads owned by current user instead of assigned to
        owned_leads = [lead.id for lead in Lead.query.filter_by(owner_id=current_user.id).all()]
        if lead_id and lead_id not in owned_leads:
            return jsonify({'error': 'Access denied'}), 403
        
        if not lead_id:
            query = query.filter(Activity.lead_id.in_(owned_leads))
    
    activities = query.order_by(Activity.timestamp.desc()).limit(limit).all()
    
    # Prepare data for JSON response
    result = []
    for activity in activities:
        user = User.query.get(activity.user_id) if activity.user_id else None
        lead = Lead.query.get(activity.lead_id) if activity.lead_id else None
        
        activity_data = {
            'id': activity.id,
            'action_type': activity.action_type,
            'description': activity.description,
            'timestamp': activity.timestamp.isoformat(),
            'target_type': activity.target_type,
            'target_id': activity.target_id,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}"
            } if user else None,
            'lead': {
                'id': lead.id,
                'full_name': f"{lead.first_name} {lead.last_name}"
            } if lead else None
        }
        
        result.append(activity_data)
    
    return jsonify(result)
