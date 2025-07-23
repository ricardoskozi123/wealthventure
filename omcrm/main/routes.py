from flask import render_template, flash, url_for, redirect, Blueprint, current_app
from omcrm import db
from flask_login import login_required, current_user
from configparser import ConfigParser
from omcrm.tasks.models import Task
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
from omcrm.activities.models import Activity
from omcrm.leads.models import Lead, LeadSource
from omcrm.deals.models import Deal, DealStage
from omcrm.users.models import User
from omcrm.rbac import get_visible_deals_query

parser = ConfigParser()

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
def home():
    """
    Smart routing: Show landing page for visitors, dashboard for authenticated users
    """
    # If user is not authenticated, show the public landing page
    if not current_user.is_authenticated:
        return render_template("landing.html", 
                               title="Professional Trading Platform",
                               platform_name="OMCRM")
    
    # If user is a client, redirect to client dashboard
    if isinstance(current_user, Lead) and current_user.is_client:
        return redirect(url_for('client.dashboard'))
    
    # DISABLED FOR SINGLE SERVER DEPLOYMENT
    # Check if we're on the client domain but accessing admin pages
    # from flask import request
    # host = request.host.lower()
    # 
    # # Skip domain redirects for local development
    # if not host.startswith('crm.') and host not in ['127.0.0.1:5000', 'localhost:5000']:
    #     # Redirect to crm. subdomain for admin pages
    #     return redirect(f"http://crm.{host}{request.path}")
        
    # Get upcoming tasks for the user or all tasks if admin
    upcoming_date = datetime.utcnow() + timedelta(days=7)
    today = datetime.utcnow()
    
    if current_user.is_admin:
        tasks = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date <= upcoming_date
            )
        ).order_by(Task.due_date.asc()).limit(5).all()
    else:
        tasks = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date <= upcoming_date,
                or_(Task.creator_id == current_user.id, Task.assignee_id == current_user.id)
            )
        ).order_by(Task.due_date.asc()).limit(5).all()
    
    # Get all users needed for tasks
    user_ids = set()
    for task in tasks:
        if task.assignee_id:
            user_ids.add(task.assignee_id)
        if task.creator_id:
            user_ids.add(task.creator_id)
    
    users = {user.id: user for user in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
    
    # Count tasks due today
    today_end = datetime.utcnow().replace(hour=23, minute=59, second=59)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    
    if current_user.is_admin:
        tasks_due_today = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date >= today_start,
                Task.due_date <= today_end
            )
        ).count()
        
        high_priority_tasks = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.priority == 'high'
            )
        ).count()
        
        # Count total tasks for the user
        total_tasks = Task.query.filter(
            Task.status.in_(['pending', 'in_progress'])
        ).count()
    else:
        tasks_due_today = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date >= today_start,
                Task.due_date <= today_end,
                or_(Task.creator_id == current_user.id, Task.assignee_id == current_user.id)
            )
        ).count()
        
        high_priority_tasks = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.priority == 'high',
                or_(Task.creator_id == current_user.id, Task.assignee_id == current_user.id)
            )
        ).count()
        
        # Count total tasks for the user
        total_tasks = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                or_(Task.creator_id == current_user.id, Task.assignee_id == current_user.id)
            )
        ).count()
    
    # Get recent deals
    
    # Get total leads/clients for the user
    if current_user.is_admin:
        total_leads = Lead.query.filter_by(is_client=True).count()
    else:
        total_leads = Lead.query.filter_by(is_client=True, owner_id=current_user.id).count()
    
    # Get total deal value for the user
    deal_query = Deal.query
    if not current_user.is_admin:
        deal_query = deal_query.filter_by(owner_id=current_user.id)
    
    # Apply team-based permissions
    deal_query = get_visible_deals_query(deal_query)
    total_deal_value = sum([deal.expected_close_price for deal in deal_query.all()])
    
    # Calculate conversion rate (deals won / total deals)
    deal_stages = DealStage.query.all()
    won_stage_ids = [stage.id for stage in deal_stages if stage.close_type == 'won']
    
    if won_stage_ids:
        total_deals_query = Deal.query
        won_deals_query = Deal.query.filter(Deal.deal_stage_id.in_(won_stage_ids))
        
        if not current_user.is_admin:
            total_deals_query = total_deals_query.filter_by(owner_id=current_user.id)
            won_deals_query = won_deals_query.filter_by(owner_id=current_user.id)
        
        # Apply team-based permissions
        total_deals_query = get_visible_deals_query(total_deals_query)
        won_deals_query = get_visible_deals_query(won_deals_query)
        
        total_deals_count = total_deals_query.count()
        won_deals_count = won_deals_query.count()
        
        conversion_rate = round((won_deals_count / total_deals_count * 100) if total_deals_count > 0 else 0)
    else:
        conversion_rate = 0
    
    recent_deals = deal_query.order_by(Deal.date_created.desc()).limit(5).all()
    
    # Format total deal value
    formatted_deal_value = "${:,.2f}".format(total_deal_value)
    
    # Prepare data for Revenue Overview Chart (Deal Won values by month)
    import calendar
    
    current_year = datetime.utcnow().year
    months = list(calendar.month_abbr)[1:]  # Get month abbreviations (Jan, Feb, etc.)
    
    # Initialize monthly revenue data
    monthly_revenue = [0] * 12
    
    # Get all won deals for the current year
    if won_stage_ids:
        won_deals = Deal.query.filter(
            Deal.deal_stage_id.in_(won_stage_ids),
            Deal.date_created >= datetime(current_year, 1, 1),
            Deal.date_created <= datetime(current_year, 12, 31, 23, 59, 59)
        )
        
        if not current_user.is_admin:
            won_deals = won_deals.filter_by(owner_id=current_user.id)
            
        won_deals = get_visible_deals_query(won_deals).all()
        
        # Aggregate deal values by month
        for deal in won_deals:
            month_index = deal.date_created.month - 1  # Adjust for 0-based index
            monthly_revenue[month_index] += deal.expected_close_price
    
    # Prepare data for Leads by Source chart
    
    # Get all lead sources
    lead_sources = LeadSource.query.all()
    source_names = [source.source_name for source in lead_sources]
    
    # Count leads by source
    source_counts = []
    for source in lead_sources:
        query = Lead.query.filter_by(lead_source_id=source.id)
        if not current_user.is_admin:
            query = query.filter_by(owner_id=current_user.id)
        count = query.count()
        source_counts.append(count)
    
    # Generate random colors for chart
    import random
    
    def generate_rgba(opacity=0.8):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        return f'rgba({r}, {g}, {b}, {opacity})'
    
    # Generate colors for each source
    source_colors = [generate_rgba() for _ in source_names]
    
    # Get recent activities
    if current_user.is_admin:
        recent_activities = Activity.query.order_by(Activity.timestamp.desc()).limit(10).all()
    else:
        # Get activities for leads owned by the user
        owned_leads = [lead.id for lead in Lead.query.filter_by(owner_id=current_user.id).all()]
        recent_activities = Activity.query.filter(
            or_(
                Activity.user_id == current_user.id,
                Activity.lead_id.in_(owned_leads)
            )
        ).order_by(Activity.timestamp.desc()).limit(10).all()
    
    # Get user and lead data for activities
    activity_user_ids = [a.user_id for a in recent_activities if a.user_id is not None]
    activity_lead_ids = [a.lead_id for a in recent_activities if a.lead_id is not None]
    
    # Update users dict with additional users from activities
    for user_id in activity_user_ids:
        if user_id not in users:
            user_ids.add(user_id)
    
    if user_ids:
        users = {user.id: user for user in User.query.filter(User.id.in_(user_ids)).all()}
    
    # Get leads dict for activities
    leads = {lead.id: lead for lead in Lead.query.filter(Lead.id.in_(activity_lead_ids)).all()} if activity_lead_ids else {}
    
    return render_template("index.html", 
                           title="Dashboard", 
                           tasks=tasks, 
                           users=users,
                           leads=leads,
                           activities_due=tasks_due_today,
                           high_priority_count=high_priority_tasks,
                           today=today,
                           timedelta=timedelta,
                           recent_deals=recent_deals,
                           recent_activities=recent_activities,
                           total_leads=total_leads,
                           total_deals=formatted_deal_value,
                           conversion_rate=f"{conversion_rate}%",
                           total_tasks=total_tasks,
                           months=months,
                           monthly_revenue=monthly_revenue,
                           source_names=source_names,
                           source_counts=source_counts,
                           source_colors=source_colors)


@main.route("/dashboard")
@login_required
def dashboard():
    """Direct dashboard route for authenticated users"""
    return redirect(url_for('main.home'))


@main.route("/create_db")
def create_db():
    db.create_all()
    flash('Database created successfully!', 'info')
    return redirect(url_for('main.home'))

