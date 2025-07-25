from omcrm import db, login_manager
from flask_login import UserMixin, current_user
from flask import session

# Avoid circular import by only importing Lead when needed
@login_manager.user_loader
def load_user(user_id):
    """Load the appropriate user or client based on user_id and session data"""
    
    # Check if we're in client login mode from the session
    is_client_login = session.get('login_type') == 'client'
    
    if is_client_login:
        # This is a client login, so only check for Lead
        from omcrm.leads.models import Lead
        return Lead.query.filter_by(id=int(user_id), is_client=True).first()
    else:
        # This is a user login, so only check for User
        return User.query.get(int(user_id))


class Team(db.Model):
    id = db.Column(db.Integer, db.Sequence('team_id_seq'), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    leader_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    
    leader = db.relationship('User', foreign_keys=[leader_id], backref='led_team', uselist=False, lazy=True)
    members = db.relationship('User', backref='team', foreign_keys='User.team_id', lazy=True)
    
    @staticmethod
    def get_by_id(team_id):
        return Team.query.filter_by(id=team_id).first()
    
    def __repr__(self):
        return f"Team('{self.name}')"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, db.Sequence('user_id_seq'), primary_key=True)
    first_name = db.Column(db.String(20), nullable=True)
    last_name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    avatar = db.Column(db.String(25), nullable=True)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_first_login = db.Column(db.Boolean, nullable=False, default=True)
    is_user_active = db.Column(db.Boolean, nullable=False, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id', ondelete='SET NULL'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id', ondelete='SET NULL'), nullable=True)
    leads = db.relationship('Lead', backref='owner', lazy=True)
    # Use simple string reference without relationship to avoid circular imports

    @staticmethod
    def get_label(user):
        return user.get_name()

    @staticmethod
    def user_list_query():
        return User.query

    @staticmethod
    def get_current_user():
        return User.query.filter_by(id=current_user.id).first()

    @staticmethod
    def get_by_id(user_id):
        return User.query.filter_by(id=user_id).first()
    
    @property
    def is_team_leader(self):
        """
        Check if the user is a team leader
        Returns True if the user has a led_team attribute that is not None
        """
        try:
            # First check if the user is an admin (optional)
            if getattr(self, 'is_admin', False):
                return False  # Admins use different permissions
                
            # Check if led_team attribute exists
            if not hasattr(self, 'led_team'):
                return False
                
            # Check if led_team is None
            led_team = getattr(self, 'led_team', None)
            if led_team is None:
                return False
                
            # Handle led_team as a list
            if isinstance(led_team, list):
                return len(led_team) > 0
                
            # If led_team exists and isn't None or an empty list, consider them a team leader
            return True
        except Exception as e:
            # Log error and return False to be safe
            print(f"Error checking team leader status: {str(e)}")
            return False
        
    def get_team_members(self):
        """
        Get a list of team members for a team leader
        Returns an empty list if the user is not a team leader or if there are no team members
        """
        try:
            # Check if user is a team leader first
            if not getattr(self, 'is_team_leader', False):
                return []
                
            # Safely get led_team attribute
            led_team = getattr(self, 'led_team', None)
            if led_team is None:
                return []
                
            # Handle different led_team structures
            if hasattr(led_team, 'members'):
                members = getattr(led_team, 'members', None)
                return members if members else []
                
            if isinstance(led_team, list) and len(led_team) > 0:
                first_team = led_team[0]
                if hasattr(first_team, 'members'):
                    members = getattr(first_team, 'members', None)
                    return members if members else []
                    
            # Default case: no team members found
            return []
        except Exception as e:
            # Log the error and return empty list
            print(f"Error getting team members: {str(e)}")
            return []

    def get_name(self):
        return self.first_name + ' ' + self.last_name

    def __repr__(self):
        return f"User('{self.first_name}', '{self.last_name}', '{self.email}', '{self.avatar}')"


roles_resources = db.Table(
    'roles_resources',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
    db.Column('resource_id', db.Integer, db.ForeignKey('resource.id'))
)


class Role(db.Model):
    id = db.Column(db.Integer, db.Sequence('role_id_seq'), primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    user = db.relationship(
        'User',
        uselist=False,
        backref='role',
        lazy=True
    )
    resources = db.relationship(
        'Resource',
        secondary=roles_resources,
        backref=db.backref('resources', lazy='dynamic')
    )

    @staticmethod
    def get_by_name(name):
        return Role.query.filter_by(name=name).first()

    @staticmethod
    def get_by_id(role_id):
        return Role.query.filter_by(id=role_id).first()

    def set_permissions(self, resources):
        for ind in range(len(resources)):
            self.resources[ind].can_view = resources[ind].can_view.data
            self.resources[ind].can_create = resources[ind].can_create.data
            self.resources[ind].can_edit = resources[ind].can_edit.data
            self.resources[ind].can_delete = resources[ind].can_delete.data
            if hasattr(resources[ind], 'can_impersonate'):
                self.resources[ind].can_impersonate = resources[ind].can_impersonate.data
            # 🔧 NEW: Handle manager-level permissions
            if hasattr(resources[ind], 'can_view_all_clients'):
                self.resources[ind].can_view_all_clients = resources[ind].can_view_all_clients.data
            if hasattr(resources[ind], 'can_view_all_leads'):
                self.resources[ind].can_view_all_leads = resources[ind].can_view_all_leads.data


class Resource(db.Model):
    id = db.Column(db.Integer, db.Sequence('resource_id_seq'), primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    can_view = db.Column(db.Boolean, nullable=False)
    can_edit = db.Column(db.Boolean, nullable=False)
    can_create = db.Column(db.Boolean, nullable=False)
    can_delete = db.Column(db.Boolean, nullable=False)
    can_impersonate = db.Column(db.Boolean, nullable=False, default=False)
    # 🔧 NEW: Manager-level permissions
    can_view_all_clients = db.Column(db.Boolean, nullable=False, default=False)
    can_view_all_leads = db.Column(db.Boolean, nullable=False, default=False)
