"""
Real-time data service using WebSocket connections for live financial data
Supports multiple free APIs with automatic failover
"""

import asyncio
import json
import logging
import threading
import time
import websocket
from typing import Dict, List, Callable, Optional
import requests
from datetime import datetime
import queue
from flask import current_app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTimeDataManager:
    """
    Manages real-time data connections for multiple financial instruments
    """
    
    def __init__(self):
        self.connections = {}
        self.price_callbacks = []
        self.is_running = False
        self.update_thread = None
        self.price_cache = {}
        self.last_update = {}
        
        # Enhanced crypto symbol mapping for database symbols to Binance symbols
        self.crypto_symbol_mapping = {
            # Database symbol -> Binance symbol
            'BTC/USD': 'BTCUSDT',
            'ETH/USD': 'ETHUSDT', 
            'SOL/USD': 'SOLUSDT',
            'BNB/USD': 'BNBUSDT',
            'ADA/USD': 'ADAUSDT',
            'DOT/USD': 'DOTUSDT',
            'AVAX/USD': 'AVAXUSDT',
            'MATIC/USD': 'MATICUSDT',
            'DOGE/USD': 'DOGEUSDT',
            'XRP/USD': 'XRPUSDT',
            'TON/USD': 'TONUSDT',
            # Also support direct symbols
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'SOL': 'SOLUSDT',
            'BNB': 'BNBUSDT',
            'ADA': 'ADAUSDT',
            'DOT': 'DOTUSDT',
            'AVAX': 'AVAXUSDT',
            'MATIC': 'MATICUSDT',
            'DOGE': 'DOGEUSDT',
            'XRP': 'XRPUSDT',
            'TON': 'TONUSDT'
        }
        
        # Reverse mapping for Binance symbol -> Database symbol
        self.binance_to_db_mapping = {}
        for db_symbol, binance_symbol in self.crypto_symbol_mapping.items():
            base_symbol = binance_symbol.replace('USDT', '')
            self.binance_to_db_mapping[base_symbol] = db_symbol
        
        # Free API configurations
        self.apis = {
            'binance': {
                'url': 'wss://stream.binance.com:9443/ws/',
                'type': 'crypto',
                'active': False,
                'connection': None
            },
            'finnhub': {
                'url': 'wss://ws.finnhub.io',
                'token': 'demo',  # Free demo token
                'type': 'stocks',
                'active': False,
                'connection': None
            },
            'polygon': {
                'url': 'wss://socket.polygon.io',
                'token': 'demo',  # Free demo token
                'type': 'multi',
                'active': False,
                'connection': None
            }
        }
        
        # Instrument mapping
        self.instrument_mapping = {
            'crypto': {
                'BTC': 'btcusdt',
                'ETH': 'ethusdt',
                'SOL': 'solusdt',
                'BNB': 'bnbusdt',
                'ADA': 'adausdt',
                'DOT': 'dotusdt',
                'AVAX': 'avaxusdt',
                'MATIC': 'maticusdt'
            },
            'stocks': {
                'AAPL': 'AAPL',
                'MSFT': 'MSFT',
                'GOOGL': 'GOOGL',
                'AMZN': 'AMZN',
                'TSLA': 'TSLA',
                'META': 'META',
                'NVDA': 'NVDA',
                'JPM': 'JPM'
            }
        }

    def add_price_callback(self, callback: Callable):
        """Add a callback function to be called when prices update"""
        self.price_callbacks.append(callback)

    def remove_price_callback(self, callback: Callable):
        """Remove a price callback"""
        if callback in self.price_callbacks:
            self.price_callbacks.remove(callback)

    def notify_price_update(self, symbol: str, price: float, change_24h: float = 0):
        """Notify all callbacks of a price update"""
        update_data = {
            'symbol': symbol,
            'price': price,
            'change_24h': change_24h,
            'timestamp': datetime.now().isoformat()
        }
        
        # Update cache
        self.price_cache[symbol] = update_data
        self.last_update[symbol] = time.time()
        
        # Notify callbacks
        for callback in self.price_callbacks:
            try:
                callback(update_data)
            except Exception as e:
                logger.error(f"Error in price callback: {e}")

    def get_cached_price(self, symbol: str) -> Optional[Dict]:
        """Get the last cached price for a symbol"""
        return self.price_cache.get(symbol)

    def start_binance_crypto_stream(self, symbols: List[str]):
        """Start Binance WebSocket for cryptocurrency prices"""
        try:
            # Convert symbols to Binance format
            binance_symbols = []
            for symbol in symbols:
                if symbol.upper() in self.instrument_mapping['crypto']:
                    binance_symbols.append(self.instrument_mapping['crypto'][symbol.upper()])
            
            if not binance_symbols:
                return
                
            # Create stream URL
            streams = [f"{symbol}@ticker" for symbol in binance_symbols]
            stream_url = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if 'data' in data:
                        ticker_data = data['data']
                    else:
                        ticker_data = data
                        
                    binance_symbol = ticker_data.get('s', '').replace('USDT', '')  # e.g., BTC
                    price = float(ticker_data.get('c', 0))
                    change_24h = float(ticker_data.get('P', 0))
                    
                    if binance_symbol and price > 0:
                        # Map back to database symbol if needed
                        db_symbol = self.binance_to_db_mapping.get(binance_symbol, binance_symbol)
                        self.notify_price_update(db_symbol, price, change_24h)
                        logger.info(f"💰 Binance WebSocket: {db_symbol} = ${price:,.2f} ({change_24h:+.2f}%)")
                        
                except json.JSONDecodeError:
                    logger.error("Failed to parse Binance WebSocket message")
                except Exception as e:
                    logger.error(f"Error processing Binance message: {e}")

            def on_error(ws, error):
                logger.error(f"Binance WebSocket error: {error}")
                self.apis['binance']['active'] = False

            def on_close(ws, close_status_code, close_msg):
                logger.info("Binance WebSocket connection closed")
                self.apis['binance']['active'] = False

            def on_open(ws):
                logger.info("Binance WebSocket connection opened")
                self.apis['binance']['active'] = True

            # Create WebSocket connection
            ws = websocket.WebSocketApp(stream_url,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close,
                                      on_open=on_open)
            
            self.apis['binance']['connection'] = ws
            
            # Start connection in separate thread
            def run_websocket():
                ws.run_forever()
                
            threading.Thread(target=run_websocket, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Failed to start Binance WebSocket: {e}")

    def start_finnhub_stock_stream(self, symbols: List[str]):
        """Start Finnhub WebSocket for stock prices"""
        try:
            ws_url = f"wss://ws.finnhub.io?token=demo"
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if data.get('type') == 'trade':
                        for trade in data.get('data', []):
                            symbol = trade.get('s')
                            price = trade.get('p')
                            if symbol and price:
                                self.notify_price_update(symbol, price)
                                logger.debug(f"Finnhub price update: {symbol} = ${price}")
                                
                except Exception as e:
                    logger.error(f"Error processing Finnhub message: {e}")

            def on_error(ws, error):
                logger.error(f"Finnhub WebSocket error: {error}")
                self.apis['finnhub']['active'] = False

            def on_close(ws, close_status_code, close_msg):
                logger.info("Finnhub WebSocket connection closed")
                self.apis['finnhub']['active'] = False

            def on_open(ws):
                logger.info("Finnhub WebSocket connection opened")
                self.apis['finnhub']['active'] = True
                
                # Subscribe to symbols
                for symbol in symbols:
                    if symbol.upper() in self.instrument_mapping['stocks']:
                        subscribe_msg = json.dumps({"type": "subscribe", "symbol": symbol.upper()})
                        ws.send(subscribe_msg)
                        logger.info(f"Subscribed to Finnhub updates for {symbol}")

            ws = websocket.WebSocketApp(ws_url,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close,
                                      on_open=on_open)
            
            self.apis['finnhub']['connection'] = ws
            
            def run_websocket():
                ws.run_forever()
                
            threading.Thread(target=run_websocket, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Failed to start Finnhub WebSocket: {e}")

    def start_fallback_polling(self, symbols: List[str]):
        """Start fallback polling for symbols not covered by WebSockets"""
        def polling_worker():
            while self.is_running:
                try:
                    for symbol in symbols:
                        # Check if we have recent data (within 30 seconds)
                        last_update_time = self.last_update.get(symbol, 0)
                        if time.time() - last_update_time > 30:
                            # Fetch price using existing API methods
                            price = self._fetch_price_fallback(symbol)
                            if price:
                                self.notify_price_update(symbol, price)
                                
                    time.sleep(10)  # Poll every 10 seconds
                    
                except Exception as e:
                    logger.error(f"Error in fallback polling: {e}")
                    time.sleep(5)

        if self.update_thread is None or not self.update_thread.is_alive():
            self.update_thread = threading.Thread(target=polling_worker, daemon=True)
            self.update_thread.start()

    def _fetch_price_fallback(self, symbol: str) -> Optional[float]:
        """Fetch price using HTTP API as fallback"""
        try:
            # Try different APIs based on symbol type
            if symbol.upper() in ['BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'DOT', 'AVAX', 'MATIC']:
                # Crypto - try CoinGecko
                crypto_ids = {
                    'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
                    'BNB': 'binancecoin', 'ADA': 'cardano', 'DOT': 'polkadot',
                    'AVAX': 'avalanche-2', 'MATIC': 'matic-network'
                }
                crypto_id = crypto_ids.get(symbol.upper())
                if crypto_id:
                    url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd'
                    response = requests.get(url, timeout=5)
                    data = response.json()
                    return data.get(crypto_id, {}).get('usd')
                    
            else:
                # Stock - try Alpha Vantage
                api_key = 'J54VFE3RK2YHL5MN'  # Demo key
                url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}'
                response = requests.get(url, timeout=5)
                data = response.json()
                quote = data.get('Global Quote', {})
                price_str = quote.get('05. price')
                if price_str:
                    return float(price_str)
                    
        except Exception as e:
            logger.error(f"Fallback price fetch failed for {symbol}: {e}")
            
        return None

    def start_real_time_feeds(self, instruments: List[Dict]):
        """Start real-time data feeds for given instruments"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Separate instruments by type
        crypto_symbols = []
        stock_symbols = []
        
        for instrument in instruments:
            symbol = instrument.get('symbol', '').upper()
            instrument_type = instrument.get('type', 'stock').lower()
            
            if instrument_type == 'crypto' or symbol in self.instrument_mapping['crypto']:
                crypto_symbols.append(symbol)
            else:
                stock_symbols.append(symbol)
        
        # Start WebSocket connections
        if crypto_symbols:
            logger.info(f"Starting Binance WebSocket for crypto: {crypto_symbols}")
            self.start_binance_crypto_stream(crypto_symbols)
            
        if stock_symbols:
            logger.info(f"Starting Finnhub WebSocket for stocks: {stock_symbols}")
            self.start_finnhub_stock_stream(stock_symbols)
        
        # Start fallback polling for all symbols
        all_symbols = crypto_symbols + stock_symbols
        if all_symbols:
            logger.info(f"Starting fallback polling for: {all_symbols}")
            self.start_fallback_polling(all_symbols)

    def stop_real_time_feeds(self):
        """Stop all real-time data feeds"""
        self.is_running = False
        
        # Close WebSocket connections
        for api_name, api_config in self.apis.items():
            if api_config.get('connection'):
                try:
                    api_config['connection'].close()
                    api_config['active'] = False
                    api_config['connection'] = None
                    logger.info(f"Closed {api_name} WebSocket connection")
                except Exception as e:
                    logger.error(f"Error closing {api_name} connection: {e}")
        
        # Wait for threads to finish
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=5)
        
        logger.info("All real-time data feeds stopped")

    def get_connection_status(self) -> Dict:
        """Get status of all connections"""
        status = {}
        for api_name, api_config in self.apis.items():
            status[api_name] = {
                'active': api_config.get('active', False),
                'type': api_config.get('type'),
                'url': api_config.get('url')
            }
        return status

    def get_all_crypto_instruments_from_db(self):
        """Get all crypto instruments from the database"""
        try:
            from omcrm.webtrader.models import TradingInstrument
            crypto_instruments = TradingInstrument.query.filter_by(type='crypto').all()
            
            result = []
            for instrument in crypto_instruments:
                result.append({
                    'id': instrument.id,
                    'symbol': instrument.symbol,
                    'name': instrument.name,
                    'type': instrument.type
                })
            
            logger.info(f"Found {len(result)} crypto instruments in database: {[i['symbol'] for i in result]}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting crypto instruments from database: {e}")
            return []

    def auto_subscribe_all_crypto(self):
        """Automatically subscribe to ALL crypto instruments in the database"""
        try:
            crypto_instruments = self.get_all_crypto_instruments_from_db()
            
            if not crypto_instruments:
                logger.warning("No crypto instruments found in database")
                return False
            
            # Extract symbols and map them to Binance format
            crypto_symbols = []
            for instrument in crypto_instruments:
                db_symbol = instrument['symbol']
                if db_symbol in self.crypto_symbol_mapping:
                    binance_symbol = self.crypto_symbol_mapping[db_symbol]
                    crypto_symbols.append(binance_symbol.replace('USDT', ''))  # Remove USDT for internal use
                    logger.info(f"📈 Auto-subscribing: {db_symbol} → {binance_symbol}")
                else:
                    logger.warning(f"⚠️  No Binance mapping for {db_symbol}")
            
            if crypto_symbols:
                logger.info(f"🚀 Starting Binance WebSocket for {len(crypto_symbols)} crypto instruments")
                self.start_binance_crypto_stream(crypto_symbols)
                return True
            else:
                logger.warning("No valid crypto symbols to subscribe to")
                return False
                
        except Exception as e:
            logger.error(f"Error in auto_subscribe_all_crypto: {e}")
            return False

# Global instance
real_time_manager = RealTimeDataManager() 