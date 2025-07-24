#!/usr/bin/env python3
"""
Dedicated Price Updater - Background Worker
Runs independently from the main app to update instrument prices
Uses the same Binance WebSocket logic as before for real-time crypto prices!
"""

import os
import sys
import time
import logging
from datetime import datetime
import random
import json
import threading

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - PRICE_WORKER - %(levelname)s - %(message)s'
)

# Global WebSocket variables for crypto prices
crypto_ws = None
crypto_price_cache = {}

def create_app_context():
    """Create a minimal Flask app context for database access"""
    from omcrm import create_app, db
    from omcrm.webtrader.models import TradingInstrument
    from omcrm.leads.models import Lead, LeadSource, LeadStatus, Comment
    from omcrm.deals.models import Deal, DealStage
    from omcrm.users.models import User, Team, Role, Resource
    from omcrm.settings.models import AppConfig, Currency, TimeZone
    from omcrm.activities.models import Activity
    
    app = create_app()
    return app, db

def start_crypto_websocket(crypto_instruments):
    """Start Binance WebSocket for real-time crypto prices - same logic as before"""
    global crypto_ws, crypto_price_cache
    
    if crypto_ws is not None:
        logging.info("🔄 WebSocket already running, skipping...")
        return
    
    # Extract symbols and convert to Binance format (same as before)
    binance_symbols = []
    for instrument in crypto_instruments:
        symbol = instrument['symbol']
        if '/' in symbol:
            # Convert BTC/USD -> btcusdt
            base_symbol = symbol.split('/')[0].lower()
            binance_symbol = f"{base_symbol}usdt"
            binance_symbols.append(binance_symbol)
            logging.info(f"📈 Mapping {symbol} → {binance_symbol}")
    
    if not binance_symbols:
        logging.warning("⚠️  No valid crypto symbols found for WebSocket")
        return
    
    # NON-BLOCKING: Don't block the main worker thread (same pattern as before)
    def start_websocket_async():
        try:
            # Create WebSocket URL for multiple symbols (exact same pattern)
            streams = [f"{symbol}@ticker" for symbol in binance_symbols]
            ws_url = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
            
            logging.info(f"🔗 Connecting to Binance WebSocket...")
            logging.info(f"📊 Subscribing to: {', '.join(binance_symbols)}")
            logging.info(f"🌐 URL: {ws_url}")
            
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
                    
                    # Convert BTCUSDT -> BTC/USD for database lookup (same logic)
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
                        logging.info(f"{color} {db_symbol}: ${price:,.6f} ({change_24h:+.2f}%)")
                        
                except Exception as e:
                    logging.error(f"❌ Error parsing WebSocket message: {e}")
            
            def on_error(ws, error):
                logging.error(f"❌ WebSocket Error: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                global crypto_ws
                crypto_ws = None
                logging.info(f"🔌 WebSocket Closed: {close_status_code} - {close_msg}")
            
            def on_open(ws):
                logging.info(f"✅ WebSocket Connected Successfully!")
                logging.info(f"💰 Receiving unlimited free real-time crypto prices...")
            
            # Create WebSocket connection (exact same pattern)
            import websocket
            global crypto_ws
            crypto_ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Run WebSocket (this will block in the background thread)
            crypto_ws.run_forever()
            
        except Exception as e:
            logging.error(f"❌ WebSocket startup error: {e}")
    
    # Start in background thread to avoid blocking worker (same as before)
    ws_thread = threading.Thread(target=start_websocket_async, daemon=True)
    ws_thread.start()
    
    logging.info("🚀 WebSocket thread started (non-blocking)!")

def get_cached_crypto_price(symbol):
    """Get cached price from WebSocket data"""
    global crypto_price_cache
    
    cached_data = crypto_price_cache.get(symbol)
    if cached_data:
        # Check if data is recent (less than 30 seconds old)
        age = time.time() - cached_data['timestamp']
        if age < 30:
            return cached_data['price']
    
    return None

def get_crypto_price_simple(symbol):
    """Get crypto price - prioritize WebSocket, fallback to API"""
    import requests
    
    # First try WebSocket cache (real-time prices)
    ws_price = get_cached_crypto_price(symbol)
    if ws_price:
        logging.info(f"💰 WebSocket price for {symbol}: ${ws_price:,.2f}")
        return round(ws_price, 6)
    
    # Fallback to CoinGecko API if WebSocket not available
    crypto_mappings = {
        'BTC/USD': 'bitcoin',
        'ETH/USD': 'ethereum', 
        'SOL/USD': 'solana',
        'BNB/USD': 'binancecoin',
        'ADA/USD': 'cardano',
        'DOT/USD': 'polkadot',
        'AVAX/USD': 'avalanche-2',
        'MATIC/USD': 'matic-network',
        'DOGE/USD': 'dogecoin',
        'XRP/USD': 'ripple'
    }
    
    crypto_id = crypto_mappings.get(symbol)
    if not crypto_id:
        return None
        
    try:
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if crypto_id in data and 'usd' in data[crypto_id]:
            price = float(data[crypto_id]['usd'])
            logging.info(f"💰 API fallback price for {symbol}: ${price:,.2f}")
            return round(price, 6)
            
    except Exception as e:
        logging.warning(f"Failed to get API price for {symbol}: {e}")
    
    return None

def get_stock_price_simple(symbol):
    """Simple stock price with realistic simulation"""
    base_prices = {
        'AAPL': 214.09, 'MSFT': 428.52, 'GOOGL': 174.57, 'AMZN': 186.85,
        'TSLA': 248.30, 'META': 513.26, 'NVDA': 128.74, 'JPM': 198.43,
        'V': 278.56, 'WMT': 68.92, 'NFLX': 645.23, 'CRM': 234.12,
        'AMD': 145.67, 'INTC': 89.45, 'BABA': 234.56, 'TSM': 167.89
    }
    
    if symbol in base_prices:
        base_price = base_prices[symbol]
        # Add small realistic variation (±1% max)
        variation = random.uniform(-0.01, 0.01)
        simulated_price = base_price * (1 + variation)
        logging.info(f"📊 Simulated price for {symbol}: ${simulated_price:.2f}")
        return round(simulated_price, 2)
    
    return 100.0  # Default fallback

def update_all_prices():
    """Update prices for all instruments"""
    app, db = create_app_context()
    
    with app.app_context():
        from omcrm.webtrader.models import TradingInstrument
        
        try:
            instruments = TradingInstrument.query.all()
            updated_count = 0
            
            for instrument in instruments:
                try:
                    new_price = None
                    
                    if instrument.type == 'crypto':
                        new_price = get_crypto_price_simple(instrument.symbol)
                    elif instrument.type == 'stock':
                        new_price = get_stock_price_simple(instrument.symbol)
                    
                    if new_price and new_price != instrument.current_price:
                        # Calculate percentage change
                        if instrument.current_price and instrument.current_price > 0:
                            change = ((new_price - instrument.current_price) / instrument.current_price) * 100
                            instrument.change = round(change, 2)
                        else:
                            instrument.change = 0.0
                        
                        instrument.current_price = new_price
                        instrument.last_updated = datetime.utcnow()
                        updated_count += 1
                        
                except Exception as e:
                    logging.error(f"Error updating {instrument.symbol}: {e}")
                    continue
            
            if updated_count > 0:
                db.session.commit()
                logging.info(f"✅ Updated {updated_count}/{len(instruments)} instruments")
            else:
                logging.info(f"📊 No updates needed for {len(instruments)} instruments")
                
        except Exception as e:
            logging.error(f"Error in update cycle: {e}")
            db.session.rollback()

def main():
    """Main price updater loop"""
    logging.info("🚀 Starting dedicated price updater worker...")
    logging.info("📊 Will update prices every 10 seconds")
    
    # Initialize WebSocket for crypto instruments (same as before)
    try:
        logging.info("💰 Initializing Binance WebSocket for crypto...")
        app, db = create_app_context()
        
        with app.app_context():
            from omcrm.webtrader.models import TradingInstrument
            
            # Get all crypto instruments from database
            crypto_instruments = TradingInstrument.query.filter_by(type='crypto').all()
            
            if crypto_instruments:
                # Convert to the format expected by the WebSocket function
                crypto_instrument_data = []
                for instrument in crypto_instruments:
                    crypto_instrument_data.append({
                        'symbol': instrument.symbol,
                        'name': instrument.name,
                        'type': instrument.type
                    })
                
                # Start WebSocket connection using the EXACT working pattern
                start_crypto_websocket(crypto_instrument_data)
                logging.info(f"🎉 Started Binance WebSocket for {len(crypto_instrument_data)} crypto instruments!")
                logging.info(f"🔗 Symbols: {[i['symbol'] for i in crypto_instrument_data]}")
            else:
                logging.warning("⚠️  No crypto instruments found in database")
                
    except Exception as e:
        logging.error(f"Error starting crypto WebSocket: {e}")
    
    # Give WebSocket time to connect
    time.sleep(3)
    
    while True:
        try:
            start_time = time.time()
            update_all_prices()
            
            # Sleep for remaining time to maintain 10-second intervals
            elapsed = time.time() - start_time
            sleep_time = max(0, 10 - elapsed)
            
            if sleep_time > 0:
                logging.info(f"💤 Sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
            else:
                logging.warning(f"⚠️  Update took {elapsed:.1f}s (longer than 10s interval)")
                
        except KeyboardInterrupt:
            logging.info("🛑 Price updater stopped by user")
            break
        except Exception as e:
            logging.error(f"❌ Unexpected error: {e}")
            time.sleep(5)  # Brief pause before retrying

if __name__ == "__main__":
    main() 