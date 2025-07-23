from datetime import datetime
from flask import current_app
from omcrm import db
from omcrm.users.models import User

class TaskPriority:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'

    @classmethod
    def choices(cls):
        return [(cls.LOW, 'Low'), (cls.MEDIUM, 'Medium'), (cls.HIGH, 'High')]

class TaskStatus:
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    @classmethod
    def choices(cls):
        return [
            (cls.PENDING, 'Pending'),
            (cls.IN_PROGRESS, 'In Progress'),
            (cls.COMPLETED, 'Completed'),
            (cls.CANCELLED, 'Cancelled')
        ]

class Task(db.Model):
    __tablename__ = 'task'  # Use singular for SQLite compatibility
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Task priority: 'low', 'medium', 'high'
    priority = db.Column(db.String(20), nullable=False, default='medium')
    
    # Task status: 'pending', 'in_progress', 'completed', 'cancelled'
    status = db.Column(db.String(20), nullable=False, default='pending')
    
    # Simple integer IDs without constraints
    lead_id = db.Column(db.Integer, nullable=True)
    deal_id = db.Column(db.Integer, nullable=True)
    account_id = db.Column(db.Integer, nullable=True)
    contact_id = db.Column(db.Integer, nullable=True)
    client_id = db.Column(db.Integer, nullable=True)
    
    # User IDs without relationship constraints
    creator_id = db.Column(db.Integer, nullable=False)
    assignee_id = db.Column(db.Integer, nullable=True)
    
    # Define relationships
    creator = db.relationship('User', foreign_keys=[creator_id], 
                             backref=db.backref('created_tasks', lazy='dynamic'),
                             primaryjoin="Task.creator_id == User.id")
    assignee = db.relationship('User', foreign_keys=[assignee_id],
                              backref=db.backref('assigned_tasks', lazy='dynamic'),
                              primaryjoin="Task.assignee_id == User.id")
    
    def __repr__(self):
        return f"Task('{self.title}', due on '{self.due_date}')"
    
    def is_overdue_method(self):
        """Check if task is overdue"""
        return self.due_date < datetime.utcnow() and self.status not in ['completed', 'cancelled']
    
    @property
    def formatted_due_date(self):
        return self.due_date.strftime('%b %d, %Y %I:%M %p')
    
    @property
    def short_due_date(self):
        return self.due_date.strftime('%b %d, %Y')
    
    @property
    def status_label(self):
        status_labels = {
            'pending': 'Pending',
            'in_progress': 'In Progress',
            'completed': 'Completed',
            'cancelled': 'Cancelled'
        }
        return status_labels.get(self.status, self.status.title())
    
    @property
    def priority_label(self):
        priority_labels = {
            'low': 'Low',
            'medium': 'Medium',
            'high': 'High'
        }
        return priority_labels.get(self.priority, self.priority.title())
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        return self.due_date < datetime.utcnow() and self.status not in ['completed', 'cancelled']
    
    @classmethod
    def get_upcoming_tasks(cls, user_id, limit=5):
        """Get upcoming tasks for a user that haven't been completed"""
        return cls.query.filter(
            cls.assignee_id == user_id,
            cls.status != TaskStatus.COMPLETED,
            cls.status != TaskStatus.CANCELLED
        ).order_by(cls.due_date).limit(limit).all()
    
    @classmethod
    def get_recent_activity(cls, limit=5):
        """Get recently created or updated tasks as activity feed"""
        return cls.query.order_by(
            cls.created_on.desc()
        ).limit(limit).all()
    
    @classmethod
    def get_pending_notifications(cls, user_id):
        """Get unread tasks assigned to a user"""
        return cls.query.filter(
            cls.assignee_id == user_id,
            cls.status == TaskStatus.PENDING
        ).all()
    
    def mark_as_read(self):
        """Mark a task as read"""
        self.status = TaskStatus.COMPLETED
        db.session.commit()

    # Property to match the template's expectation
    @property
    def date_created(self):
        return self.created_on
    
    @property
    def date_completed(self):
        # This would normally come from a completed_on field, but providing a placeholder
        if self.status == 'completed':
            return datetime.utcnow()  # In a real app, store the actual completion date
        return None

# Add TaskComment model for task comments
class TaskComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    task = db.relationship('Task', backref=db.backref('comments', lazy=True))
    user = db.relationship('User', backref=db.backref('task_comments', lazy=True))
    
    def __repr__(self):
        return f"TaskComment('{self.id}', task_id='{self.task_id}')" 
