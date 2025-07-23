#!/usr/bin/env python3
"""
Test script to verify the real-time websocket implementation
"""

import asyncio
import websocket
import json
import threading
import time
from omcrm.webtrader.realtime_data import real_time_manager

def test_binance_websocket():
    """Test Binance WebSocket connection"""
    print("Testing Binance WebSocket...")
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            symbol = data.get('s', '').replace('USDT', '')
            price = float(data.get('c', 0))
            change_24h = float(data.get('P', 0))
            print(f"Binance: {symbol} = ${price:.2f} ({change_24h:+.2f}%)")
        except Exception as e:
            print(f"Error parsing Binance data: {e}")

    def on_error(ws, error):
        print(f"Binance WebSocket error: {error}")

    def on_close(ws, close_status_code, close_msg):
        print("Binance WebSocket connection closed")

    def on_open(ws):
        print("Binance WebSocket connection opened")

    # Test with Bitcoin ticker
    ws_url = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
    ws = websocket.WebSocketApp(ws_url,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close,
                              on_open=on_open)
    
    # Run for 10 seconds
    def stop_after_delay():
        time.sleep(10)
        ws.close()
    
    threading.Thread(target=stop_after_delay, daemon=True).start()
    ws.run_forever()

def test_real_time_manager():
    """Test the RealTimeDataManager"""
    print("\nTesting RealTimeDataManager...")
    
    # Test callback
    def price_callback(update_data):
        print(f"Price update: {update_data}")
    
    real_time_manager.add_price_callback(price_callback)
    
    # Test instruments
    test_instruments = [
        {'id': 1, 'symbol': 'BTC', 'name': 'Bitcoin', 'type': 'crypto'},
        {'id': 2, 'symbol': 'ETH', 'name': 'Ethereum', 'type': 'crypto'},
        {'id': 3, 'symbol': 'AAPL', 'name': 'Apple Inc.', 'type': 'stock'}
    ]
    
    print("Starting real-time feeds...")
    real_time_manager.start_real_time_feeds(test_instruments)
    
    # Let it run for 30 seconds
    print("Collecting data for 30 seconds...")
    time.sleep(30)
    
    print("Stopping real-time feeds...")
    real_time_manager.stop_real_time_feeds()
    
    # Show cached data
    print("\nCached price data:")
    for symbol, data in real_time_manager.price_cache.items():
        print(f"  {symbol}: {data}")

def test_connection_status():
    """Test connection status reporting"""
    print("\nTesting connection status...")
    status = real_time_manager.get_connection_status()
    
    print("Connection Status:")
    for api_name, api_status in status.items():
        print(f"  {api_name}: Active={api_status['active']}, Type={api_status['type']}")

if __name__ == "__main__":
    print("=== Real-time WebSocket Testing ===\n")
    
    # Test 1: Direct Binance WebSocket
    try:
        test_binance_websocket()
    except Exception as e:
        print(f"Binance test failed: {e}")
    
    # Test 2: Real-time manager
    try:
        test_real_time_manager()
    except Exception as e:
        print(f"Real-time manager test failed: {e}")
    
    # Test 3: Connection status
    try:
        test_connection_status()
    except Exception as e:
        print(f"Connection status test failed: {e}")
    
    print("\n=== Testing Complete ===")
    print("\nTo run the Flask app with real-time features:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Start the Flask app: python manage.py run")
    print("3. Navigate to /webtrader/dashboard")
    print("4. Open browser console to see real-time price updates")
    print("5. Check the real-time feed status at /webtrader/realtime_status") 