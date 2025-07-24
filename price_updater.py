#!/usr/bin/env python3
"""
Dedicated Price Updater - Background Worker
Runs independently from the main app to update instrument prices
"""

import os
import sys
import time
import logging
from datetime import datetime
import random

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - PRICE_WORKER - %(levelname)s - %(message)s'
)

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

def get_crypto_price_simple(symbol):
    """Simple crypto price fetcher for background worker"""
    import requests
    
    # Try CoinGecko first (most reliable)
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
            logging.info(f"💰 Updated {symbol}: ${price:,.2f}")
            return round(price, 6)
            
    except Exception as e:
        logging.warning(f"Failed to get price for {symbol}: {e}")
    
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
        logging.info(f"📊 Updated {symbol}: ${simulated_price:.2f}")
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