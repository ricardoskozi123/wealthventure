from datetime import datetime, timedelta
from flask import render_template, flash, redirect, url_for, request, jsonify, abort
from flask_login import current_user, login_required
from sqlalchemy import or_, and_

from omcrm import db
from omcrm.rbac import check_access, is_admin
from .forms import TaskForm, TaskFilterForm, TaskQuickCompleteForm
from .models import Task, TaskStatus, TaskPriority
from . import tasks
from omcrm.users.models import User

@tasks.route("/tasks")
@login_required
def task_list():
    """View all tasks with filtering options"""
    form = TaskFilterForm()
    
    # Default to showing only pending and in_progress tasks
    if not request.args.get('status'):
        tasks_query = Task.query.filter(
            Task.status.in_(['pending', 'in_progress'])
        )
    else:
        tasks_query = Task.query
    
    # Apply filters based on form inputs
    if request.args.get('status'):
        tasks_query = tasks_query.filter(Task.status == request.args.get('status'))
    
    if request.args.get('priority'):
        tasks_query = tasks_query.filter(Task.priority == request.args.get('priority'))
    
    if request.args.get('assignee_id') and int(request.args.get('assignee_id')) > 0:
        tasks_query = tasks_query.filter(Task.assignee_id == request.args.get('assignee_id'))
    
    # Regular users can only see tasks they created or assigned to them
    if not current_user.is_admin:
        tasks_query = tasks_query.filter(
            or_(Task.creator_id == current_user.id, Task.assignee_id == current_user.id)
        )
    
    tasks_list = tasks_query.order_by(Task.due_date.asc()).all()
    
    # Get user objects for each task
    users = {}
    for task in tasks_list:
        if task.assignee_id and task.assignee_id not in users:
            users[task.assignee_id] = User.query.get(task.assignee_id)
    
    return render_template('tasks/task_list.html',
                          title='Tasks',
                          tasks=tasks_list,
                          form=form,
                          users=users)

@tasks.route("/tasks/create", methods=['GET', 'POST'])
@login_required
def create_task():
    """Create a new task"""
    form = TaskForm()
    
    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            priority=form.priority.data,
            status=form.status.data,
            creator_id=current_user.id
        )
        
        # Handle assignee
        if form.assignee_id.data and form.assignee_id.data > 0:
            task.assignee_id = form.assignee_id.data
        
        # Handle related entities
        if form.lead_id.data and form.lead_id.data > 0:
            task.lead_id = form.lead_id.data
        
        if form.deal_id.data and form.deal_id.data > 0:
            task.deal_id = form.deal_id.data
        
        if form.client_id.data and form.client_id.data > 0:
            task.client_id = form.client_id.data
        
        db.session.add(task)
        db.session.commit()
        
        flash('Task created successfully!', 'success')
        return redirect(url_for('tasks.task_list'))
    
    # Set default due date to tomorrow
    if not form.due_date.data:
        form.due_date.data = datetime.utcnow() + timedelta(days=1)
    
    return render_template('tasks/create_task.html',
                          title='Create Task',
                          form=form)

@tasks.route("/tasks/<int:task_id>", methods=['GET', 'POST'])
@login_required
def update_task(task_id):
    """Update an existing task"""
    task = Task.query.get_or_404(task_id)
    
    # Check if user has permission to edit this task
    if not current_user.is_admin and task.creator_id != current_user.id and task.assignee_id != current_user.id:
        abort(403)
    
    form = TaskForm()
    
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        task.priority = form.priority.data
        task.status = form.status.data
        
        # Handle assignee
        if form.assignee_id.data and form.assignee_id.data > 0:
            task.assignee_id = form.assignee_id.data
        else:
            task.assignee_id = None
        
        # Handle related entities
        if form.lead_id.data and form.lead_id.data > 0:
            task.lead_id = form.lead_id.data
        else:
            task.lead_id = None
            
        if form.deal_id.data and form.deal_id.data > 0:
            task.deal_id = form.deal_id.data
        else:
            task.deal_id = None
            
        if form.client_id.data and form.client_id.data > 0:
            task.client_id = form.client_id.data
        else:
            task.client_id = None
        
        db.session.commit()
        
        flash('Task updated successfully!', 'success')
        return redirect(url_for('tasks.task_list'))
    
    # Populate form with existing data
    form.title.data = task.title
    form.description.data = task.description
    form.due_date.data = task.due_date
    form.priority.data = task.priority
    form.status.data = task.status
    
    if task.assignee_id:
        form.assignee_id.data = task.assignee_id
    
    # Set related entities
    if task.lead_id:
        form.lead_id.data = task.lead_id
    if task.deal_id:
        form.deal_id.data = task.deal_id
    if task.client_id:
        form.client_id.data = task.client_id
    
    # Look up the users manually since we don't have relationships
    assignee = None
    if task.assignee_id:
        assignee = User.query.get(task.assignee_id)
    
    creator = User.query.get(task.creator_id)
    
    # Add users to template context
    return render_template('tasks/update_task.html',
                          title='Update Task',
                          form=form,
                          task=task,
                          assignee=assignee,
                          creator=creator)

@tasks.route("/tasks/delete/<int:task_id>", methods=['POST'])
@login_required
def delete_task(task_id):
    """Delete a task"""
    task = Task.query.get_or_404(task_id)
    
    # Check if user has permission to delete this task
    if not current_user.is_admin and task.creator_id != current_user.id:
        abort(403)
    
    db.session.delete(task)
    db.session.commit()
    
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('tasks.task_list'))

@tasks.route("/tasks/<int:task_id>/view", methods=['GET'])
@login_required
def view_task(task_id):
    """View a task's details"""
    task = Task.query.get_or_404(task_id)
    
    # Check if user has permission to view this task
    if not current_user.is_admin and task.creator_id != current_user.id and task.assignee_id != current_user.id:
        abort(403)
    
    # Get creator and assignee user objects
    creator = User.query.get(task.creator_id)
    assignee = None
    if task.assignee_id:
        assignee = User.query.get(task.assignee_id)
    
    # Get client if client_id exists
    client = None
    if task.client_id:
        from omcrm.leads.models import Lead
        client = Lead.query.get(task.client_id)
    
    # Create a form to include CSRF token 
    form = TaskQuickCompleteForm()
    
    return render_template('tasks/view_task.html',
                          title='Task Details',
                          task=task, 
                          creator=creator,
                          assignee=assignee,
                          client=client,
                          form=form)

@tasks.route("/tasks/complete", methods=['POST'])
@login_required
def complete_task():
    """Mark a task as complete"""
    task_id = request.form.get('task_id')
    
    if not task_id:
        flash('No task ID provided', 'danger')
        return redirect(url_for('tasks.task_list'))
    
    task = Task.query.get_or_404(task_id)
    
    # Check if user has permission to update this task
    if not current_user.is_admin and task.creator_id != current_user.id and task.assignee_id != current_user.id:
        flash('You do not have permission to complete this task', 'danger')
        return redirect(url_for('tasks.task_list'))
    
    task.status = 'completed'
    db.session.commit()
    
    flash('Task marked as complete', 'success')
    return redirect(url_for('tasks.view_task', task_id=task.id))

@tasks.route("/api/dashboard/tasks")
@login_required
def get_dashboard_tasks():
    """Get upcoming tasks for dashboard widget"""
    # Get pending and in-progress tasks due in the next 7 days
    upcoming_date = datetime.utcnow() + timedelta(days=7)
    
    if current_user.is_admin:
        tasks_query = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date <= upcoming_date
            )
        )
    else:
        tasks_query = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date <= upcoming_date,
                or_(Task.creator_id == current_user.id, Task.assignee_id == current_user.id)
            )
        )
    
    tasks_list = tasks_query.order_by(Task.due_date.asc()).limit(5).all()
    
    tasks_data = []
    for task in tasks_list:
        tasks_data.append({
            'id': task.id,
            'title': task.title,
            'priority': task.priority,
            'due_date': task.short_due_date,
            'is_overdue': task.is_overdue
        })
    
    return jsonify({'tasks': tasks_data})

@tasks.route("/api/notifications/count")
@login_required
def get_notification_count():
    """Get count of pending notifications"""
    # Get count of pending and overdue tasks
    today = datetime.utcnow()
    
    # Check if current_user is a User object (staff) or Lead object (client)
    is_admin_user = hasattr(current_user, 'is_admin') and current_user.is_admin
    
    if is_admin_user:
        count = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date <= today
            )
        ).count()
    else:
        # For regular users and client leads, only show their relevant tasks
        count = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date <= today,
                or_(
                    Task.creator_id == current_user.id, 
                    Task.assignee_id == current_user.id
                )
            )
        ).count()
    
    return jsonify({'count': count})

@tasks.route("/api/notifications")
@login_required
def get_notifications():
    """Get list of notifications for the current user"""
    # Get pending and overdue tasks
    today = datetime.utcnow()
    
    # Check if current_user is a User object (staff) or Lead object (client)
    is_admin_user = hasattr(current_user, 'is_admin') and current_user.is_admin
    
    if is_admin_user:
        tasks = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date <= today
            )
        ).order_by(Task.due_date.asc()).limit(10).all()
    else:
        # For regular users and client leads, only show their relevant tasks
        tasks = Task.query.filter(
            and_(
                Task.status.in_(['pending', 'in_progress']),
                Task.due_date <= today,
                or_(
                    Task.creator_id == current_user.id, 
                    Task.assignee_id == current_user.id
                )
            )
        ).order_by(Task.due_date.asc()).limit(10).all()
    
    notifications = []
    for task in tasks:
        time_ago = ''
        if task.due_date:
            # Calculate time ago based on due date
            time_delta = today - task.due_date
            if time_delta.days > 0:
                time_ago = f"{time_delta.days} days ago"
            elif time_delta.seconds // 3600 > 0:
                time_ago = f"{time_delta.seconds // 3600} hours ago"
            else:
                time_ago = f"{time_delta.seconds // 60} minutes ago"
        
        # Determine priority
        priority = "low"
        if task.priority == 2:
            priority = "medium"
        elif task.priority == 3:
            priority = "high"
            
        # Create notification object
        notification = {
            'id': task.id,
            'title': f"Task: {task.title}",
            'description': task.description[:100] + '...' if task.description and len(task.description) > 100 else task.description,
            'time_ago': time_ago,
            'is_read': False,  # Assume unread for now
            'priority': priority,
            'url': url_for('tasks.view_task', task_id=task.id)
        }
        notifications.append(notification)
    
    return jsonify({'notifications': notifications}) 
