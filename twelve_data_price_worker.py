#!/usr/bin/env python3
"""
🚀 INSTANT Twelve Data WebSocket Price Worker
Real-time price updates using Twelve Data WebSocket API
Your API Key: 902d8585e8c040f591a3293d1b79ab88
Pro Plan: 610 API credits/minute, 500 WebSocket credits
"""

import os
import sys
import time
import logging
import requests
import json
import websocket
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from omcrm.webtrader.models import TradingInstrument

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twelve_data_websocket_worker.log'),
        logging.StreamHandler()
    ]
)

class TwelveDataWebSocketWorker:
    def __init__(self):
        self.api_key = '902d8585e8c040f591a3293d1b79ab88'
        self.websocket_url = 'wss://ws.twelvedata.com/v1/quotes/price'
        self.ws = None
        self.app = create_app()
        self.running = False
        
        # Symbol mapping for Twelve Data WebSocket
        self.symbol_mapping = {
            # Forex pairs
            'EUR/USD': 'EUR/USD', 'GBP/USD': 'GBP/USD', 'USD/JPY': 'USD/JPY',
            'USD/CHF': 'USD/CHF', 'AUD/USD': 'AUD/USD', 'USD/CAD': 'USD/CAD',
            'NZD/USD': 'NZD/USD', 'EUR/GBP': 'EUR/GBP', 'EUR/JPY': 'EUR/JPY',
            'GBP/JPY': 'GBP/JPY', 'EUR/CHF': 'EUR/CHF', 'GBP/CHF': 'GBP/CHF',
            
            # Crypto pairs
            'BTC/USD': 'BTC/USD', 'ETH/USD': 'ETH/USD', 'ADA/USD': 'ADA/USD',
            'SOL/USD': 'SOL/USD', 'DOT/USD': 'DOT/USD', 'AVAX/USD': 'AVAX/USD',
            'MATIC/USD': 'MATIC/USD', 'LINK/USD': 'LINK/USD', 'UNI/USD': 'UNI/USD',
            'LTC/USD': 'LTC/USD', 'XRP/USD': 'XRP/USD', 'DOGE/USD': 'DOGE/USD',
            
            # Commodities
            'XAU/USD': 'XAU/USD',  # Gold
            'XAG/USD': 'XAG/USD',  # Silver
            'XPT/USD': 'XPT/USD',  # Platinum
            'XPD/USD': 'XPD/USD',  # Palladium
            'WTI': 'WTI',          # Crude Oil
            'BRENT': 'BRENT',      # Brent Oil
            'NATGAS': 'NATGAS',    # Natural Gas
            'COPPER': 'COPPER',    # Copper
            'WHEAT': 'WHEAT', 'CORN': 'CORN', 'COFFEE': 'COFFEE',
            'SUGAR': 'SUGAR', 'COTTON': 'COTTON', 'SOYBEANS': 'SOYBEANS',
            
            # Stocks
            'AAPL': 'AAPL', 'MSFT': 'MSFT', 'GOOGL': 'GOOGL', 'AMZN': 'AMZN',
            'TSLA': 'TSLA', 'META': 'META', 'NVDA': 'NVDA', 'NFLX': 'NFLX',
            'DIS': 'DIS', 'PYPL': 'PYPL', 'ADBE': 'ADBE', 'CRM': 'CRM'
        }

    def on_message(self, ws, message):
        """Handle incoming WebSocket messages with real-time price updates"""
        try:
            data = json.loads(message)
            
            if data.get('event') == 'price':
                symbol = data.get('symbol')
                price = float(data.get('price', 0))
                
                if symbol and price > 0:
                    # Find the original symbol (reverse mapping)
                    original_symbol = None
                    for orig, mapped in self.symbol_mapping.items():
                        if mapped == symbol:
                            original_symbol = orig
                            break
                    
                    if original_symbol:
                        # Update database with new price instantly
                        with self.app.app_context():
                            instrument = TradingInstrument.query.filter_by(symbol=original_symbol).first()
                            if instrument:
                                instrument.update_price(price)
                                db.session.commit()
                                logging.info(f"⚡ INSTANT UPDATE: {original_symbol} = ${price}")
                            else:
                                logging.warning(f"⚠️  Instrument {original_symbol} not found in database")
                    else:
                        logging.warning(f"⚠️  Symbol mapping not found for {symbol}")
            
            elif data.get('event') == 'subscribe-status':
                if data.get('status') == 'ok':
                    logging.info(f"✅ Subscribed to {data.get('symbol')}")
                else:
                    logging.error(f"❌ Subscription failed for {data.get('symbol')}: {data.get('message')}")
                    
        except json.JSONDecodeError:
            logging.error(f"❌ Invalid JSON received: {message}")
        except Exception as e:
            logging.error(f"❌ Error processing message: {str(e)}")

    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        logging.error(f"❌ WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        logging.warning("🔌 WebSocket connection closed")
        if self.running:
            logging.info("🔄 Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            self.connect()

    def on_open(self, ws):
        """Handle WebSocket connection open"""
        logging.info("🎉 WebSocket connected to Twelve Data!")
        
        # Get all instruments from database and subscribe to them
        with self.app.app_context():
            instruments = TradingInstrument.query.all()
            
            if not instruments:
                logging.warning("⚠️  No instruments found in database")
                return
            
            logging.info(f"📡 Subscribing to {len(instruments)} instruments...")
            
            # Subscribe to all instruments
            for instrument in instruments:
                mapped_symbol = self.symbol_mapping.get(instrument.symbol, instrument.symbol)
                
                subscribe_message = {
                    "action": "subscribe",
                    "params": {
                        "symbols": mapped_symbol
                    }
                }
                
                ws.send(json.dumps(subscribe_message))
                logging.info(f"📡 Subscribed to {instrument.symbol} ({mapped_symbol})")
                time.sleep(0.1)  # Small delay between subscriptions

    def connect(self):
        """Connect to Twelve Data WebSocket"""
        if not self.running:
            return
            
        websocket_url_with_key = f"{self.websocket_url}?apikey={self.api_key}"
        
        logging.info(f"🔌 Connecting to Twelve Data WebSocket...")
        
        self.ws = websocket.WebSocketApp(
            websocket_url_with_key,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # Run forever (blocking)
        self.ws.run_forever()

    def start_websocket(self):
        """Start the WebSocket connection in a separate thread"""
        self.running = True
        
        logging.info("🚀 Starting Twelve Data WebSocket Price Worker...")
        logging.info(f"🔑 API Key: {self.api_key[:8]}...")
        logging.info("⚡ INSTANT price updates via WebSocket!")
        
        # Start WebSocket in a separate thread
        websocket_thread = threading.Thread(target=self.connect, daemon=True)
        websocket_thread.start()
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("🛑 Stopping WebSocket worker...")
            self.running = False
            if self.ws:
                self.ws.close()

    def run_hybrid(self):
        """Run hybrid mode: WebSocket for real-time + API fallback every 30 seconds"""
        self.running = True
        
        logging.info("🚀 Starting HYBRID Twelve Data Price Worker...")
        logging.info("⚡ WebSocket for instant updates + API fallback every 30s")
        
        # Start WebSocket in background
        websocket_thread = threading.Thread(target=self.connect, daemon=True)
        websocket_thread.start()
        
        # Fallback API updates every 30 seconds for missed symbols
        def api_fallback():
            while self.running:
                try:
                    time.sleep(30)  # Wait 30 seconds
                    if self.running:
                        self.update_all_prices_api()
                except Exception as e:
                    logging.error(f"❌ API fallback error: {str(e)}")
        
        api_thread = threading.Thread(target=api_fallback, daemon=True)
        api_thread.start()
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("🛑 Stopping hybrid worker...")
            self.running = False
            if self.ws:
                self.ws.close()

    def update_all_prices_api(self):
        """Fallback API method (same as original but faster)"""
        with self.app.app_context():
            instruments = TradingInstrument.query.all()
            
            if not instruments:
                return
            
            logging.info(f"🔄 API fallback check for {len(instruments)} instruments...")
            
            updated_count = 0
            for instrument in instruments:
                try:
                    # Check if price is older than 1 minute
                    if instrument.last_updated:
                        seconds_old = (datetime.utcnow() - instrument.last_updated).total_seconds()
                        if seconds_old < 60:
                            continue  # Skip if recently updated
                    
                    # Get price via API
                    price = self.get_price_api(instrument.symbol)
                    if price:
                        instrument.update_price(price)
                        updated_count += 1
                        logging.info(f"🔄 API fallback: {instrument.symbol} = ${price}")
                
                except Exception as e:
                    logging.error(f"❌ API fallback error for {instrument.symbol}: {str(e)}")
            
            if updated_count > 0:
                db.session.commit()
                logging.info(f"✅ API fallback updated {updated_count} instruments")

    def get_price_api(self, symbol):
        """Get price via API (fallback method)"""
        try:
            mapped_symbol = self.symbol_mapping.get(symbol, symbol)
            
            url = 'https://api.twelvedata.com/price'
            params = {
                'symbol': mapped_symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'price' in data:
                    return float(data['price'])
                    
        except Exception as e:
            logging.error(f"❌ API fallback error for {symbol}: {str(e)}")
            
        return None

def main():
    """Main function"""
    worker = TwelveDataWebSocketWorker()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--websocket':
            # Pure WebSocket mode
            worker.start_websocket()
        elif sys.argv[1] == '--hybrid':
            # Hybrid mode (WebSocket + API fallback)
            worker.run_hybrid()
        elif sys.argv[1] == '--test':
            # Test API connection
            test_symbol = sys.argv[2] if len(sys.argv) > 2 else 'EUR/USD'
            price = worker.get_price_api(test_symbol)
            print(f"{test_symbol}: ${price}" if price else f"Failed to get price for {test_symbol}")
        else:
            print("Usage: python twelve_data_price_worker.py [--websocket|--hybrid|--test SYMBOL]")
    else:
        # Default: Run hybrid mode (recommended)
        worker.run_hybrid()

if __name__ == '__main__':
    main() 