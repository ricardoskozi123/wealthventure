# omcrm/webtrader/models.py

from datetime import datetime, time
from omcrm import db
import pytz
import logging
logging.basicConfig(level=logging.DEBUG)

class TradingInstrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # forex, crypto, stock, commodity
    current_price = db.Column(db.Float, nullable=True)
    change = db.Column(db.Float, nullable=True, default=0.0)
    last_updated = db.Column(db.DateTime, nullable=True)
    
    # Valid instrument types
    VALID_TYPES = ['forex', 'crypto', 'stock', 'commodity']
    
    # Market hours configuration for different exchanges
    MARKET_HOURS = {
        # US Markets (NYSE, NASDAQ)
        'US': {
            'timezone': 'America/New_York',
            'trading_days': [0, 1, 2, 3, 4],  # Monday to Friday
            'sessions': [{'start': time(9, 30), 'end': time(16, 0)}]
        },
        # European Markets
        'LSE': {  # London Stock Exchange
            'timezone': 'Europe/London',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [{'start': time(8, 0), 'end': time(16, 30)}]
        },
        'FSE': {  # Frankfurt Stock Exchange
            'timezone': 'Europe/Berlin',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [{'start': time(8, 0), 'end': time(22, 0)}]
        },
        'SIX': {  # SIX Swiss Exchange
            'timezone': 'Europe/Zurich',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [{'start': time(9, 0), 'end': time(17, 20)}]
        },
        'AEX': {  # Euronext Amsterdam
            'timezone': 'Europe/Amsterdam',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [{'start': time(9, 0), 'end': time(17, 30)}]
        },
        'SSE': {  # Stockholm Stock Exchange
            'timezone': 'Europe/Stockholm',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [{'start': time(9, 0), 'end': time(17, 25)}]
        },
        # Asian Markets
        'TSE': {  # Tokyo Stock Exchange
            'timezone': 'Asia/Tokyo',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [
                {'start': time(9, 0), 'end': time(11, 30)},
                {'start': time(12, 30), 'end': time(15, 0)}
            ]
        },
        'SSE_CN': {  # Shanghai Stock Exchange
            'timezone': 'Asia/Shanghai',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [
                {'start': time(9, 30), 'end': time(11, 30)},
                {'start': time(13, 0), 'end': time(14, 57)}
            ]
        },
        'SZSE': {  # Shenzhen Stock Exchange
            'timezone': 'Asia/Shanghai',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [
                {'start': time(9, 30), 'end': time(11, 30)},
                {'start': time(13, 0), 'end': time(14, 57)}
            ]
        },
        'SEHK': {  # Stock Exchange of Hong Kong
            'timezone': 'Asia/Hong_Kong',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [
                {'start': time(9, 30), 'end': time(12, 0)},
                {'start': time(13, 0), 'end': time(16, 0)}
            ]
        },
        'NSE': {  # National Stock Exchange of India
            'timezone': 'Asia/Kolkata',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [{'start': time(9, 15), 'end': time(15, 30)}]
        },
        'TADAWUL': {  # Saudi Stock Exchange
            'timezone': 'Asia/Riyadh',
            'trading_days': [6, 0, 1, 2, 3],  # Sunday to Thursday
            'sessions': [{'start': time(10, 0), 'end': time(15, 0)}]
        },
        'KRX': {  # Korea Exchange
            'timezone': 'Asia/Seoul',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [{'start': time(9, 0), 'end': time(15, 30)}]
        },
        'TWSE': {  # Taiwan Stock Exchange
            'timezone': 'Asia/Taipei',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [{'start': time(9, 15), 'end': time(13, 30)}]
        },
        # Oceania Markets
        'ASX': {  # Australian Securities Exchange
            'timezone': 'Australia/Sydney',
            'trading_days': [0, 1, 2, 3, 4],
            'sessions': [{'start': time(10, 0), 'end': time(16, 0)}]
        }
    }
    
    # Symbol to exchange mapping for stocks
    STOCK_EXCHANGES = {
        # US Stocks (default)
        'AAPL': 'US', 'MSFT': 'US', 'GOOGL': 'US', 'AMZN': 'US', 'TSLA': 'US',
        'META': 'US', 'NVDA': 'US', 'NFLX': 'US', 'DIS': 'US', 'PYPL': 'US',
        'ADBE': 'US', 'CRM': 'US', 'ZOOM': 'US', 'UBER': 'US', 'SPOT': 'US',
        # Add more symbols as needed
    }

    def __init__(self, **kwargs):
        # Validate instrument type
        if 'type' in kwargs and kwargs['type'] not in self.VALID_TYPES:
            raise ValueError(f"Invalid instrument type. Must be one of: {', '.join(self.VALID_TYPES)}")
        super().__init__(**kwargs)

    def __repr__(self):
        return f'<TradingInstrument {self.symbol}>'

    @property
    def precision(self):
        """Get the appropriate decimal precision for this instrument"""
        if self.type == 'crypto':
            return 6
        elif self.type == 'forex':
            return 5
        elif self.type == 'commodity':
            return 2
        else:  # stocks
            return 2

    @property
    def formatted_price(self):
        """Get formatted price with appropriate precision"""
        if self.current_price is None:
            return "N/A"
        return f"${self.current_price:.{self.precision}f}"

    @property
    def price_change_color(self):
        """Get CSS color class based on price change"""
        if self.change is None:
            return 'text-muted'
        elif self.change > 0:
            return 'text-success'
        elif self.change < 0:
            return 'text-danger'
        else:
            return 'text-muted'

    @property
    def change_direction(self):
        """Get direction indicator for price change"""
        if self.change is None or self.change == 0:
            return '➡️'
        elif self.change > 0:
            return '⬆️'
        else:
            return '⬇️'

    def get_exchange(self):
        """Get the exchange for this instrument"""
        if self.type == 'stock':
            return self.STOCK_EXCHANGES.get(self.symbol, 'US')  # Default to US
        return None
    
    def is_market_open(self):
        """Check if the market is currently open for this instrument"""
        # Forex and crypto markets are always open
        if self.type in ['forex', 'crypto', 'commodity']:
            return True
        
        # For stocks, check market hours
        if self.type == 'stock':
            exchange = self.get_exchange()
            if not exchange or exchange not in self.MARKET_HOURS:
                return True  # Default to open if no market hours defined
            
            market_config = self.MARKET_HOURS[exchange]
            
            try:
                # Get current time in the market's timezone
                market_tz = pytz.timezone(market_config['timezone'])
                current_time = datetime.now(market_tz)
                current_weekday = current_time.weekday()
                current_time_only = current_time.time()
                
                # Check if it's a trading day
                if current_weekday not in market_config['trading_days']:
                    return False
                
                # Check if current time is within trading sessions
                for session in market_config['sessions']:
                    if session['start'] <= current_time_only <= session['end']:
                        return True
                
                return False
                
            except Exception as e:
                # If timezone conversion fails, default to open
                print(f"Error checking market hours for {self.symbol}: {e}")
                return True
        
        return True  # Default to open for unknown types
    
    def get_market_status(self):
        """Get detailed market status information"""
        if self.type in ['forex', 'crypto', 'commodity']:
            return {
                'is_open': True,
                'status': 'Always Open',
                'next_open': None,
                'next_close': None
            }
        
        if self.type == 'stock':
            exchange = self.get_exchange()
            is_open = self.is_market_open()
            
            return {
                'is_open': is_open,
                'status': 'Market Open' if is_open else 'Market Closed',
                'exchange': exchange,
                'timezone': self.MARKET_HOURS.get(exchange, {}).get('timezone', 'UTC')
            }
        
        return {'is_open': True, 'status': 'Unknown', 'exchange': None}

    def update_price(self, new_price):
        """Update price and calculate change"""
        if self.current_price is not None and new_price is not None:
            self.change = new_price - self.current_price
        self.current_price = new_price
        self.last_updated = datetime.utcnow()

    def to_dict(self):
        """Convert instrument to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'type': self.type,
            'current_price': self.current_price,
            'change': self.change,
            'formatted_price': self.formatted_price,
            'price_change_color': self.price_change_color,
            'change_direction': self.change_direction,
            'market_status': self.get_market_status(),
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

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
