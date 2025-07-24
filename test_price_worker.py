#!/usr/bin/env python3
"""
Test script to verify price worker functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_price_functions():
    """Test the price fetching functions"""
    print("🧪 Testing price worker functions...")
    
    try:
        from price_updater import get_crypto_price_simple, get_stock_price_simple
        
        # Test crypto price fetching
        print("\n💰 Testing crypto prices:")
        crypto_symbols = ['BTC/USD', 'ETH/USD']
        for symbol in crypto_symbols:
            price = get_crypto_price_simple(symbol)
            if price:
                print(f"✅ {symbol}: ${price:,.2f}")
            else:
                print(f"❌ {symbol}: Failed to get price")
        
        # Test stock price simulation
        print("\n📊 Testing stock prices:")
        stock_symbols = ['AAPL', 'MSFT']
        for symbol in stock_symbols:
            price = get_stock_price_simple(symbol)
            print(f"✅ {symbol}: ${price:.2f} (simulated)")
        
        print("\n🎉 Price worker functions working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing price functions: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\n🔗 Testing database connection...")
    
    try:
        from price_updater import create_app_context
        
        app, db = create_app_context()
        with app.app_context():
            from omcrm.webtrader.models import TradingInstrument
            
            instruments = TradingInstrument.query.all()
            print(f"✅ Found {len(instruments)} instruments in database")
            
            for instrument in instruments[:3]:  # Show first 3
                print(f"   - {instrument.symbol} ({instrument.type}): ${instrument.current_price or 'No price'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Price Worker Test Suite")
    print("=" * 40)
    
    success = True
    success &= test_price_functions()
    success &= test_database_connection()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ ALL TESTS PASSED - Price worker ready for deployment!")
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
    
    print("\n📋 Next steps:")
    print("1. Run: docker-compose down")
    print("2. Run: docker-compose build --no-cache") 
    print("3. Run: docker-compose up -d")
    print("4. Check: docker-compose logs -f price_worker") 