"""
Market Hours Utility for Wealth Venture Trading Platform
========================================================

Checks if stock markets are open and provides trading session information.
"""

from datetime import datetime, time, date
import pytz
from typing import Dict, Tuple, Optional
import requests
import json
from functools import lru_cache

class MarketHoursChecker:
    """Check if stock markets are open for trading"""
    
    def __init__(self):
        # Market timezones
        self.timezones = {
            'US': pytz.timezone('US/Eastern'),
            'UK': pytz.timezone('Europe/London'),
            'EU': pytz.timezone('Europe/Frankfurt'),
            'ASIA': pytz.timezone('Asia/Tokyo')
        }
        
        # US Market Hours (Eastern Time)
        self.us_market_hours = {
            'pre_market_start': time(4, 0),      # 4:00 AM
            'regular_start': time(9, 30),       # 9:30 AM
            'regular_end': time(16, 0),         # 4:00 PM
            'after_hours_end': time(20, 0)      # 8:00 PM
        }
        
        # US Market Holidays 2024-2025 (add more as needed)
        self.us_holidays = {
            # 2024
            date(2024, 1, 1),   # New Year's Day
            date(2024, 1, 15),  # MLK Day
            date(2024, 2, 19),  # Presidents Day
            date(2024, 3, 29),  # Good Friday
            date(2024, 5, 27),  # Memorial Day
            date(2024, 6, 19),  # Juneteenth
            date(2024, 7, 4),   # Independence Day
            date(2024, 9, 2),   # Labor Day
            date(2024, 11, 28), # Thanksgiving
            date(2024, 12, 25), # Christmas
            
            # 2025
            date(2025, 1, 1),   # New Year's Day
            date(2025, 1, 20),  # MLK Day
            date(2025, 2, 17),  # Presidents Day
            date(2025, 4, 18),  # Good Friday
            date(2025, 5, 26),  # Memorial Day
            date(2025, 6, 19),  # Juneteenth
            date(2025, 7, 4),   # Independence Day
            date(2025, 9, 1),   # Labor Day
            date(2025, 11, 27), # Thanksgiving
            date(2025, 12, 25), # Christmas
        }
    
    def get_current_time_et(self) -> datetime:
        """Get current time in Eastern Time"""
        return datetime.now(self.timezones['US'])
    
    def is_market_holiday(self, check_date: date = None) -> bool:
        """Check if given date is a market holiday"""
        if check_date is None:
            check_date = self.get_current_time_et().date()
        
        return check_date in self.us_holidays
    
    def is_weekend(self, check_date: date = None) -> bool:
        """Check if given date is weekend"""
        if check_date is None:
            check_date = self.get_current_time_et().date()
        
        return check_date.weekday() >= 5  # Saturday = 5, Sunday = 6
    
    def get_market_status(self) -> Dict:
        """
        Get comprehensive market status
        
        Returns:
            Dict with market status information
        """
        now_et = self.get_current_time_et()
        current_date = now_et.date()
        current_time = now_et.time()
        
        # Check if market is closed due to weekend or holiday
        if self.is_weekend(current_date):
            next_open = self._get_next_market_open(now_et)
            return {
                'is_open': False,
                'status': 'CLOSED_WEEKEND',
                'message': 'Market is closed for the weekend',
                'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'next_open': next_open.strftime('%Y-%m-%d %H:%M:%S %Z') if next_open else None,
                'session': 'CLOSED'
            }
        
        if self.is_market_holiday(current_date):
            next_open = self._get_next_market_open(now_et)
            return {
                'is_open': False,
                'status': 'CLOSED_HOLIDAY',
                'message': 'Market is closed for holiday',
                'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'next_open': next_open.strftime('%Y-%m-%d %H:%M:%S %Z') if next_open else None,
                'session': 'CLOSED'
            }
        
        # Check trading sessions
        if current_time < self.us_market_hours['pre_market_start']:
            # Before pre-market
            next_open = now_et.replace(
                hour=self.us_market_hours['pre_market_start'].hour,
                minute=self.us_market_hours['pre_market_start'].minute,
                second=0, microsecond=0
            )
            return {
                'is_open': False,
                'status': 'CLOSED_OVERNIGHT',
                'message': 'Market opens at 4:00 AM ET (Pre-market)',
                'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'next_open': next_open.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'session': 'CLOSED'
            }
        
        elif current_time < self.us_market_hours['regular_start']:
            # Pre-market hours
            return {
                'is_open': True,
                'status': 'PRE_MARKET',
                'message': 'Pre-market trading is open (4:00 AM - 9:30 AM ET)',
                'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'next_open': None,
                'session': 'PRE_MARKET',
                'regular_open_at': now_et.replace(
                    hour=self.us_market_hours['regular_start'].hour,
                    minute=self.us_market_hours['regular_start'].minute,
                    second=0, microsecond=0
                ).strftime('%Y-%m-%d %H:%M:%S %Z')
            }
        
        elif current_time < self.us_market_hours['regular_end']:
            # Regular market hours
            return {
                'is_open': True,
                'status': 'REGULAR_HOURS',
                'message': 'Regular market hours (9:30 AM - 4:00 PM ET)',
                'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'next_open': None,
                'session': 'REGULAR',
                'market_close_at': now_et.replace(
                    hour=self.us_market_hours['regular_end'].hour,
                    minute=self.us_market_hours['regular_end'].minute,
                    second=0, microsecond=0
                ).strftime('%Y-%m-%d %H:%M:%S %Z')
            }
        
        elif current_time < self.us_market_hours['after_hours_end']:
            # After-hours trading
            return {
                'is_open': True,
                'status': 'AFTER_HOURS',
                'message': 'After-hours trading (4:00 PM - 8:00 PM ET)',
                'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'next_open': None,
                'session': 'AFTER_HOURS',
                'after_hours_end_at': now_et.replace(
                    hour=self.us_market_hours['after_hours_end'].hour,
                    minute=self.us_market_hours['after_hours_end'].minute,
                    second=0, microsecond=0
                ).strftime('%Y-%m-%d %H:%M:%S %Z')
            }
        
        else:
            # After 8 PM - market closed until next day
            next_open = self._get_next_market_open(now_et)
            return {
                'is_open': False,
                'status': 'CLOSED_OVERNIGHT',
                'message': 'Market is closed until next trading day',
                'current_time_et': now_et.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'next_open': next_open.strftime('%Y-%m-%d %H:%M:%S %Z') if next_open else None,
                'session': 'CLOSED'
            }
    
    def _get_next_market_open(self, from_time: datetime) -> Optional[datetime]:
        """Get the next time the market opens"""
        current_date = from_time.date()
        
        # Try next 10 days to find next market open
        for days_ahead in range(1, 11):
            check_date = current_date + datetime.timedelta(days=days_ahead)
            
            # Skip weekends and holidays
            if not self.is_weekend(check_date) and not self.is_market_holiday(check_date):
                next_open = datetime.combine(
                    check_date, 
                    self.us_market_hours['pre_market_start']
                )
                return self.timezones['US'].localize(next_open)
        
        return None
    
    def is_trading_allowed(self, allow_pre_market: bool = False, allow_after_hours: bool = False) -> Tuple[bool, str]:
        """
        Check if trading should be allowed based on market status
        
        Args:
            allow_pre_market: Allow trading during pre-market hours
            allow_after_hours: Allow trading during after-hours
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        status = self.get_market_status()
        
        if not status['is_open']:
            return False, status['message']
        
        session = status['session']
        
        if session == 'REGULAR':
            return True, "Regular market hours - trading allowed"
        
        elif session == 'PRE_MARKET':
            if allow_pre_market:
                return True, "Pre-market trading allowed"
            else:
                return False, "Pre-market trading not enabled"
        
        elif session == 'AFTER_HOURS':
            if allow_after_hours:
                return True, "After-hours trading allowed"
            else:
                return False, "After-hours trading not enabled"
        
        return False, "Trading not allowed at this time"

# Global instance
market_checker = MarketHoursChecker()

# Convenience functions
def is_market_open() -> bool:
    """Quick check if market is open (regular hours only)"""
    status = market_checker.get_market_status()
    return status['is_open'] and status['session'] == 'REGULAR'

def get_market_status() -> Dict:
    """Get current market status"""
    return market_checker.get_market_status()

def can_trade(allow_extended_hours: bool = False) -> Tuple[bool, str]:
    """Check if trading is allowed"""
    return market_checker.is_trading_allowed(
        allow_pre_market=allow_extended_hours,
        allow_after_hours=allow_extended_hours
    )