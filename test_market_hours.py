#!/usr/bin/env python3
"""
Test Market Hours Functionality
===============================

Quick test script to verify market hours checking works correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from omcrm.utils.market_hours import MarketHoursChecker, get_market_status, can_trade, is_market_open

def test_market_hours():
    """Test the market hours functionality"""
    
    print("🧪 Testing Market Hours Functionality")
    print("=" * 50)
    
    # Create checker instance
    checker = MarketHoursChecker()
    
    # Test current time
    current_time = checker.get_current_time_et()
    print(f"📅 Current Time (ET): {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"📅 Current Date: {current_time.date()}")
    print(f"📅 Day of Week: {current_time.strftime('%A')}")
    
    # Test holiday check
    is_holiday = checker.is_market_holiday()
    print(f"🎄 Is Holiday: {is_holiday}")
    
    # Test weekend check
    is_weekend = checker.is_weekend()
    print(f"📅 Is Weekend: {is_weekend}")
    
    print("\n" + "=" * 50)
    
    # Test market status
    status = get_market_status()
    print("📊 Market Status:")
    print(f"   Is Open: {status['is_open']}")
    print(f"   Status: {status['status']}")
    print(f"   Session: {status['session']}")
    print(f"   Message: {status['message']}")
    
    if 'next_open' in status and status['next_open']:
        print(f"   Next Open: {status['next_open']}")
    
    print("\n" + "=" * 50)
    
    # Test trading permissions
    can_trade_regular, reason_regular = can_trade(allow_extended_hours=False)
    print("🔒 Trading Permissions (Regular Hours Only):")
    print(f"   Can Trade: {can_trade_regular}")
    print(f"   Reason: {reason_regular}")
    
    can_trade_extended, reason_extended = can_trade(allow_extended_hours=True)
    print("\n🔓 Trading Permissions (Extended Hours):")
    print(f"   Can Trade: {can_trade_extended}")
    print(f"   Reason: {reason_extended}")
    
    print("\n" + "=" * 50)
    
    # Test simple market open check
    market_open = is_market_open()
    print(f"📈 Simple Market Open Check: {market_open}")
    
    print("\n✅ Market Hours Test Complete!")
    
    return status

if __name__ == "__main__":
    try:
        test_market_hours()
    except Exception as e:
        print(f"❌ Error testing market hours: {e}")
        import traceback
        traceback.print_exc()
