"""
Market Hours Checker for Trading Platform
Prevents trading during market closures
"""

from datetime import datetime, time
import pytz

def is_stock_market_open():
    """
    Check if US stock market is currently open
    NYSE/NASDAQ trading hours: 9:30 AM - 4:00 PM EST (Monday-Friday)
    """
    try:
        # Get current time in Eastern timezone
        eastern = pytz.timezone('US/Eastern')
        now_eastern = datetime.now(eastern)
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now_eastern.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Market hours: 9:30 AM - 4:00 PM EST
        market_open = time(9, 30)  # 9:30 AM
        market_close = time(16, 0)  # 4:00 PM
        
        current_time = now_eastern.time()
        
        # Check if current time is within market hours
        return market_open <= current_time <= market_close
        
    except Exception as e:
        print(f"Error checking market hours: {e}")
        # In case of error, allow trading (fail-safe)
        return True

def get_market_status():
    """
    Get detailed market status information
    """
    try:
        eastern = pytz.timezone('US/Eastern')
        now_eastern = datetime.now(eastern)
        
        is_open = is_stock_market_open()
        
        # Calculate next market open/close
        if now_eastern.weekday() >= 5:  # Weekend
            # Next Monday 9:30 AM
            days_until_monday = (7 - now_eastern.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 1  # If it's Sunday, next Monday is 1 day
            next_open = now_eastern.replace(hour=9, minute=30, second=0, microsecond=0)
            next_open = next_open.replace(day=now_eastern.day + days_until_monday)
        elif is_open:
            # Market is open, next close is today at 4:00 PM
            next_close = now_eastern.replace(hour=16, minute=0, second=0, microsecond=0)
            return {
                'is_open': True,
                'status': 'Market is OPEN',
                'next_change': 'Market closes',
                'next_time': next_close.strftime('%I:%M %p %Z'),
                'current_time': now_eastern.strftime('%I:%M %p %Z on %A')
            }
        else:
            # Market is closed, check if it's same day or next day
            current_time = now_eastern.time()
            if current_time < time(9, 30):
                # Before market open today
                next_open = now_eastern.replace(hour=9, minute=30, second=0, microsecond=0)
            else:
                # After market close, next open is tomorrow (or Monday if Friday)
                if now_eastern.weekday() == 4:  # Friday
                    next_open = now_eastern.replace(hour=9, minute=30, second=0, microsecond=0)
                    next_open = next_open.replace(day=now_eastern.day + 3)  # Monday
                else:
                    next_open = now_eastern.replace(hour=9, minute=30, second=0, microsecond=0)
                    next_open = next_open.replace(day=now_eastern.day + 1)  # Tomorrow
        
        return {
            'is_open': False,
            'status': 'Market is CLOSED',
            'next_change': 'Market opens',
            'next_time': next_open.strftime('%I:%M %p %Z on %A'),
            'current_time': now_eastern.strftime('%I:%M %p %Z on %A')
        }
        
    except Exception as e:
        print(f"Error getting market status: {e}")
        return {
            'is_open': True,
            'status': 'Market status unknown',
            'next_change': 'Unable to determine',
            'next_time': 'N/A',
            'current_time': 'N/A'
        }

def is_instrument_tradeable(instrument_type):
    """
    Check if a specific instrument type can be traded right now
    """
    if instrument_type.lower() == 'stock':
        return is_stock_market_open()
    
    # Crypto, Forex, Commodities can be traded 24/7 (or have different hours)
    # For now, allow all non-stock instruments
    return True

# Market holidays (add more as needed)
MARKET_HOLIDAYS = [
    # 2024 holidays (update yearly)
    "2024-01-01",  # New Year's Day
    "2024-01-15",  # Martin Luther King Jr. Day
    "2024-02-19",  # Presidents' Day
    "2024-03-29",  # Good Friday
    "2024-05-27",  # Memorial Day
    "2024-06-19",  # Juneteenth
    "2024-07-04",  # Independence Day
    "2024-09-02",  # Labor Day
    "2024-11-28",  # Thanksgiving
    "2024-12-25",  # Christmas
    
    # 2025 holidays
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # Martin Luther King Jr. Day
    "2025-02-17",  # Presidents' Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving
    "2025-12-25",  # Christmas
]

def is_market_holiday():
    """Check if today is a market holiday"""
    try:
        eastern = pytz.timezone('US/Eastern')
        today = datetime.now(eastern).strftime('%Y-%m-%d')
        return today in MARKET_HOLIDAYS
    except:
        return False
