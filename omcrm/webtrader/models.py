# omcrm/webtrader/models.py

from datetime import datetime

from omcrm import db
import logging
logging.basicConfig(level=logging.DEBUG)

class TradingInstrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    previous_price = db.Column(db.Float, nullable=True, default=None)  # Added for change calculation
    change = db.Column(db.Float, nullable=True, default=0.0)  # Percentage change
    type = db.Column(db.String(10), nullable=False)  # 'stock' or 'crypto'
    last_updated = db.Column(db.DateTime, nullable=True)

    def update_price(self, new_price):
        """Update the price and calculate the change percentage"""
        try:
            if self.current_price is not None:
                # Store current price as previous price
                self.previous_price = self.current_price
                
                # Calculate percentage change
                percentage_change = ((new_price - self.current_price) / self.current_price) * 100
                self.change = round(percentage_change, 2)
            else:
                # If this is the first price update, there's no change to calculate
                self.previous_price = new_price  # Set both to the same value
                self.change = 0.0  # No change for first update
        except Exception as e:
            # If any error occurs, just update price without change
            logging.warning(f"Error calculating price change: {str(e)}")
            self.change = 0.0
        
        # Always update the current price
        self.current_price = new_price
        self.last_updated = datetime.utcnow()

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    instrument_id = db.Column(db.Integer, db.ForeignKey('trading_instrument.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    trade_type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    opening_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    closing_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(10), nullable=False, default='open')
    closing_price = db.Column(db.Float, nullable=True)
    profit_loss = db.Column(db.Float, nullable=True)
    order_type = db.Column(db.String(20), nullable=False, default='market')  # New field for order type
    target_price = db.Column(db.Float, nullable=True)  # New field for target price
    notes = db.Column(db.Text, nullable=True)  # Add notes field for trade journaling
    leverage = db.Column(db.Float, nullable=False, default=5.0)  # Default leverage is 5x

    lead = db.relationship('Lead', back_populates='trades')
    instrument = db.relationship('TradingInstrument', backref=db.backref('trades', lazy=True))

    def calculate_profit_loss(self):
        if self.status == 'closed' and self.closing_price is not None:
            if self.trade_type == 'buy':  # Long position
                self.profit_loss = (self.closing_price - self.price) * self.amount
            elif self.trade_type == 'sell':  # Short position
                self.profit_loss = (self.price - self.closing_price) * self.amount
        else:
            self.profit_loss = 0.0  # Default to 0 if not calculated
        return self.profit_loss
    
    def calculate_roi(self):
        """Calculate Return on Investment (ROI) as a percentage"""
        if self.status == 'closed' and self.profit_loss is not None:
            investment = self.price * self.amount
            if investment > 0:
                return (self.profit_loss / investment) * 100
        return 0.0
    
    def get_holding_period(self):
        """Calculate the holding period of the trade"""
        if self.status == 'closed' and self.closing_date:
            opening = self.opening_date if self.opening_date else self.date
            delta = self.closing_date - opening
            # Format nicely (e.g., "2 days, 3 hours")
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            if days > 0:
                return f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''}"
            elif hours > 0:
                return f"{hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''}"
            else:
                return f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif self.status == 'open':
            opening = self.opening_date if self.opening_date else self.date
            delta = datetime.utcnow() - opening
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            if days > 0:
                return f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''} (open)"
            elif hours > 0:
                return f"{hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''} (open)"
            else:
                return f"{minutes} minute{'s' if minutes != 1 else ''} (open)"
        return "N/A"
