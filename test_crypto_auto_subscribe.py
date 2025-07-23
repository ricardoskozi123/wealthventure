#!/usr/bin/env python3
"""
Test script to demonstrate auto-subscription to all crypto instruments
"""

import time
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_crypto_auto_subscribe():
    """Test the enhanced auto-subscription feature"""
    print("=== TESTING CRYPTO AUTO-SUBSCRIPTION ===\n")
    
    try:
        from omcrm.webtrader.realtime_data import real_time_manager
        
        print("🔧 Testing enhanced symbol mapping...")
        
        # Test symbol mappings
        test_symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD', 'ADA/USD']
        for symbol in test_symbols:
            if symbol in real_time_manager.crypto_symbol_mapping:
                binance_symbol = real_time_manager.crypto_symbol_mapping[symbol]
                print(f"  ✅ {symbol} → {binance_symbol}")
            else:
                print(f"  ❌ {symbol} → NO MAPPING")
        
        print(f"\n📊 Total crypto mappings: {len(real_time_manager.crypto_symbol_mapping)}")
        print(f"📊 Reverse mappings: {len(real_time_manager.binance_to_db_mapping)}")
        
        # Test database access (if available)
        print(f"\n🗄️  Testing database access...")
        try:
            crypto_instruments = real_time_manager.get_all_crypto_instruments_from_db()
            print(f"  ✅ Found {len(crypto_instruments)} crypto instruments in database")
            for instrument in crypto_instruments[:5]:  # Show first 5
                print(f"     - {instrument['symbol']} ({instrument['name']})")
            if len(crypto_instruments) > 5:
                print(f"     ... and {len(crypto_instruments) - 5} more")
        except Exception as e:
            print(f"  ⚠️  Database not accessible: {e}")
            print(f"     (This is normal if Flask app is not running)")
        
        # Test auto-subscription
        print(f"\n🚀 Testing auto-subscription...")
        try:
            success = real_time_manager.auto_subscribe_all_crypto()
            if success:
                print(f"  ✅ Auto-subscription successful!")
                
                # Wait for connections
                print(f"  ⏳ Waiting 3 seconds for WebSocket connections...")
                time.sleep(3)
                
                # Check connection status
                status = real_time_manager.get_connection_status()
                binance_active = status.get('binance', {}).get('active', False)
                print(f"  📡 Binance WebSocket active: {binance_active}")
                
                # Check cached prices
                cached_count = len(real_time_manager.price_cache)
                print(f"  💰 Cached prices: {cached_count}")
                
                if cached_count > 0:
                    print(f"  📈 Sample prices:")
                    for symbol, data in list(real_time_manager.price_cache.items())[:3]:
                        price = data.get('price', 'N/A')
                        change = data.get('change_24h', 0)
                        print(f"     - {symbol}: ${price:,.2f} ({change:+.2f}%)")
                
            else:
                print(f"  ❌ Auto-subscription failed")
                
        except Exception as e:
            print(f"  ❌ Auto-subscription error: {e}")
        
        print(f"\n=== TEST COMPLETE ===")
        
        if real_time_manager.is_running:
            print(f"\n🛑 Stopping real-time feeds...")
            real_time_manager.stop_real_time_feeds()
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"   Make sure you're in the correct directory with the Flask app")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_crypto_auto_subscribe() 