#!/usr/bin/env python3
"""
Simple crypto WebSocket test that bypasses database issues
Tests with common crypto symbols that should be in your database
"""

import time
import json
import logging
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

def test_crypto_websocket_simple():
    """Test WebSocket with common crypto symbols (bypassing database)"""
    
    print("🔍 Testing Crypto WebSocket (Bypassing Database)...")
    
    # Common crypto symbols that should be in your database
    # These are the symbols your app would typically have
    test_crypto_symbols = [
        'BTC/USD',   # Bitcoin
        'ETH/USD',   # Ethereum  
        'SOL/USD',   # Solana
        'BNB/USD',   # Binance Coin
        'ADA/USD',   # Cardano
        'DOT/USD',   # Polkadot
        'AVAX/USD',  # Avalanche
        'MATIC/USD', # Polygon
        'TON/USD',   # Toncoin
    ]
    
    print(f"📊 Testing with common crypto symbols:")
    for symbol in test_crypto_symbols:
        print(f"   - {symbol}")
    
    # Convert to Binance symbols (exactly like your app does)
    binance_symbols = []
    for symbol in test_crypto_symbols:
        if '/' in symbol:
            # Convert BTC/USD -> btcusdt
            base_symbol = symbol.split('/')[0].lower()
            binance_symbol = f"{base_symbol}usdt"
            binance_symbols.append(binance_symbol)
            print(f"📈 Mapping {symbol} → {binance_symbol}")
    
    print(f"\n🚀 Starting WebSocket for symbols: {binance_symbols}")
    start_test_websocket(binance_symbols)

def start_test_websocket(binance_symbols):
    """Start WebSocket using EXACT same code as routes.py"""
    
    # Global cache (same as routes.py)
    crypto_price_cache = {}
    
    # Create WebSocket URL for multiple symbols (exact same pattern)
    streams = [f"{symbol}@ticker" for symbol in binance_symbols]
    ws_url = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
    
    print(f"🔗 Connecting to Binance WebSocket...")
    print(f"📊 Subscribing to: {', '.join(binance_symbols)}")
    print(f"🌐 URL: {ws_url[:80]}..." if len(ws_url) > 80 else f"🌐 URL: {ws_url}")
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            
            # Handle single stream data (exact same pattern)
            if 'stream' in data and 'data' in data:
                ticker_data = data['data']
            else:
                ticker_data = data
            
            symbol = ticker_data.get('s', 'UNKNOWN')
            price = float(ticker_data.get('c', 0))
            change_24h = float(ticker_data.get('P', 0))
            
            # Convert BTCUSDT -> BTC/USD for database lookup
            if symbol.endswith('USDT'):
                base_symbol = symbol.replace('USDT', '')
                db_symbol = f"{base_symbol}/USD"
                
                # Cache the price data
                crypto_price_cache[db_symbol] = {
                    'price': price,
                    'change_24h': change_24h,
                    'timestamp': time.time()
                }
                
                color = "🟢" if change_24h >= 0 else "🔴"
                print(f"{color} {db_symbol}: ${price:,.6f} ({change_24h:+.2f}%)")
                
        except Exception as e:
            print(f"❌ Error parsing WebSocket message: {e}")
    
    def on_error(ws, error):
        print(f"❌ WebSocket Error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 WebSocket Closed: {close_status_code} - {close_msg}")
    
    def on_open(ws):
        print(f"✅ WebSocket Connected Successfully!")
        print(f"💰 Receiving unlimited free real-time crypto prices...")
        print("-" * 50)
    
    # Create WebSocket connection (exact same pattern)
    import websocket
    crypto_ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    
    # Run WebSocket for 15 seconds to test
    def run_websocket():
        crypto_ws.run_forever()
    
    ws_thread = threading.Thread(target=run_websocket, daemon=True)
    ws_thread.start()
    
    print("🚀 WebSocket thread started!")
    print("⏳ Running for 15 seconds to test...")
    
    # Wait 15 seconds then show results
    time.sleep(15)
    
    print("\n" + "="*50)
    print("📋 RESULTS:")
    print(f"💰 Cached prices count: {len(crypto_price_cache)}")
    
    if crypto_price_cache:
        print("✅ WebSocket is working! Cached prices:")
        for symbol, data in crypto_price_cache.items():
            price = data['price']
            change = data['change_24h']
            age = time.time() - data['timestamp']
            print(f"   {symbol}: ${price:,.6f} ({change:+.2f}%) - {age:.1f}s ago")
        
        print(f"\n🎉 SUCCESS! Your WebSocket implementation is working correctly!")
        print(f"📝 This means the issue is likely with:")
        print(f"   1. No crypto instruments in your database with type='crypto'")
        print(f"   2. The auto-start code in webtrader_dashboard() not running")
        print(f"   3. The get_cached_crypto_price() function not finding cached data")
        
    else:
        print("❌ No prices received. WebSocket may not be connecting.")
        print("🔍 Check your internet connection and firewall settings.")
    
    # Close WebSocket
    crypto_ws.close()
    print("\n🔌 WebSocket test complete!")

if __name__ == "__main__":
    test_crypto_websocket_simple() 