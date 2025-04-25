from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional
from wtforms_sqlalchemy.fields import QuerySelectField

from omcrm.users.models import User
from omcrm.leads.models import Lead
from omcrm.deals.models import Deal
from .models import TaskPriority, TaskStatus

def user_query():
    return User.query.filter_by(is_user_active=True).all()

def lead_query():
    return Lead.query.all()

def deal_query():
    return Deal.query.all()

class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    due_date = DateTimeField('Due Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], default='medium')
    
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='pending')
    
    # Simplified assignee field - using direct selection rather than QuerySelectField
    assignee_id = SelectField('Assignee', coerce=int, validators=[Optional()])
    
    # Related entity references
    lead_id = SelectField('Related Lead', coerce=int, validators=[Optional()])
    deal_id = SelectField('Related Deal', coerce=int, validators=[Optional()])
    client_id = SelectField('Related Client', coerce=int, validators=[Optional()])
    
    submit = SubmitField('Save Task')
    
    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        # Get all users for assignee dropdown
        users = User.query.all()
        self.assignee_id.choices = [(0, '-- Unassigned --')] + [(user.id, f"{user.first_name} {user.last_name}") for user in users]
        
        # Load related item choices
        from omcrm.leads.models import Lead
        from omcrm.deals.models import Deal
        
        # Lead choices
        leads = Lead.query.all()
        self.lead_id.choices = [(0, '-- None --')] + [(lead.id, f"{lead.first_name} {lead.last_name} - {lead.company_name}") for lead in leads]
        
        # Deal choices
        deals = Deal.query.all()
        self.deal_id.choices = [(0, '-- None --')] + [(deal.id, deal.title) for deal in deals]
        
        # Client choices - use a try/except to safely handle possible attribute errors
        try:
            # First try to get leads marked as clients
            clients = []
            try:
                # Try using is_client attribute if it exists
                clients = Lead.query.filter_by(is_client=True).all()
            except:
                pass
                
            # If no clients found via is_client, try an alternative approach
            if not clients:
                # Check if there's a client_type field or similar
                try:
                    clients = Lead.query.filter_by(lead_type='client').all()
                except:
                    pass
            
            # If still no clients, fall back to all leads
            if not clients:
                clients = Lead.query.all()
                
            self.client_id.choices = [(0, '-- None --')] + [(client.id, f"{client.first_name} {client.last_name} - {client.company_name}") for client in clients]
        except Exception as e:
            # Final fallback - just use an empty list with only the "None" option
            self.client_id.choices = [(0, '-- None --')]

class TaskFilterForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('', 'All Statuses'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='')
    
    priority = SelectField('Priority', choices=[
        ('', 'All Priorities'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], default='')
    
    # Simplified assignee field
    assignee_id = SelectField('Assignee', coerce=int)
    
    submit = SubmitField('Filter')
    
    def __init__(self, *args, **kwargs):
        super(TaskFilterForm, self).__init__(*args, **kwargs)
        # Get all users for assignee dropdown
        users = User.query.all()
        self.assignee_id.choices = [(0, 'All Users')] + [(user.id, f"{user.first_name} {user.last_name}") for user in users]

class TaskQuickCompleteForm(FlaskForm):
    task_id = HiddenField('Task ID', validators=[DataRequired()])
    submit = SubmitField('Mark Complete') 
