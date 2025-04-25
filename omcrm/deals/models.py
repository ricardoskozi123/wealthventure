from datetime import datetime
from omcrm import db


class DealStage(db.Model):
    id = db.Column(db.Integer, db.Sequence('deal_stage_id_seq'), primary_key=True)
    stage_name = db.Column(db.String(20), nullable=False)
    display_order = db.Column(db.Integer, nullable=False)
    close_type = db.Column(db.String(10), nullable=True, default=None)
    deals = db.relationship(
        'Deal',
        backref='dealstage',
        lazy=True
    )

    @staticmethod
    def deal_stage_list_query():
        return DealStage.query

    @staticmethod
    def get_label(deal_stage):
        return deal_stage.stage_name

    @staticmethod
    def get_deal_stage(deal_stage_id):
        return DealStage.query.filter_by(id=deal_stage_id).first()

    @staticmethod
    def get_by_id(deal_stage_id):
        """Get a deal stage by ID with proper error handling."""
        if deal_stage_id is None:
            return None
        try:
            return DealStage.query.get(deal_stage_id)
        except Exception:
            return None

    def __repr__(self):
        return f"DealStage('{self.stage_name}')"


class Deal(db.Model):
    id = db.Column(db.Integer, db.Sequence('deal_id_seq'), primary_key=True)
    title = db.Column(db.String(100), nullable=True)
    expected_close_price = db.Column(db.Float, nullable=False)
    expected_close_date = db.Column(db.DateTime, nullable=True)
    deal_stage_id = db.Column(db.Integer, db.ForeignKey('deal_stage.id', ondelete='SET NULL'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('lead.id', ondelete='cascade'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    notes = db.Column(db.String(200), nullable=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    probability = db.Column(db.Integer, nullable=False, default=50)  # Default 50% probability

    deal_stage = db.relationship('DealStage', backref='deal', uselist=False, lazy=True)
    # Fix circular import by using simple string reference and removing backref
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_deals', uselist=False, lazy=True)
    client = db.relationship('Lead', backref='deals', uselist=False, lazy=True)
    
    @property
    def deal_owner(self):
        return self.owner

    def is_expired(self):
        today = datetime.today()
        if self.expected_close_date < today:
            return True
        return False

    @staticmethod
    def get_deal(deal_id):
        return Deal.query.filter_by(id=deal_id).first()

    def __repr__(self):
        return f"Deal('{self.title}', '{self.deal_stage_id}', '{self.client_id}', '{self.owner_id}')"
