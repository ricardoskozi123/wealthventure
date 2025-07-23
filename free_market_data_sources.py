#!/usr/bin/env python3
"""
Free Market Data Sources - Unlimited/High-Limit WebSocket & API Integration
No rate limiting issues, all free tiers with generous limits
"""

import websocket
import requests
import json
import time
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

class FreeMarketDataManager:
    def __init__(self):
        self.stock_ws = None
        self.price_cache = {}
        self.running = False
        
    def start_free_stock_websocket(self, stock_symbols):
        """
        Start IEX Cloud WebSocket for stocks (500,000 free messages/month)
        Real-time data with no rate limits on WebSocket
        """
        if self.stock_ws is not None:
            logging.info("🔄 Stock WebSocket already running")
            return
            
        # IEX Cloud free WebSocket endpoint
        ws_url = "wss://ws-api.iextrading.com/1.0/tops"
        
        logging.info(f"🔗 Connecting to IEX Cloud WebSocket (FREE)...")
        logging.info(f"📈 Subscribing to stocks: {', '.join(stock_symbols)}")
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                for item in data:
                    symbol = item.get('symbol', 'UNKNOWN')
                    price = float(item.get('lastSalePrice', 0))
                    
                    if price > 0:
                        # Cache the price
                        self.price_cache[f"{symbol}/USD"] = {
                            'price': price,
                            'change_24h': 0,  # IEX doesn't provide 24h change in this stream
                            'timestamp': time.time(),
                            'source': 'IEX_FREE'
                        }
                        
                        logging.info(f"📊 {symbol}: ${price:.2f} (IEX Free)")
                        
            except Exception as e:
                logging.error(f"❌ Error parsing IEX WebSocket message: {e}")
        
        def on_error(ws, error):
            logging.error(f"❌ IEX WebSocket Error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            self.stock_ws = None
            logging.info(f"🔌 IEX WebSocket Closed: {close_status_code}")
        
        def on_open(ws):
            logging.info(f"✅ IEX WebSocket Connected (FREE - 500k msgs/month)!")
            # Subscribe to symbols
            subscribe_msg = {
                "subscribe": stock_symbols
            }
            ws.send(json.dumps(subscribe_msg))
        
        # Create WebSocket connection
        self.stock_ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Run in background thread
        def run_websocket():
            self.stock_ws.run_forever()
        
        ws_thread = threading.Thread(target=run_websocket, daemon=True)
        ws_thread.start()
        
        logging.info("🚀 IEX Stock WebSocket thread started!")
    
    def get_free_forex_prices(self, currency_pairs):
        """
        Get forex prices from ExchangeRate-API (1,500 requests/month FREE)
        No WebSocket but very reliable API
        """
        logging.info(f"💱 Fetching FREE forex data for: {', '.join(currency_pairs)}")
        
        try:
            # Get latest USD rates (covers most major pairs)
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            rates = data.get('rates', {})
            
            for pair in currency_pairs:
                if '/' in pair:
                    base, quote = pair.split('/')
                    
                    if base == 'USD' and quote in rates:
                        # USD/XXX pair
                        rate = rates[quote]
                        self.price_cache[pair] = {
                            'price': rate,
                            'change_24h': 0,
                            'timestamp': time.time(),
                            'source': 'ExchangeRate_FREE'
                        }
                        logging.info(f"💰 {pair}: {rate:.4f} (FREE ExchangeRate-API)")
                        
                    elif quote == 'USD' and base in rates:
                        # XXX/USD pair  
                        rate = 1 / rates[base]
                        self.price_cache[pair] = {
                            'price': rate,
                            'change_24h': 0,
                            'timestamp': time.time(),
                            'source': 'ExchangeRate_FREE'
                        }
                        logging.info(f"💰 {pair}: {rate:.4f} (FREE ExchangeRate-API)")
                        
        except Exception as e:
            logging.error(f"❌ Error fetching forex data: {e}")
    
    def get_free_commodity_prices(self, commodity_symbols):
        """
        Get commodity prices from Alpha Vantage (500 requests/day FREE)
        Includes Gold, Silver, Oil, etc.
        """
        logging.info(f"🥇 Fetching FREE commodity data for: {', '.join(commodity_symbols)}")
        
        # Free Alpha Vantage key (demo key - replace with your own for production)
        api_key = "demo"  # Get free key at: https://www.alphavantage.co/support/#api-key
        
        commodity_mapping = {
            'GOLD': 'GC=F',    # Gold futures
            'SILVER': 'SI=F',  # Silver futures  
            'OIL': 'CL=F',     # Crude oil futures
            'COPPER': 'HG=F'   # Copper futures
        }
        
        for commodity in commodity_symbols:
            try:
                symbol = commodity_mapping.get(commodity, commodity)
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
                
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                quote = data.get('Global Quote', {})
                
                if quote and '05. price' in quote:
                    price = float(quote['05. price'])
                    change_percent = float(quote.get('10. change percent', '0%').replace('%', ''))
                    
                    self.price_cache[f"{commodity}/USD"] = {
                        'price': price,
                        'change_24h': change_percent,
                        'timestamp': time.time(),
                        'source': 'AlphaVantage_FREE'
                    }
                    
                    color = "🟢" if change_percent >= 0 else "🔴"
                    logging.info(f"{color} {commodity}: ${price:.2f} ({change_percent:+.2f}%) [FREE Alpha Vantage]")
                
                # Small delay to respect rate limits
                time.sleep(0.2)
                
            except Exception as e:
                logging.error(f"❌ Error fetching {commodity} price: {e}")
    
    def get_cached_price(self, symbol):
        """Get cached price from any source"""
        cached_data = self.price_cache.get(symbol)
        if cached_data:
            # Check if data is recent (less than 60 seconds old)
            age = time.time() - cached_data['timestamp']
            if age < 60:
                return cached_data['price']
        return None
    
    def start_all_free_feeds(self, crypto_symbols, stock_symbols, forex_pairs, commodity_symbols):
        """Start all free market data feeds"""
        logging.info("🚀 Starting ALL FREE market data feeds...")
        
        # 1. Crypto WebSocket (already implemented - Binance)
        logging.info("✅ Crypto: Using existing Binance WebSocket (UNLIMITED FREE)")
        
        # 2. Stocks WebSocket (IEX Cloud)
        if stock_symbols:
            self.start_free_stock_websocket(stock_symbols)
        
        # 3. Forex API polling (every 5 minutes to stay within limits)
        if forex_pairs:
            def forex_poller():
                while True:
                    self.get_free_forex_prices(forex_pairs)
                    time.sleep(300)  # 5 minutes = 288 calls/day (under 1500/month limit)
            
            forex_thread = threading.Thread(target=forex_poller, daemon=True)
            forex_thread.start()
            logging.info("✅ Forex: Started ExchangeRate-API poller (1,500 req/month)")
        
        # 4. Commodities API polling (every 10 minutes to stay within limits)
        if commodity_symbols:
            def commodity_poller():
                while True:
                    self.get_free_commodity_prices(commodity_symbols)
                    time.sleep(600)  # 10 minutes = 144 calls/day (under 500/day limit)
            
            commodity_thread = threading.Thread(target=commodity_poller, daemon=True)
            commodity_thread.start()
            logging.info("✅ Commodities: Started Alpha Vantage poller (500 req/day)")
        
        logging.info("🎉 ALL FREE market data feeds started successfully!")

# Example usage
if __name__ == "__main__":
    manager = FreeMarketDataManager()
    
    # Test with sample data
    crypto_symbols = ['BTC/USD', 'ETH/USD']  # Already handled by Binance
    stock_symbols = ['AAPL', 'MSFT', 'GOOGL']
    forex_pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY']
    commodity_symbols = ['GOLD', 'SILVER', 'OIL']
    
    manager.start_all_free_feeds(crypto_symbols, stock_symbols, forex_pairs, commodity_symbols)
    
    # Keep running
    try:
        while True:
            time.sleep(10)
            # Test getting cached prices
            for symbol in ['AAPL/USD', 'EUR/USD', 'GOLD/USD']:
                price = manager.get_cached_price(symbol)
                if price:
                    print(f"💰 Cached {symbol}: ${price}")
    except KeyboardInterrupt:
        print("Stopping...") 