from datetime import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
from omcrm.webtrader.models import Trade
from omcrm import db
from flask_login import UserMixin


class LeadStatus(db.Model):
    id = db.Column(db.Integer, db.Sequence('lead_status_id_seq'), primary_key=True)
    status_name = db.Column(db.String(40), unique=True, nullable=False)
    color = db.Column(db.String(20), nullable=True, default='#4361ee')  # Color for display purposes only
    description = db.Column(db.String(100), nullable=True)  # Description/meaning of the status
    leads = db.relationship('Lead', backref='status', lazy=True)

    @staticmethod
    def lead_status_query():
        return LeadStatus.query

    @staticmethod
    def get_by_id(lead_status_id):
        return LeadStatus.query.filter_by(id=lead_status_id).first()

    def __repr__(self):
        return f"LeadStatus('{self.status_name}')"


class LeadSource(db.Model):
    id = db.Column(db.Integer, db.Sequence('lead_source_id_seq'), primary_key=True)
    source_name = db.Column(db.String(40), unique=True, nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=True)
    affiliate_id = db.Column(db.String(40), nullable=True)
    is_api_enabled = db.Column(db.Boolean, default=False)
    leads = db.relationship('Lead', backref='source', lazy=True)

    @staticmethod
    def get_by_id(lead_source_id):
        return LeadSource.query.filter_by(id=lead_source_id).first()

    @staticmethod
    def get_by_api_key(api_key):
        return LeadSource.query.filter_by(api_key=api_key, is_api_enabled=True).first()

    @staticmethod
    def lead_source_query():
        return LeadSource.query

    def __repr__(self):
        return f"LeadSource('{self.source_name}')"


class Lead(db.Model, UserMixin):
    id = db.Column(db.Integer, db.Sequence('lead_id_seq'), primary_key=True)
    title = db.Column(db.String(100), nullable=True)
    first_name = db.Column(db.String(40), nullable=True)
    last_name = db.Column(db.String(40), nullable=False)
    company_name = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    address_line = db.Column(db.String(40), nullable=True)
    addr_state = db.Column(db.String(40), nullable=True)
    addr_city = db.Column(db.String(40), nullable=True)
    post_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(40), nullable=True)
    notes = db.Column(db.String(200), nullable=True)
    lead_source_id = db.Column(db.Integer, db.ForeignKey('lead_source.id', ondelete='SET NULL'), nullable=True)
    lead_status_id = db.Column(db.Integer, db.ForeignKey('lead_status.id', ondelete='SET NULL'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    # 🔧 NEW: Funnel tracking for lead attribution
    funnel_name = db.Column(db.String(100), nullable=True)
    affiliate_id = db.Column(db.String(100), nullable=True)  # Store affiliate ID directly
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='lead', cascade="all, delete-orphan", lazy=True)
    is_client = db.Column(db.Boolean, default=False)
    conversion_date = db.Column(db.DateTime, nullable=True)
    trades = db.relationship('Trade', back_populates='lead', lazy=True)
    _password = db.Column(db.String(128), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    current_balance = db.Column(db.Float, default=0.0, nullable=False)
    bonus_balance = db.Column(db.Float, default=0.0, nullable=False)
    credit_balance = db.Column(db.Float, default=0.0, nullable=False)
    available_to_trade = db.Column(db.Boolean, default=True, nullable=False)
    profile_image = db.Column(db.String(120), nullable=True, default='default.jpg')

    @property
    def equity(self):
        """Calculate equity based on current balance + bonus balance + unrealized P/L"""
        total_balance = self.current_balance + self.bonus_balance + self.credit_balance
        
        # Calculate unrealized P/L from open trades
        unrealized_pl = 0.0
        for trade in self.trades:
            if trade.status == 'open':
                # Get the current price of the instrument
                instrument = trade.instrument
                if instrument and instrument.current_price:
                    if trade.trade_type == 'buy':  # Long position
                        unrealized_pl += (instrument.current_price - trade.price) * trade.amount
                    elif trade.trade_type == 'sell':  # Short position
                        unrealized_pl += (trade.price - instrument.current_price) * trade.amount
                        
        return total_balance + unrealized_pl

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, plain_text_password):
        self._password = generate_password_hash(plain_text_password)

    def set_password(self, password):
        self._password = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return check_password_hash(self._password, password)

    @property
    def is_authenticated(self):
        return True

    # Removed is_active property override - using database column directly
    
    @property
    def is_anonymous(self):
        return False

    def update_balance(self, amount):
        if self.current_balance is None:
            self.current_balance = 0.0
        self.current_balance += amount
        db.session.commit()

    def add_credit(self, amount):
        """Add credit to the client's account"""
        if self.credit_balance is None:
            self.credit_balance = 0.0
        self.credit_balance += amount
        db.session.commit()

    def apply_bonus(self, bonus_amount):
        """Apply bonus as a fixed dollar amount"""
        if self.bonus_balance is None:
            self.bonus_balance = 0.0
        self.bonus_balance += bonus_amount
        db.session.commit()

    def get_total_balance(self):
        """Get total balance including credit and bonus"""
        if self.current_balance is None:
            self.current_balance = 0.0
        if self.bonus_balance is None:
            self.bonus_balance = 0.0
        if self.credit_balance is None:
            self.credit_balance = 0.0
        return self.current_balance + self.bonus_balance + self.credit_balance

    @staticmethod
    def get_by_id(lead_id):
        return Lead.query.filter_by(id=lead_id).first()

    @staticmethod
    def get_leads_for_forms(owner_id=None):
        """
        Get leads for form select fields with optional filtering by owner
        Returns a list of tuples (id, display_name) for WTForms select fields
        """
        query = Lead.query.filter_by(is_client=True)
        
        # Filter by owner if specified
        if owner_id is not None:
            query = query.filter_by(owner_id=owner_id)
            
        leads = query.order_by(Lead.last_name).all()
        
        # Format as (id, display_name) for form select fields
        return [(lead.id, f"{lead.first_name} {lead.last_name} - {lead.email if lead.email else '(no email)'}") 
                for lead in leads]

    def __repr__(self):
        return f"Lead('{self.last_name}', '{self.email}', '{self.company_name}')"


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id', ondelete='CASCADE'), nullable=True)
    user = db.relationship('User', backref='comments', lazy=True)

    def __repr__(self):
        return f"Comment('{self.content}', '{self.date_posted}')"
