#!/usr/bin/env python3
"""Simple test for crypto auto-subscription"""

import time

def test_crypto_subscription():
    print("🚀 Testing Enhanced Crypto WebSocket System")
    
    from omcrm.webtrader.realtime_data import real_time_manager
    
    # Test symbol mappings
    print("\n📊 Symbol Mappings:")
    mappings = real_time_manager.crypto_symbol_mapping
    for db_symbol, binance_symbol in list(mappings.items())[:8]:
        print(f"  {db_symbol} → {binance_symbol}")
    
    print(f"\nTotal mappings: {len(mappings)}")
    
    # Test Binance WebSocket
    print("\n🔌 Starting Binance WebSocket...")
    crypto_symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'ADA']
    real_time_manager.start_binance_crypto_stream(crypto_symbols)
    
    # Wait for data
    print("⏳ Waiting 5 seconds for real-time data...")
    time.sleep(5)
    
    # Show results
    print(f"\n💰 Real-time Prices:")
    cached = real_time_manager.price_cache
    print(f"Symbols with cached data: {len(cached)}")
    
    for symbol, data in cached.items():
        price = data.get('price', 0)
        change = data.get('change_24h', 0)
        print(f"  {symbol}: ${price:,.2f} ({change:+.2f}%)")
    
    # Connection status
    status = real_time_manager.get_connection_status()
    binance_active = status.get('binance', {}).get('active', False)
    print(f"\n📡 Binance WebSocket Active: {binance_active}")
    
    print("\n✅ Test Complete!")

if __name__ == "__main__":
    test_crypto_subscription() 