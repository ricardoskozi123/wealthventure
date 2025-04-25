from datetime import datetime
from omcrm import db


class Deposit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(20), nullable=False)  # 'crypto', 'wire', 'card', etc.
    crypto_type = db.Column(db.String(20), nullable=True)  # 'BTC', 'ETH', etc.
    reference = db.Column(db.String(100), nullable=True)  # Transaction reference or ID
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'approved', 'rejected'
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    processed_date = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    lead = db.relationship('Lead', backref=db.backref('deposits', lazy=True))
    processor = db.relationship('User', backref=db.backref('processed_deposits', lazy=True))
    
    def __repr__(self):
        return f"Deposit(id={self.id}, lead_id={self.lead_id}, amount=${self.amount:.2f}, status={self.status})"
    
    def approve(self, user_id):
        """Approve a deposit and update client balance"""
        if self.status != 'pending':
            return False
        
        self.status = 'approved'
        self.processed_date = datetime.utcnow()
        self.processed_by = user_id
        
        # Update client balance
        if self.lead:
            self.lead.update_balance(self.amount)
        
        db.session.commit()
        return True
    
    def reject(self, user_id):
        """Reject a deposit request"""
        if self.status != 'pending':
            return False
        
        self.status = 'rejected'
        self.processed_date = datetime.utcnow()
        self.processed_by = user_id
        
        db.session.commit()
        return True


class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(20), nullable=False)  # 'crypto', 'wire', etc.
    
    # Crypto-specific fields
    crypto_type = db.Column(db.String(20), nullable=True)  # 'BTC', 'ETH', etc.
    wallet_address = db.Column(db.String(255), nullable=True)
    
    # Bank-specific fields
    bank_name = db.Column(db.String(100), nullable=True)
    account_holder = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(50), nullable=True)
    swift_code = db.Column(db.String(20), nullable=True)
    
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'approved', 'rejected'
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    processed_date = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reference = db.Column(db.String(100), nullable=True)  # Transaction reference or ID
    
    # Relationships
    lead = db.relationship('Lead', backref=db.backref('withdrawals', lazy=True))
    processor = db.relationship('User', backref=db.backref('processed_withdrawals', lazy=True))
    
    def __repr__(self):
        return f"Withdrawal(id={self.id}, lead_id={self.lead_id}, amount=${self.amount:.2f}, status={self.status})"
    
    def approve(self, user_id, reference=None):
        """Approve a withdrawal and update client balance"""
        if self.status != 'pending':
            return False
        
        # Check if client has sufficient balance
        if self.lead and self.lead.current_balance < self.amount:
            return False
        
        self.status = 'approved'
        self.processed_date = datetime.utcnow()
        self.processed_by = user_id
        
        if reference:
            self.reference = reference
        
        # Update client balance
        if self.lead:
            self.lead.update_balance(-self.amount)
        
        db.session.commit()
        return True
    
    def reject(self, user_id, reason=None):
        """Reject a withdrawal request"""
        if self.status != 'pending':
            return False
        
        self.status = 'rejected'
        self.processed_date = datetime.utcnow()
        self.processed_by = user_id
        
        if reason:
            self.notes = f"{self.notes or ''}\n\nRejection reason: {reason}".strip()
        
        db.session.commit()
        return True 