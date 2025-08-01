#!/usr/bin/env python3
"""
Twelve Data Price Worker
Independent price update worker using Twelve Data API
Your API Key: 902d8585e8c040f591a3293d1b79ab88
Pro Plan: 610 API credits/minute, 500 WebSocket credits
"""

import os
import sys
import time
import logging
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import schedule

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from omcrm.webtrader.models import TradingInstrument

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twelve_data_price_worker.log'),
        logging.StreamHandler()
    ]
)

class TwelveDataPriceWorker:
    def __init__(self):
        self.api_key = '902d8585e8c040f591a3293d1b79ab88'
        self.base_url = 'https://api.twelvedata.com'
        self.credits_per_minute = 610  # Pro plan limit
        self.request_count = 0
        self.minute_start = time.time()
        
        # Symbol mapping for Twelve Data API
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

    def check_rate_limit(self):
        """Check if we're within the rate limit"""
        current_time = time.time()
        
        # Reset counter every minute
        if current_time - self.minute_start >= 60:
            self.request_count = 0
            self.minute_start = current_time
            
        if self.request_count >= self.credits_per_minute:
            sleep_time = 60 - (current_time - self.minute_start)
            if sleep_time > 0:
                logging.warning(f"Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
                self.request_count = 0
                self.minute_start = time.time()

    def get_price(self, symbol):
        """Get price for a single symbol from Twelve Data API"""
        try:
            self.check_rate_limit()
            
            # Map symbol to Twelve Data format
            twelve_data_symbol = self.symbol_mapping.get(symbol, symbol)
            
            url = f'{self.base_url}/price'
            params = {
                'symbol': twelve_data_symbol,
                'apikey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            self.request_count += 1
            
            if response.status_code == 200:
                data = response.json()
                if 'price' in data:
                    price = float(data['price'])
                    logging.info(f"✅ {symbol}: ${price}")
                    return price
                elif 'message' in data:
                    logging.warning(f"⚠️  {symbol}: {data['message']}")
                else:
                    logging.error(f"❌ {symbol}: Unexpected response format")
            else:
                logging.error(f"❌ {symbol}: HTTP {response.status_code}")
                
        except Exception as e:
            logging.error(f"❌ Error getting price for {symbol}: {str(e)}")
            
        return None

    def get_batch_prices(self, symbols):
        """Get prices for multiple symbols using batch API"""
        try:
            self.check_rate_limit()
            
            # Map symbols to Twelve Data format
            mapped_symbols = []
            for symbol in symbols:
                mapped_symbol = self.symbol_mapping.get(symbol, symbol)
                mapped_symbols.append(mapped_symbol)
            
            # Twelve Data batch API (uses more credits but faster)
            url = f'{self.base_url}/price'
            params = {
                'symbol': ','.join(mapped_symbols[:8]),  # Max 8 symbols per batch
                'apikey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=15)
            self.request_count += len(mapped_symbols[:8])  # Each symbol counts as 1 credit
            
            if response.status_code == 200:
                data = response.json()
                prices = {}
                
                if isinstance(data, dict):
                    # Single symbol response
                    if 'price' in data:
                        prices[symbols[0]] = float(data['price'])
                elif isinstance(data, list):
                    # Multiple symbols response
                    for i, item in enumerate(data):
                        if i < len(symbols) and 'price' in item:
                            prices[symbols[i]] = float(item['price'])
                
                return prices
                
        except Exception as e:
            logging.error(f"❌ Error getting batch prices: {str(e)}")
            
        return {}

    def update_instrument_price(self, instrument):
        """Update price for a single instrument"""
        try:
            price = self.get_price(instrument.symbol)
            if price:
                instrument.update_price(price)
                return True
        except Exception as e:
            logging.error(f"❌ Error updating {instrument.symbol}: {str(e)}")
        return False

    def update_all_prices(self):
        """Update prices for all instruments"""
        app = create_app()
        
        with app.app_context():
            instruments = TradingInstrument.query.all()
            
            if not instruments:
                logging.info("No instruments found in database")
                return
            
            logging.info(f"🚀 Starting price update for {len(instruments)} instruments...")
            
            updated_count = 0
            start_time = time.time()
            
            # Use ThreadPoolExecutor for concurrent updates
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                
                for instrument in instruments:
                    future = executor.submit(self.update_instrument_price, instrument)
                    futures.append((future, instrument))
                    
                    # Small delay to avoid overwhelming the API
                    time.sleep(0.1)
                
                # Collect results
                for future, instrument in futures:
                    try:
                        if future.result():
                            updated_count += 1
                    except Exception as e:
                        logging.error(f"❌ Future error for {instrument.symbol}: {str(e)}")
            
            # Commit all changes
            try:
                db.session.commit()
                duration = time.time() - start_time
                logging.info(f"✅ Updated {updated_count}/{len(instruments)} instruments in {duration:.1f}s")
                logging.info(f"📊 API requests used: {self.request_count}/610 this minute")
            except Exception as e:
                db.session.rollback()
                logging.error(f"❌ Database commit error: {str(e)}")

    def run_continuous(self):
        """Run the price worker continuously"""
        logging.info("🚀 Starting Twelve Data Price Worker...")
        logging.info(f"🔑 API Key: {self.api_key[:8]}...")
        logging.info(f"📊 Credits per minute: {self.credits_per_minute}")
        
        # Schedule price updates every 2 minutes (conservative to stay within limits)
        schedule.every(2).minutes.do(self.update_all_prices)
        
        # Initial price update
        self.update_all_prices()
        
        logging.info("⏰ Scheduled updates every 2 minutes")
        logging.info("🔄 Running continuous price worker... (Ctrl+C to stop)")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(10)  # Check every 10 seconds
        except KeyboardInterrupt:
            logging.info("🛑 Price worker stopped by user")
        except Exception as e:
            logging.error(f"❌ Price worker error: {str(e)}")

def main():
    """Main function"""
    worker = TwelveDataPriceWorker()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            # Run once and exit
            worker.update_all_prices()
        elif sys.argv[1] == '--test':
            # Test a single symbol
            test_symbol = sys.argv[2] if len(sys.argv) > 2 else 'EUR/USD'
            price = worker.get_price(test_symbol)
            print(f"{test_symbol}: ${price}" if price else f"Failed to get price for {test_symbol}")
        else:
            print("Usage: python twelve_data_price_worker.py [--once|--test SYMBOL]")
    else:
        # Run continuously
        worker.run_continuous()

if __name__ == '__main__':
    main() 