from datetime import datetime
from omcrm import db


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=True)
    action_type = db.Column(db.String(50), nullable=False)  # comment, lead_created, deal_updated, etc.
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    target_type = db.Column(db.String(50), nullable=True)  # lead, deal, meeting, comment, deposit, withdrawal
    target_id = db.Column(db.Integer, nullable=True)  # ID of the target object
    data = db.Column(db.JSON, nullable=True)  # Additional JSON data if needed
    
    # Relationships
    user = db.relationship('User', backref=db.backref('activities', lazy=True))
    lead = db.relationship('Lead', backref=db.backref('activities', lazy=True))
    
    def __repr__(self):
        return f"Activity(id={self.id}, action_type='{self.action_type}', timestamp={self.timestamp})"
    
    @staticmethod
    def log(action_type, description, user=None, lead=None, target_type=None, target_id=None, data=None):
        """
        Create and save a new activity log
        
        Args:
            action_type: Type of action (e.g., 'lead_created', 'comment_added')
            description: Human-readable description of the activity
            user: User who performed the action
            lead: Lead associated with the activity (optional)
            target_type: Type of object being acted upon (optional)
            target_id: ID of the target object (optional)
            data: Additional JSON data (optional)
        """
        activity = Activity(
            user_id=user.id if user else None,
            lead_id=lead.id if lead else None,
            action_type=action_type,
            description=description,
            target_type=target_type,
            target_id=target_id,
            data=data
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return activity
    
    @staticmethod
    def get_recent(limit=10, user_id=None, lead_id=None, action_type=None):
        """
        Get recent activities with optional filtering
        """
        query = Activity.query
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if lead_id:
            query = query.filter_by(lead_id=lead_id)
            
        if action_type:
            query = query.filter_by(action_type=action_type)
            
        return query.order_by(Activity.timestamp.desc()).limit(limit).all() 