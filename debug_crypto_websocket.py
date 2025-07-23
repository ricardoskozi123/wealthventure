#!/usr/bin/env python3
"""
Debug script to test crypto WebSocket exactly like the main app
"""

import time
import json
import logging
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

def test_crypto_websocket():
    """Test the exact WebSocket implementation from routes.py"""
    
    print("🔍 Starting Crypto WebSocket Debug...")
    
    # Step 1: Get crypto instruments from database (simulating your app)
    try:
        from omcrm import create_app, db
        from omcrm.webtrader.models import TradingInstrument
        
        app = create_app()
        with app.app_context():
            # Query crypto instruments exactly like your app does
            crypto_instruments = TradingInstrument.query.filter_by(type='crypto').all()
            
            print(f"📊 Found {len(crypto_instruments)} crypto instruments in database:")
            for instrument in crypto_instruments:
                print(f"   ID: {instrument.id}, Symbol: {instrument.symbol}, Name: {instrument.name}, Type: {instrument.type}")
            
            if not crypto_instruments:
                print("❌ No crypto instruments found! This is why WebSocket isn't starting.")
                print("💡 Add some crypto instruments to your database first.")
                return
            
            # Step 2: Convert to Binance symbols (exactly like your app)
            binance_symbols = []
            for instrument in crypto_instruments:
                symbol = instrument.symbol
                if '/' in symbol:
                    # Convert BTC/USD -> btcusdt
                    base_symbol = symbol.split('/')[0].lower()
                    binance_symbol = f"{base_symbol}usdt"
                    binance_symbols.append(binance_symbol)
                    print(f"📈 Mapping {symbol} → {binance_symbol}")
            
            if not binance_symbols:
                print("❌ No valid crypto symbols for Binance WebSocket")
                return
            
            # Step 3: Start WebSocket using exact same code as routes.py
            print(f"\n🚀 Starting WebSocket for symbols: {binance_symbols}")
            start_test_websocket(binance_symbols)
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("💡 Make sure Flask app is properly configured and database exists")

def start_test_websocket(binance_symbols):
    """Start WebSocket using EXACT same code as routes.py"""
    
    # Global cache (same as routes.py)
    crypto_price_cache = {}
    
    # Create WebSocket URL for multiple symbols (exact same pattern)
    streams = [f"{symbol}@ticker" for symbol in binance_symbols]
    ws_url = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
    
    print(f"🔗 Connecting to Binance WebSocket...")
    print(f"📊 Subscribing to: {', '.join(binance_symbols)}")
    print(f"🌐 URL: {ws_url}")
    
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
    else:
        print("❌ No prices received. WebSocket may not be connecting.")
    
    # Close WebSocket
    crypto_ws.close()
    print("\n🔌 WebSocket test complete!")

if __name__ == "__main__":
    test_crypto_websocket() 