#!/usr/bin/env python3
"""
Simple test to verify Binance WebSocket works independently
This will test the unlimited free Binance WebSocket without Socket.IO
"""

import websocket
import json
import threading
import time

def test_binance_websocket():
    """Test Binance WebSocket for real-time crypto prices"""
    
    # Test symbols (crypto pairs)
    symbols = ['btcusdt', 'ethusdt', 'solusdt']
    
    # Create WebSocket URL for multiple symbols
    streams = [f"{symbol}@ticker" for symbol in symbols]
    ws_url = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
    
    print(f"🔗 Connecting to Binance WebSocket...")
    print(f"📊 Subscribing to: {', '.join(symbols)}")
    print(f"🌐 URL: {ws_url}")
    print("-" * 50)
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            
            # Handle single stream data
            if 'stream' in data and 'data' in data:
                ticker_data = data['data']
            else:
                ticker_data = data
            
            symbol = ticker_data.get('s', 'UNKNOWN')
            price = float(ticker_data.get('c', 0))
            change_24h = float(ticker_data.get('P', 0))
            
            # Clean symbol for display
            clean_symbol = symbol.replace('USDT', '')
            
            # Color coding for price changes
            color = "🟢" if change_24h >= 0 else "🔴"
            
            print(f"{color} {clean_symbol}: ${price:,.6f} ({change_24h:+.2f}%)")
            
        except Exception as e:
            print(f"❌ Error parsing message: {e}")
    
    def on_error(ws, error):
        print(f"❌ WebSocket Error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 WebSocket Closed: {close_status_code} - {close_msg}")
    
    def on_open(ws):
        print(f"✅ WebSocket Connected Successfully!")
        print(f"💰 Receiving unlimited free real-time crypto prices...")
        print("-" * 50)
    
    # Create WebSocket connection
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    
    # Run WebSocket
    try:
        ws.run_forever()
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
        ws.close()

if __name__ == "__main__":
    print("🚀 Testing Binance WebSocket (Unlimited & Free)")
    print("Press Ctrl+C to stop the test")
    print("=" * 50)
    
    test_binance_websocket() 