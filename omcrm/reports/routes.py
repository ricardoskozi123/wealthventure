from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from flask import render_template
from sqlalchemy import func, text, extract, distinct, desc
from datetime import datetime, timedelta
from omcrm.deals.models import Deal, DealStage
from omcrm.leads.models import Lead, LeadSource, LeadStatus
from omcrm.users.models import User, Team
from omcrm.activities.models import Activity
from omcrm.tasks.models import Task
from omcrm import db
from omcrm.rbac import is_admin, check_access

from functools import reduce

reports = Blueprint('reports', __name__)


@reports.route("/reports")
@login_required
def deal_reports():
    # Get key metrics for dashboard
    total_revenue = db.session.query(func.sum(Deal.expected_close_price)).join(
        DealStage, Deal.deal_stage_id == DealStage.id
    ).filter(DealStage.stage_name == 'Closed - Won').scalar() or 0
    
    active_leads_count = db.session.query(func.count(Lead.id)).filter(
        Lead.is_client == False
    ).scalar() or 0
    
    # Calculate conversion rate
    total_leads = db.session.query(func.count(Lead.id)).scalar() or 1  # Prevent division by zero
    converted_clients = db.session.query(func.count(Lead.id)).filter(
        Lead.is_client == True
    ).scalar() or 0
    conversion_rate = (converted_clients / total_leads) * 100
    
    # Calculate average deal size
    deal_count = db.session.query(func.count(Deal.id)).join(
        DealStage, Deal.deal_stage_id == DealStage.id
    ).filter(DealStage.stage_name == 'Closed - Won').scalar() or 1  # Prevent division by zero
    avg_deal_size = total_revenue / deal_count if deal_count > 0 else 0
    
    # Get deal stage distribution data
    deal_stages = db.session.query(
        DealStage.stage_name,
        func.count(Deal.id).label('count')
    ).join(
        Deal, DealStage.id == Deal.deal_stage_id
    ).group_by(
        DealStage.stage_name
    ).all()
    
    stage_labels = [stage.stage_name for stage in deal_stages]
    stage_counts = [stage.count for stage in deal_stages]
    
    return render_template(
        "reports/reports.html", 
        title="Reports Dashboard",
        total_revenue=total_revenue,
        active_leads_count=active_leads_count,
        conversion_rate=conversion_rate,
        avg_deal_size=avg_deal_size,
        stage_labels=stage_labels,
        stage_counts=stage_counts
    )


@reports.route("/reports/deal_stages")
@login_required
def deal_stages():
    if current_user.is_admin:
        query = Deal.query \
            .with_entities(
                DealStage.stage_name.label('stage_name'),
                func.sum(Deal.expected_close_price).label('total_price'),
                func.count(Deal.id).label('total_count')
            ) \
            .join(Deal.deal_stage) \
            .group_by(DealStage.stage_name) \
            .order_by(text('total_price DESC'))
    else:
        query = Deal.query \
            .with_entities(
                DealStage.stage_name.label('stage_name'),
                func.sum(Deal.expected_close_price).label('total_price'),
                func.count(Deal.id).label('total_count')
            ) \
            .join(Deal.deal_stage) \
            .group_by(DealStage.stage_name, Deal.owner_id) \
            .having(Deal.owner_id == current_user.id) \
            .order_by(text('total_price DESC'))

    return render_template("reports/deals_stages.html",
                           title="Deal Stage Revenue", 
                           deals=query.all())


@reports.route("/reports/deals_closed")
@login_required
def deals_closed():
    if current_user.is_admin:
        query = Deal.query \
            .with_entities(
                Lead.company_name.label('client_name'),
                DealStage.stage_name.label('stage_name'),
                func.sum(Deal.expected_close_price).label('total_price'),
                func.count(Deal.id).label('total_count')
            ) \
            .join(Deal.client, Deal.deal_stage) \
            .group_by(Lead.company_name, DealStage.stage_name) \
            .order_by(text('stage_name'))
    else:
        query = Deal.query \
            .with_entities(
                Lead.company_name.label('client_name'),
                DealStage.stage_name.label('stage_name'),
                func.sum(Deal.expected_close_price).label('total_price'),
                func.count(Deal.id).label('total_count')
            ) \
            .join(Deal.client, Deal.deal_stage) \
            .group_by(Lead.company_name, DealStage.stage_name, Deal.owner_id) \
            .having(Deal.owner_id == current_user.id) \
            .order_by(text('stage_name'))

    stages = []
    data = []
    rows = query.all()
    if len(rows) > 0:
        for d in rows:
            if d[1] not in stages:
                stages.append(d[1])
                data.append({
                    'stage_name': d[1],
                    'clients_count': len([x[1] for x in rows if x[1] == d[1]]),
                    'rows': [(x[0], x[2], x[3]) for x in rows if x[1] == d[1]]
                })

    return render_template("reports/deals_closed.html",
                           title="Client Revenue Distribution", 
                           deals=data)


def get_users_deals():
    users_list = Deal.query \
        .with_entities(
            Deal.owner_id.label('owner'),
            User.first_name,
            User.last_name,
            DealStage.stage_name,
            func.sum(Deal.expected_close_price).label('total_price')
        ) \
        .filter(DealStage.stage_name.in_(['Closed - Won', 'Closed - Lost'])) \
        .join(Deal.owner, Deal.deal_stage) \
        .group_by(Deal.owner_id, User.first_name, User.last_name, DealStage.stage_name) \
        .order_by(text('owner'))

    won_list = [x for x in users_list.all() if x.stage_name == 'Closed - Won']
    lost_list = [x for x in users_list.all() if x.stage_name == 'Closed - Lost']
    return won_list, lost_list


@reports.route("/reports/deal_stage_by_users")
@login_required
@check_access('reports', 'view')
def deal_stage_by_users():
    query = Deal.query \
        .with_entities(
            Deal.owner_id.label('owner'),
            User.first_name,
            User.last_name,
            DealStage.stage_name.label('stage_name'),
            func.sum(Deal.expected_close_price).label('total_price'),
            func.count(Deal.id).label('total_count')
        ) \
        .join(Deal.owner, Deal.deal_stage) \
        .group_by(Deal.owner_id, User.first_name, User.last_name, DealStage.stage_name) \
        .order_by(text('owner'))

    users = []
    data = []
    rows = query.all()
    if len(rows) > 0:
        for d in rows:
            if d[0] not in users:
                users.append(d[0])
                data.append({
                    'owner': f'{d[1]} {d[2]}',
                    'count': len([x[3] for x in rows if x[0] == d[0]]),
                    'rows': [(x[3], x[4], x[5]) for x in rows if x[0] == d[0]],
                    'total_cost': reduce(lambda a, b: a + b, [x[4] for x in rows if x[0] == d[0]]),
                    'total_qty': reduce(lambda a, b: a + b, [x[5] for x in rows if x[0] == d[0]])
                })

    return render_template("reports/deals_stage_by_users.html",
                           title="User Sales Performance",
                           deals=data,
                           deals_closed=get_users_deals())


@reports.route("/reports/deal_closed_by_date")
@login_required
def deal_closed_by_date():
    # Group by month and year
    query = db.session.query(
        extract('year', Deal.expected_close_date).label('year'),
        extract('month', Deal.expected_close_date).label('month'),
        DealStage.stage_name,
        func.sum(Deal.expected_close_price).label('total_price'),
        func.count(Deal.id).label('deal_count')
    ).join(
        DealStage, Deal.deal_stage_id == DealStage.id
    ).filter(
        DealStage.stage_name.in_(['Closed - Won', 'Closed - Lost'])
    ).group_by(
        'year', 'month', DealStage.stage_name
    ).order_by(
        'year', 'month'
    )
    
    # If not admin, filter by owner
    if not current_user.is_admin:
        query = query.filter(Deal.owner_id == current_user.id)
    
    result = query.all()
    
    # Process the data for the chart
    months = []
    won_data = []
    lost_data = []
    
    for row in result:
        month_str = f"{int(row.month)}/{int(row.year)}"
        if month_str not in months:
            months.append(month_str)
            
        if row.stage_name == 'Closed - Won':
            won_data.append({'month': month_str, 'amount': float(row.total_price), 'count': row.deal_count})
        elif row.stage_name == 'Closed - Lost':
            lost_data.append({'month': month_str, 'amount': float(row.total_price), 'count': row.deal_count})
    
    return render_template("reports/deals_closed_by_time.html",
                         title="Sales Timeline Analysis",
                         months=months,
                         won_data=won_data,
                         lost_data=lost_data)


@reports.route("/reports/sales_forecast")
@login_required
def sales_forecast():
    # Get historical data for prediction
    historical = db.session.query(
        extract('year', Deal.expected_close_date).label('year'),
        extract('month', Deal.expected_close_date).label('month'),
        func.sum(Deal.expected_close_price).label('revenue')
    ).join(
        DealStage, Deal.deal_stage_id == DealStage.id
    ).filter(
        DealStage.stage_name == 'Closed - Won'
    ).group_by(
        'year', 'month'
    ).order_by(
        'year', 'month'
    ).all()
    
    # Get pipeline data for prediction
    pipeline = db.session.query(
        DealStage.stage_name,
        func.sum(Deal.expected_close_price).label('potential_revenue'),
        func.count(Deal.id).label('deal_count')
    ).join(
        Deal, DealStage.id == Deal.deal_stage_id
    ).filter(
        DealStage.stage_name.notin_(['Closed - Won', 'Closed - Lost'])
    ).group_by(
        DealStage.stage_name
    ).all()
    
    # Simple forecasting based on probability by stage
    stage_probabilities = {
        'Discovery': 0.2,
        'Proposal': 0.4,
        'Negotiation': 0.7,
        'Qualification': 0.3,
        'Presentation': 0.5
    }
    
    # Calculate forecast
    forecast_data = []
    total_forecast = 0
    
    for stage in pipeline:
        probability = stage_probabilities.get(stage.stage_name, 0.3)  # Default probability
        forecast_value = float(stage.potential_revenue) * probability
        total_forecast += forecast_value
        
        forecast_data.append({
            'stage': stage.stage_name,
            'potential': float(stage.potential_revenue),
            'probability': probability,
            'forecast': forecast_value,
            'count': stage.deal_count
        })
    
    # Get historical monthly average
    historical_data = []
    if historical:
        total_historical = sum(h.revenue for h in historical)
        months_count = len(historical)
        monthly_average = total_historical / months_count if months_count > 0 else 0
    else:
        monthly_average = 0
    
    return render_template("reports/sales_forecast.html",
                         title="Sales Forecasting",
                         forecast_data=forecast_data,
                         total_forecast=total_forecast,
                         monthly_average=monthly_average,
                         historical=historical)


@reports.route("/reports/lead_source_performance")
@login_required
def lead_source_performance():
    # Get lead source performance data
    query = db.session.query(
        LeadSource.source_name,
        func.count(Lead.id).label('total_leads'),
        func.sum(case((Lead.is_client == True, 1), else_=0)).label('converted'),
        (func.sum(case((Lead.is_client == True, 1), else_=0)) / func.count(Lead.id) * 100).label('conversion_rate')
    ).join(
        Lead, LeadSource.id == Lead.lead_source_id
    ).group_by(
        LeadSource.source_name
    ).order_by(
        desc('total_leads')
    )
    
    # Add revenue data from converted leads
    sources_data = []
    
    for row in query.all():
        # Get total revenue from this source
        revenue = db.session.query(func.sum(Deal.expected_close_price)).join(
            Lead, Deal.client_id == Lead.id
        ).join(
            LeadSource, Lead.lead_source_id == LeadSource.id
        ).filter(
            LeadSource.source_name == row.source_name,
            Lead.is_client == True
        ).scalar() or 0
        
        sources_data.append({
            'source': row.source_name,
            'leads': row.total_leads,
            'converted': row.converted,
            'conversion_rate': float(row.conversion_rate),
            'revenue': float(revenue),
            'cost_per_lead': 0,  # Would need campaign cost data
            'roi': 0  # Would need campaign cost data
        })
    
    return render_template("reports/lead_source_performance.html",
                         title="Lead Source Performance",
                         sources_data=sources_data)


@reports.route("/reports/lead_conversion_rate")
@login_required
def lead_conversion_rate():
    # Get conversion rate over time (monthly)
    query = db.session.query(
        extract('year', Lead.date_created).label('year'),
        extract('month', Lead.date_created).label('month'),
        func.count(Lead.id).label('total_leads'),
        func.sum(case((Lead.is_client == True, 1), else_=0)).label('converted')
    ).group_by(
        'year', 'month'
    ).order_by(
        'year', 'month'
    )
    
    # Process data for chart
    months = []
    conversion_data = []
    
    for row in query.all():
        month_str = f"{int(row.month)}/{int(row.year)}"
        months.append(month_str)
        
        conversion_rate = (row.converted / row.total_leads * 100) if row.total_leads > 0 else 0
        conversion_data.append({
            'month': month_str,
            'leads': row.total_leads,
            'converted': row.converted,
            'rate': float(conversion_rate)
        })
    
    # Get status distribution for non-converted leads
    status_dist = db.session.query(
        LeadStatus.status_name,
        func.count(Lead.id).label('count')
    ).join(
        Lead, LeadStatus.id == Lead.lead_status_id
    ).filter(
        Lead.is_client == False
    ).group_by(
        LeadStatus.status_name
    ).order_by(
        desc('count')
    ).all()
    
    status_labels = [status.status_name for status in status_dist]
    status_counts = [status.count for status in status_dist]
    
    return render_template("reports/lead_conversion_rate.html",
                         title="Lead Conversion Analysis",
                         months=months,
                         conversion_data=conversion_data,
                         status_labels=status_labels,
                         status_counts=status_counts)


@reports.route("/reports/client_acquisition")
@login_required
def client_acquisition():
    # Get client acquisition over time
    query = db.session.query(
        extract('year', Lead.conversion_date).label('year'),
        extract('month', Lead.conversion_date).label('month'),
        func.count(Lead.id).label('clients_acquired')
    ).filter(
        Lead.is_client == True,
        Lead.conversion_date != None
    ).group_by(
        'year', 'month'
    ).order_by(
        'year', 'month'
    )
    
    # Process data for chart
    months = []
    acquisition_data = []
    
    for row in query.all():
        month_str = f"{int(row.month)}/{int(row.year)}"
        months.append(month_str)
        
        acquisition_data.append({
            'month': month_str,
            'clients': row.clients_acquired
        })
    
    # Get client source distribution
    source_dist = db.session.query(
        LeadSource.source_name,
        func.count(Lead.id).label('count')
    ).join(
        Lead, LeadSource.id == Lead.lead_source_id
    ).filter(
        Lead.is_client == True
    ).group_by(
        LeadSource.source_name
    ).order_by(
        desc('count')
    ).all()
    
    source_labels = [source.source_name for source in source_dist]
    source_counts = [source.count for source in source_dist]
    
    return render_template("reports/client_acquisition.html",
                         title="Client Acquisition Trends",
                         months=months,
                         acquisition_data=acquisition_data,
                         source_labels=source_labels,
                         source_counts=source_counts)


@reports.route("/reports/client_by_country")
@login_required
def client_by_country():
    # Get client distribution by country
    query = db.session.query(
        Lead.country,
        func.count(Lead.id).label('client_count')
    ).filter(
        Lead.is_client == True,
        Lead.country != None,
        Lead.country != ''
    ).group_by(
        Lead.country
    ).order_by(
        desc('client_count')
    ).all()
    
    country_data = []
    
    for row in query:
        # Get revenue from this country
        revenue = db.session.query(func.sum(Deal.expected_close_price)).join(
            Lead, Deal.client_id == Lead.id
        ).filter(
            Lead.country == row.country,
            Lead.is_client == True
        ).scalar() or 0
        
        country_data.append({
            'country': row.country,
            'clients': row.client_count,
            'revenue': float(revenue)
        })
    
    return render_template("reports/client_by_country.html",
                         title="Client Geographical Distribution",
                         country_data=country_data)


@reports.route("/reports/user_activity")
@login_required
@check_access('reports', 'view')
def user_activity():
    # Get user activity data
    query = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        func.count(Activity.id).label('activity_count')
    ).outerjoin(
        Activity, User.id == Activity.user_id
    ).group_by(
        User.id, User.first_name, User.last_name
    ).order_by(
        desc('activity_count')
    ).all()
    
    user_activity_data = []
    
    for row in query:
        # Get leads created
        leads_created = db.session.query(func.count(Lead.id)).filter(
            Lead.owner_id == row.id
        ).scalar() or 0
        
        # Get deals created
        deals_created = db.session.query(func.count(Deal.id)).filter(
            Deal.owner_id == row.id
        ).scalar() or 0
        
        # Get tasks completed
        tasks_completed = db.session.query(func.count(Task.id)).filter(
            Task.assigned_to_id == row.id,
            Task.is_completed == True
        ).scalar() or 0
        
        user_activity_data.append({
            'name': f"{row.first_name} {row.last_name}",
            'activities': row.activity_count,
            'leads': leads_created,
            'deals': deals_created,
            'tasks': tasks_completed
        })
    
    return render_template("reports/user_activity.html",
                         title="User Activity Summary",
                         user_activity_data=user_activity_data)


@reports.route("/reports/team_performance")
@login_required
@check_access('reports', 'view')
def team_performance():
    # Get team performance data
    query = db.session.query(
        Team.id,
        Team.name,
        func.count(distinct(User.id)).label('member_count')
    ).outerjoin(
        User, Team.id == User.team_id
    ).group_by(
        Team.id, Team.name
    ).all()
    
    team_data = []
    
    for row in query:
        # Get revenue by team
        revenue = db.session.query(func.sum(Deal.expected_close_price)).join(
            User, Deal.owner_id == User.id
        ).join(
            DealStage, Deal.deal_stage_id == DealStage.id
        ).filter(
            User.team_id == row.id,
            DealStage.stage_name == 'Closed - Won'
        ).scalar() or 0
        
        # Get lead count
        lead_count = db.session.query(func.count(Lead.id)).join(
            User, Lead.owner_id == User.id
        ).filter(
            User.team_id == row.id
        ).scalar() or 0
        
        # Get conversion rate
        converted = db.session.query(func.count(Lead.id)).join(
            User, Lead.owner_id == User.id
        ).filter(
            User.team_id == row.id,
            Lead.is_client == True
        ).scalar() or 0
        
        conversion_rate = (converted / lead_count * 100) if lead_count > 0 else 0
        
        team_data.append({
            'name': row.name,
            'members': row.member_count,
            'revenue': float(revenue),
            'leads': lead_count,
            'conversion_rate': float(conversion_rate),
            'avg_revenue_per_member': float(revenue / row.member_count) if row.member_count > 0 else 0
        })
    
    return render_template("reports/team_performance.html",
                         title="Team Performance Analysis",
                         team_data=team_data)


@reports.route("/reports/task_completion")
@login_required
@check_access('reports', 'view')
def task_completion():
    # Get task completion data
    query = db.session.query(
        extract('year', Task.due_date).label('year'),
        extract('month', Task.due_date).label('month'),
        func.count(Task.id).label('total_tasks'),
        func.sum(case((Task.is_completed == True, 1), else_=0)).label('completed_tasks')
    ).group_by(
        'year', 'month'
    ).order_by(
        'year', 'month'
    )
    
    # Process data for chart
    months = []
    task_data = []
    
    for row in query.all():
        month_str = f"{int(row.month)}/{int(row.year)}"
        months.append(month_str)
        
        completion_rate = (row.completed_tasks / row.total_tasks * 100) if row.total_tasks > 0 else 0
        task_data.append({
            'month': month_str,
            'total': row.total_tasks,
            'completed': row.completed_tasks,
            'rate': float(completion_rate)
        })
    
    # Get user task completion rates
    user_query = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        func.count(Task.id).label('total_tasks'),
        func.sum(case((Task.is_completed == True, 1), else_=0)).label('completed_tasks')
    ).join(
        Task, User.id == Task.assigned_to_id
    ).group_by(
        User.id, User.first_name, User.last_name
    ).order_by(
        desc('completed_tasks')
    ).all()
    
    user_task_data = []
    
    for row in user_query:
        completion_rate = (row.completed_tasks / row.total_tasks * 100) if row.total_tasks > 0 else 0
        user_task_data.append({
            'name': f"{row.first_name} {row.last_name}",
            'total': row.total_tasks,
            'completed': row.completed_tasks,
            'rate': float(completion_rate)
        })
    
    return render_template("reports/task_completion.html",
                         title="Task Completion Rates",
                         months=months,
                         task_data=task_data,
                         user_task_data=user_task_data)


@reports.route("/reports/system_usage")
@login_required
@is_admin
def system_usage():
    # Get system usage statistics
    
    # Get last 30 days of activities
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    activity_query = db.session.query(
        extract('day', Activity.timestamp).label('day'),
        func.count(Activity.id).label('activity_count')
    ).filter(
        Activity.timestamp >= thirty_days_ago
    ).group_by(
        'day'
    ).order_by(
        'day'
    ).all()
    
    # Get user login count
    user_count = db.session.query(func.count(User.id)).filter(
        User.is_user_active == True
    ).scalar() or 0
    
    # Get entity counts
    lead_count = db.session.query(func.count(Lead.id)).scalar() or 0
    client_count = db.session.query(func.count(Lead.id)).filter(
        Lead.is_client == True
    ).scalar() or 0
    deal_count = db.session.query(func.count(Deal.id)).scalar() or 0
    task_count = db.session.query(func.count(Task.id)).scalar() or 0
    
    # Activity by type
    activity_by_type = db.session.query(
        Activity.action_type,
        func.count(Activity.id).label('count')
    ).group_by(
        Activity.action_type
    ).order_by(
        desc('count')
    ).all()
    
    activity_types = [a.action_type for a in activity_by_type]
    activity_counts = [a.count for a in activity_by_type]
    
    return render_template("reports/system_usage.html",
                         title="System Usage Statistics",
                         user_count=user_count,
                         lead_count=lead_count,
                         client_count=client_count,
                         deal_count=deal_count,
                         task_count=task_count,
                         activity_data=activity_query,
                         activity_types=activity_types,
                         activity_counts=activity_counts)
