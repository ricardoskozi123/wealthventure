#!/usr/bin/env python3
"""
Test WebTrader Market Hours Integration
======================================

Test script to verify market hours integration works in webtrader.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_webtrader_integration():
    """Test that webtrader can import and use market hours"""
    
    print("🧪 Testing WebTrader Market Hours Integration")
    print("=" * 50)
    
    try:
        # Test import
        from omcrm.utils.market_hours import can_trade, get_market_status
        print("✅ Market hours module imported successfully")
        
        # Test basic functionality
        status = get_market_status()
        print(f"📊 Market Status: {status['status']}")
        print(f"📊 Is Open: {status['is_open']}")
        print(f"📊 Session: {status['session']}")
        
        # Test trading check
        can_trade_now, reason = can_trade(allow_extended_hours=False)
        print(f"🔒 Can Trade (Regular): {can_trade_now}")
        print(f"🔒 Reason: {reason}")
        
        can_trade_extended, reason_extended = can_trade(allow_extended_hours=True)
        print(f"🔓 Can Trade (Extended): {can_trade_extended}")
        print(f"🔓 Reason: {reason_extended}")
        
        print("\n✅ WebTrader integration test passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_webtrader_integration()
    sys.exit(0 if success else 1)
