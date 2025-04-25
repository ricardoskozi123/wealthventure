from datetime import datetime
import requests
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from omcrm import db
from omcrm.leads.models import Lead, Trade
from omcrm.webtrader.forms import TradeForm, InstrumentForm
from omcrm.webtrader.models import TradingInstrument
import logging
import random
import time  # Add time import for delays

logging.basicConfig(level=logging.DEBUG)

webtrader = Blueprint('webtrader', __name__)

def get_crypto_price(name):
    """Get real-time cryptocurrency price from multiple sources with fallbacks. Prioritizes APIs."""
    crypto_id = None
    crypto_mappings = {
        'bitcoin': ['btc', 'bitcoin', 'BTCUSDT', 'BTC-USD'],
        'ethereum': ['eth', 'ethereum', 'ETHUSDT', 'ETH-USD'],
        'solana': ['sol', 'solana', 'SOLUSDT', 'SOL-USD'],
        # Add other mappings as needed
    }
    for base_id, aliases in crypto_mappings.items():
        if name.lower() in aliases or name.lower() == base_id:
            crypto_id = base_id
            break
            
    api_providers = [
        {'name': 'CoinGecko', 'func': fetch_coingecko, 'args': (name.lower(), crypto_id)},
        {'name': 'Binance', 'func': fetch_binance, 'args': (name.upper(),)},
        {'name': 'YahooFinance', 'func': fetch_yfinance_crypto, 'args': (name.upper(),)}
    ]

    # Try APIs first
    for provider in api_providers:
        try:
            logging.debug(f"Trying API: {provider['name']} for {name}")
            price = provider['func'](*provider['args'])
            if price is not None:
                logging.info(f"Got price {price} for {name} from {provider['name']}")
                return round(float(price), 6) # Use more precision for crypto
            # Add a small delay between API calls to avoid rate limiting
            time.sleep(0.2) 
        except Exception as e:
            logging.warning(f"API call to {provider['name']} for {name} failed: {str(e)}")
            time.sleep(0.2) # Delay even on failure

    # Fallback to hardcoded values if all APIs fail
    logging.warning(f"All APIs failed for crypto {name}. Falling back to hardcoded prices.")
    current_prices = {
        'bitcoin': 65337.34, 'ethereum': 3430.85, 'solana': 147.42,
        'binancecoin': 589.13, 'ripple': 0.5243, 'cardano': 0.3765,
        'dogecoin': 0.1234, 'polkadot': 6.78, 'avalanche': 32.45,
        'polygon': 0.7832
    }
    if crypto_id and crypto_id in current_prices:
        return current_prices[crypto_id]
    elif name.lower() in current_prices:
         return current_prices[name.lower()]

    logging.error(f"Cryptocurrency {name} not found in APIs or fallbacks.")
    return None

def fetch_coingecko(name_lower, crypto_id):
    # Try direct name first
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={name_lower}&vs_currencies=usd'
    response = requests.get(url, timeout=5)
    response.raise_for_status() # Raise exception for bad status codes
    data = response.json()
    if name_lower in data and 'usd' in data[name_lower]:
        return data[name_lower]['usd']
        
    # Try mapped ID if available and different from name_lower
    if crypto_id and crypto_id != name_lower:
        url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd'
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if crypto_id in data and 'usd' in data[crypto_id]:
            return data[crypto_id]['usd']
    return None
    
def fetch_binance(name_upper):
    symbol = name_upper + 'USDT'
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}'
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
    if 'price' in data:
        return data['price']
    return None

def fetch_yfinance_crypto(name_upper):
    import yfinance as yf
    ticker = yf.Ticker(f"{name_upper}-USD")
    # Use '1m' interval for more recent data, fallback to '1d' if needed
    data = ticker.history(period="1d", interval="1m", auto_adjust=True)
    if not data.empty:
        return data['Close'].iloc[-1]
    # Fallback to daily data if 1m fails
    data = ticker.history(period="1d", auto_adjust=True)
    if not data.empty:
         return data['Close'].iloc[-1]
    return None


def get_stock_price(symbol):
    """Get real-time stock price from multiple sources with fallbacks. Prioritizes APIs."""
    symbol_upper = symbol.upper()
    
    api_providers = [
        {'name': 'AlphaVantage', 'func': fetch_alphavantage, 'args': (symbol_upper,)},
        {'name': 'YahooFinance', 'func': fetch_yfinance_stock, 'args': (symbol_upper,)},
        {'name': 'FinancialModelingPrep', 'func': fetch_fmp, 'args': (symbol_upper,)}
    ]
    
    # Try APIs first
    for provider in api_providers:
        try:
            logging.debug(f"Trying API: {provider['name']} for {symbol_upper}")
            price = provider['func'](*provider['args'])
            if price is not None:
                logging.info(f"Got price {price} for {symbol_upper} from {provider['name']}")
                return round(float(price), 2)
            # Add a small delay between API calls
            time.sleep(0.2)
        except Exception as e:
            logging.warning(f"API call to {provider['name']} for {symbol_upper} failed: {str(e)}")
            time.sleep(0.2) # Delay even on failure
            
    # Fallback to hardcoded values if all APIs fail
    logging.warning(f"All APIs failed for stock {symbol_upper}. Falling back to hardcoded prices.")
    current_prices = {
        'AAPL': 214.09, 'MSFT': 428.52, 'GOOGL': 174.57, 'AMZN': 186.85,
        'TSLA': 248.30, 'META': 513.26, 'NVDA': 128.74, 'JPM': 198.43,
        'V': 278.56, 'WMT': 68.92
    }
    if symbol_upper in current_prices:
        return current_prices[symbol_upper]

    logging.error(f"Stock {symbol_upper} not found in APIs or fallbacks.")
    return None

def fetch_alphavantage(symbol_upper):
    api_key = 'J54VFE3RK2YHL5MN' # Use environment variable in production
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol_upper}&apikey={api_key}'
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
    quote = data.get('Global Quote', {})
    if quote and '05. price' in quote:
        return quote['05. price']
    return None
    
def fetch_yfinance_stock(symbol_upper):
    import yfinance as yf
    ticker = yf.Ticker(symbol_upper)
     # Use '1m' interval for more recent data, fallback to '1d' if needed
    data = ticker.history(period="1d", interval="1m", auto_adjust=True)
    if not data.empty:
        return data['Close'].iloc[-1]
    # Fallback to daily data if 1m fails
    data = ticker.history(period="1d", auto_adjust=True)
    if not data.empty:
         return data['Close'].iloc[-1]
    return None

def fetch_fmp(symbol_upper):
    # Note: Using 'demo' key has limits. Replace with your own key if available.
    api_key = 'demo' 
    url = f'https://financialmodelingprep.com/api/v3/quote-short/{symbol_upper}?apikey={api_key}'
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
    if data and isinstance(data, list) and len(data) > 0 and 'price' in data[0]:
        return data[0]['price']
    return None


def get_real_time_price(symbol, name, instrument_type):
    """Get real-time price based on instrument type using API calls first."""
    price = None
    
    # Standard API retrieval based on type
    try:
        if instrument_type == 'crypto':
            # Clean up symbol/name for API calls
            clean_name = name.lower().strip()
            if '/' in symbol:
                # For pairs like BTC/USD, use the base currency (BTC)
                clean_symbol_for_api = symbol.split('/')[0].lower().strip()
                price = get_crypto_price(clean_symbol_for_api)
            else:
                # Assume name is the primary identifier (e.g., 'bitcoin')
                price = get_crypto_price(clean_name)
        elif instrument_type == 'stock':
            clean_symbol_for_api = symbol.upper().strip()
            price = get_stock_price(clean_symbol_for_api)
        # Add logic for 'forex', 'commodities' if needed, using appropriate APIs/logic
        elif instrument_type == 'forex':
             # Example: Placeholder - integrate a real Forex API later
             logging.warning(f"Forex pricing not fully implemented for {symbol}. Using fallback.")
             price = get_forex_price_fallback(symbol) # Implement this
        elif instrument_type == 'commodities':
             # Example: Placeholder - integrate a real Commodities API later
             logging.warning(f"Commodities pricing not fully implemented for {symbol}. Using fallback.")
             price = get_commodity_price_fallback(symbol) # Implement this
        else:
            logging.error(f"Invalid instrument type: {instrument_type} for symbol {symbol}")
            return None
            
    except Exception as e:
        logging.error(f"Error during API price fetch for {symbol} ({instrument_type}): {str(e)}")
        price = None # Ensure price is None if API fetch fails

    if price is not None:
        # Format based on type
        if instrument_type == 'crypto':
             return round(float(price), 6)
        elif instrument_type == 'forex':
             return round(float(price), 4) # Forex usually uses 4 decimal places
        else: # Stocks, commodities
             return round(float(price), 2)

    # --- Fallback Logic ---
    logging.warning(f"API price fetch failed for {symbol}. Trying database price fallback.")
    
    # Fallback 1: Check database price (if reasonably recent)
    instrument = TradingInstrument.query.filter_by(symbol=symbol).first()
    if instrument and instrument.current_price and instrument.last_updated:
         time_since_update = datetime.utcnow() - instrument.last_updated
         # Only use DB price if it's less than ~5 minutes old, otherwise it's too stale
         if time_since_update.total_seconds() < 300: 
             logging.warning(f"Using recent database price {instrument.current_price} for {symbol}")
             # Apply very small random movement to simulate activity if needed, but prefer stale price
             # change = (1 + (random.random() * 0.1 - 0.05) / 100) # +/- 0.05%
             # return round(instrument.current_price * change, 6 if instrument_type == 'crypto' else (4 if instrument_type == 'forex' else 2))
             return instrument.current_price # Return the stale price directly
         else:
             logging.warning(f"Database price for {symbol} is too old ({time_since_update}).")

    # Fallback 2: Use hardcoded dictionary values (as defined in get_crypto/stock_price)
    logging.warning(f"Database fallback failed for {symbol}. Trying final hardcoded dictionary.")
    final_fallback_price = None
    if instrument_type == 'crypto':
        crypto_fallback_prices = {
            'bitcoin': 65337.34, 'ethereum': 3430.85, 'solana': 147.42,
            # ... add others from get_crypto_price ...
        }
        crypto_id = None
        crypto_mappings = { 'bitcoin': ['btc', 'bitcoin'], 'ethereum': ['eth', 'ethereum'], 'solana': ['sol', 'solana']}
        lookup_name = symbol.split('/')[0].lower().strip() if '/' in symbol else name.lower().strip()
        for base_id, aliases in crypto_mappings.items():
            if lookup_name in aliases or lookup_name == base_id:
                 crypto_id = base_id
                 break
        if crypto_id and crypto_id in crypto_fallback_prices:
            final_fallback_price = crypto_fallback_prices[crypto_id]
        elif lookup_name in crypto_fallback_prices:
            final_fallback_price = crypto_fallback_prices[lookup_name]
            
    elif instrument_type == 'stock':
        stock_fallback_prices = {
            'AAPL': 214.09, 'MSFT': 428.52, 'GOOGL': 174.57, 'AMZN': 186.85,
             # ... add others from get_stock_price ...
        }
        if symbol.upper() in stock_fallback_prices:
             final_fallback_price = stock_fallback_prices[symbol.upper()]
             
    # Add similar fallback logic for forex/commodities if needed

    if final_fallback_price is not None:
         logging.warning(f"Using final hardcoded dictionary price {final_fallback_price} for {symbol}")
         return final_fallback_price

    # Last resort: return a default/None if absolutely nothing works
    logging.error(f"Could not determine price for {symbol} using any method.")
    return None # Or maybe a default like 1.00? Returning None is safer.

# Placeholder functions for Forex/Commodities - replace with actual API calls
def get_forex_price_fallback(symbol):
    prices = {'EUR/USD': 1.0821, 'GBP/USD': 1.2673, 'USD/JPY': 153.42}
    return prices.get(symbol, 1.0)

def get_commodity_price_fallback(symbol):
    prices = {'GOLD': 2324.15, 'SILVER': 27.43, 'OIL': 78.32}
    return prices.get(symbol, 100.0)


@webtrader.route("/get_price/")
@login_required
def get_price():
    """Get current price for an instrument, using API first with 60s cache."""
    instrument_id = request.args.get('instrument_id')
    instrument = TradingInstrument.query.get_or_404(instrument_id)
    
    # Only get new price if last update was more than 60 seconds ago
    current_time = datetime.utcnow()
    if instrument.last_updated and (current_time - instrument.last_updated).total_seconds() < 60:
        # Return existing price if it was updated recently (within cache time)
        logging.debug(f"Using cached price {instrument.current_price} for {instrument.symbol}")
        return jsonify({
            'current_price': instrument.current_price,
            'change': instrument.change or 0.0
        })
    
    logging.debug(f"Cache expired or no recent price for {instrument.symbol}. Fetching live price.")
    # Get fresh price from API (or fallbacks)
    new_price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
    
    # Update the instrument in the database if a valid price was obtained
    if new_price is not None:
        try:
            # Determine precision based on type
            if instrument.type == 'crypto':
                precision = 6
            elif instrument.type == 'forex':
                precision = 4
            else: # Stocks, commodities
                precision = 2
                
            new_price = round(float(new_price), precision)
            
            # Only update if the price has actually changed to avoid unnecessary DB writes
            if instrument.current_price != new_price:
                try:
                    # Use the new update_price method to calculate change percentage
                    instrument.update_price(new_price)
                    db.session.commit()
                    logging.info(f"Updated DB price for {instrument.symbol} to {new_price} (change: {instrument.change}%)")
                except Exception as e:
                    # If update_price fails (possibly due to missing column), fall back to direct update
                    logging.error(f"Error in update_price for {instrument.symbol}: {str(e)}")
                    instrument.current_price = new_price
                    instrument.change = 0.0  # Default no change
                    instrument.last_updated = current_time
                    db.session.commit()
            else:
                # Price hasn't changed, but update timestamp to refresh cache
                instrument.last_updated = current_time
                db.session.commit()
                logging.debug(f"Price for {instrument.symbol} hasn't changed ({new_price}). Updated timestamp.")

        except (ValueError, TypeError) as e:
            logging.error(f"Error converting/saving price {new_price} for {instrument.symbol}: {str(e)}")
            # Return the last known good price from DB if conversion fails, or None
            return jsonify({
                'current_price': instrument.current_price if instrument.current_price else None,
                'change': instrument.change or 0.0
            })
    else:
         # If get_real_time_price returned None (failure)
         logging.error(f"Failed to get valid price for {instrument.symbol}. Returning last known DB price.")
         # Return the last known price from DB even if it's old, or None if never set
         return jsonify({
             'current_price': instrument.current_price if instrument.current_price else None,
             'change': instrument.change or 0.0
         })

    return jsonify({
        'current_price': new_price,
        'change': instrument.change or 0.0
    })

@webtrader.route("/", methods=['GET', 'POST'])
@login_required
def webtrader_dashboard():
    if not current_user.is_client:
        flash('Access denied. This area is for clients only.', 'danger')
        return redirect(url_for('main.home'))

    form = TradeForm()
    instruments = TradingInstrument.query.all()
    
    # Ensure all instruments have valid values
    for instrument in instruments:
        if instrument.current_price is None:
            # Initialize price for instruments with None values
            price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
            if price:
                instrument.current_price = price
                instrument.previous_price = price
                instrument.change = 0.0
                instrument.last_updated = datetime.utcnow()
                db.session.commit()
        # Ensure change is not None
        if instrument.change is None:
            instrument.change = 0.0
            db.session.commit()

    if form.validate_on_submit():
        # Check if the user is allowed to trade
        if hasattr(current_user, 'available_to_trade') and not current_user.available_to_trade:
            flash('Your account is currently not allowed to open new trades. Please contact support.', 'danger')
            return redirect(url_for('webtrader.webtrader_dashboard'))
            
        instrument_id = form.instrument_id.data
        amount = form.amount.data
        trade_type = form.trade_type.data
        order_type = form.order_type.data
        target_price = form.target_price.data if form.target_price.data else None

        # Validate inputs
        if amount <= 0:
            flash('Amount must be greater than zero.', 'danger')
            return redirect(url_for('webtrader.webtrader_dashboard'))
            
        instrument = TradingInstrument.query.get(instrument_id)
        if not instrument:
            flash('Invalid instrument selected.', 'danger')
            return redirect(url_for('webtrader.webtrader_dashboard'))

        # Get current price
        current_price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
        if not current_price:
            flash('Unable to get current price. Please try again.', 'danger')
            return redirect(url_for('webtrader.webtrader_dashboard'))

        if order_type == 'market':
            execute_market_order(current_user, instrument, amount, current_price, trade_type)
        elif order_type in ['limit', 'stop_loss', 'take_profit']:
            if not target_price or target_price <= 0:
                flash('Target price is required for limit, stop-loss, and take-profit orders.', 'danger')
                return redirect(url_for('webtrader.webtrader_dashboard'))
                
            store_order(current_user, instrument, amount, order_type, target_price, trade_type)
        else:
            flash('Invalid order type.', 'danger')
            
        return redirect(url_for('webtrader.webtrader_dashboard'))

    # Get user's trades
    open_trades = Trade.query.filter_by(lead_id=current_user.id, status='open').all()
    closed_trades = Trade.query.filter_by(lead_id=current_user.id, status='closed').all()
    pending_orders = Trade.query.filter_by(lead_id=current_user.id, status='pending').all()

    # Get user's trading status
    available_to_trade = True
    if hasattr(current_user, 'available_to_trade'):
        available_to_trade = current_user.available_to_trade

    return render_template('webtrader/webtrader.html', title='Webtrader', form=form, instruments=instruments,
                          open_trades=open_trades, closed_trades=closed_trades, pending_orders=pending_orders,
                          available_to_trade=available_to_trade)


def execute_market_order(user, instrument, amount, current_price, trade_type):
    """Execute a market order for buying or selling"""
    # Check if user is allowed to trade
    if hasattr(user, 'available_to_trade') and not user.available_to_trade:
        flash('Your account is currently not allowed to open new trades. Please contact support.', 'danger')
        return False
        
    # Calculate how many units we're trading based on the amount
    units = round(amount / current_price, 6)
    
    # Check if user has sufficient balance
    if user.current_balance >= amount:
        trade = Trade(
            lead_id=user.id,
            instrument_id=instrument.id,
            amount=units,
            price=round(current_price, 6),
            trade_type=trade_type,  # Use the passed trade_type parameter
            date=datetime.utcnow(),
            status='open'
        )
        
        # Deduct the amount from user's balance
        user.current_balance = round(user.current_balance - amount, 2)
        
        db.session.add(trade)
        db.session.commit()
        flash(f'{trade_type.capitalize()} position opened successfully!', 'success')
        return True
    else:
        flash('Insufficient balance to open position.', 'danger')
        return False

def store_order(user, instrument, amount, order_type, target_price, trade_type):
    """Store a pending order with target price"""
    # Check if user is allowed to trade
    if hasattr(user, 'available_to_trade') and not user.available_to_trade:
        flash('Your account is currently not allowed to open new trades. Please contact support.', 'danger')
        return False
        
    # Check if user has sufficient balance
    if user.current_balance < amount:
        flash('Insufficient balance to place order.', 'danger')
        return False
        
    # Calculate units based on target price for limit orders
    units = round(amount / target_price, 6)
    
    # Create the pending trade
    trade = Trade(
        lead_id=user.id,
        instrument_id=instrument.id,
        amount=units,
        price=target_price,  # The price we want to execute at
        trade_type=trade_type,  # buy or sell
        order_type=order_type,  # limit, stop_loss, or take_profit
        target_price=target_price,
        date=datetime.utcnow(),
        status='pending'
    )
    
    # Reserve the funds from the user's balance
    user.current_balance = round(user.current_balance - amount, 2)
    
    db.session.add(trade)
    db.session.commit()
    flash(f'{order_type.replace("_", " ").title()} {trade_type} order placed successfully!', 'success')
    return True

@webtrader.route("/execute_trade", methods=['POST'])
@login_required
def execute_trade():
    # Check if the user is allowed to trade
    if hasattr(current_user, 'available_to_trade') and not current_user.available_to_trade:
        flash('Your account is currently not allowed to open new trades. Please contact support.', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))
        
    form = TradeForm()
    if form.validate_on_submit():
        instrument_id = form.instrument_id.data
        amount = form.amount.data
        trade_type = form.trade_type.data
        order_type = form.order_type.data
        target_price = form.target_price.data if form.target_price.data else None

        instrument = TradingInstrument.query.get(instrument_id)
        if not instrument:
            flash('Invalid instrument selected.', 'danger')
            return redirect(url_for('webtrader.webtrader_dashboard'))
            
        # Ensure amount is positive
        if amount <= 0:
            flash('Amount must be greater than zero.', 'danger')
            return redirect(url_for('webtrader.webtrader_dashboard'))

        # Get latest price
        current_price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
        if not current_price:
            flash('Unable to get current price. Please try again.', 'danger')
            return redirect(url_for('webtrader.webtrader_dashboard'))

        # Execute different order types
        if order_type == 'market':
            execute_market_order(current_user, instrument, amount, current_price, trade_type)
        elif order_type in ['limit', 'stop_loss', 'take_profit']:
            if not target_price or target_price <= 0:
                flash('Target price is required for limit, stop-loss, and take-profit orders.', 'danger')
                return redirect(url_for('webtrader.webtrader_dashboard'))
                
            store_order(current_user, instrument, amount, order_type, target_price, trade_type)
        else:
            flash('Invalid order type.', 'danger')

    else:
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
                
    return redirect(url_for('webtrader.webtrader_dashboard'))

@webtrader.route("/close_trade", methods=['POST'])
@login_required
def close_trade():
    trade_id = request.form.get('trade_id')
    trade = Trade.query.get_or_404(trade_id)
    
    # Verify ownership
    if trade.lead_id != current_user.id:
        flash('Access denied. This is not your trade.', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))
    
    # Verify trade is still open
    if trade.status != 'open':
        flash('This trade is already closed.', 'warning')
        return redirect(url_for('webtrader.webtrader_dashboard'))

    # Get current price for the instrument
    current_price = get_real_time_price(trade.instrument.symbol, trade.instrument.name, trade.instrument.type)
    if not current_price:
        flash('Unable to get current price. Please try again.', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))
    
    # Update trade with closing info
    trade.closing_price = round(current_price, 6)
    trade.status = 'closed'
    
    # Calculate profit/loss
    trade.calculate_profit_loss()
    db.session.commit()

    # Calculate initial investment and profit/loss
    initial_investment = trade.amount * trade.price  # Units * price per unit
    profit_loss = trade.profit_loss if trade.profit_loss is not None else 0.0
    
    # Log trade details for debugging
    logging.info(f"Closing trade {trade_id}: {trade.trade_type} {trade.amount} {trade.instrument.symbol} at {trade.price}, " + 
                 f"closing at {trade.closing_price}, P/L: {profit_loss}")

    # Return funds to user with profit/loss
    if trade.trade_type == 'buy':
        # For buy trades, we add the original value + profit/loss
        amount_to_return = initial_investment + profit_loss
    elif trade.trade_type == 'sell':
        # For sell trades, we add the original investment + profit/loss
        amount_to_return = initial_investment + profit_loss
    else:
        flash('Invalid trade type.', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))
    
    # Update user balance
    current_user.update_balance(round(amount_to_return, 2))
    
    flash(f'Trade closed successfully! {"Profit" if profit_loss > 0 else "Loss"}: {abs(profit_loss):.2f}', 'success')
    return redirect(url_for('webtrader.webtrader_dashboard'))

@webtrader.route("/instruments")
@login_required
def list_instruments():
    instruments = TradingInstrument.query.all()
    return render_template("webtrader/list_instruments.html", instruments=instruments)

@webtrader.route("/instruments/new", methods=['GET', 'POST'])
@login_required
def new_instrument():
    form = InstrumentForm()
    if form.validate_on_submit():
        current_price = get_real_time_price(form.symbol.data.upper(), form.name.data, form.type.data)
        instrument = TradingInstrument(
            symbol=form.symbol.data.upper(),
            name=form.name.data,
            type=form.type.data,
            current_price=current_price,
            last_updated=datetime.utcnow()
        )
        db.session.add(instrument)
        db.session.commit()
        flash('Instrument has been created!', 'success')
        return redirect(url_for('webtrader.list_instruments'))
    return render_template("webtrader/form.html", form=form, title="New Instrument")

@webtrader.route("/instruments/edit/", methods=['GET', 'POST'])
@login_required
def edit_instrument():
    instrument_id = request.args.get('instrument_id')
    instrument = TradingInstrument.query.get_or_404(instrument_id)
    form = InstrumentForm(obj=instrument)
    if form.validate_on_submit():
        instrument.symbol = form.symbol.data.upper()
        instrument.name = form.name.data
        instrument.type = form.type.data
        instrument.current_price = get_real_time_price(form.symbol.data.upper(), form.name.data, form.type.data)
        instrument.last_updated = datetime.utcnow()
        db.session.commit()
        flash('Instrument has been updated!', 'success')
        return redirect(url_for('webtrader.list_instruments'))
    return render_template("webtrader/form.html", form=form, title="Edit Instrument")

@webtrader.route("/instruments/delete/", methods=['POST'])
@login_required
def delete_instrument():
    instrument_id = request.form.get('instrument_id')
    instrument = TradingInstrument.query.get_or_404(instrument_id)
    db.session.delete(instrument)
    db.session.commit()
    flash('Instrument has been deleted!', 'success')
    return redirect(url_for('webtrader.list_instruments'))

@webtrader.route("/get_instrument_details/")
@login_required
def get_instrument_details():
    instrument_id = request.args.get('instrument_id')
    instrument = TradingInstrument.query.get_or_404(instrument_id)
    
    # Calculate bid/ask prices based on a small spread (0.05%)
    current_price = instrument.current_price or 0.0
    spread = current_price * 0.0005  # 0.05% spread
    bid_price = round(current_price - spread/2, 2)
    ask_price = round(current_price + spread/2, 2)
    
    return jsonify({
        'symbol': instrument.symbol,
        'name': instrument.name,
        'current_price': instrument.current_price,
        'change': instrument.change or 0.0,
        'bid_price': bid_price,
        'ask_price': ask_price,
        'type': instrument.type
    })

@webtrader.route("/update_all_prices", methods=['POST'])
@login_required
def update_all_prices():
    """Update prices for all instruments more efficiently with concurrent API calls"""
    if not current_user.is_admin:
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('webtrader.list_instruments'))
        
    instruments = TradingInstrument.query.all()
    updated_count = 0
    now = datetime.utcnow()
    
    # Use multithreading to update prices concurrently
    try:
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        def update_instrument(instrument):
            try:
                # Add slight delay to avoid hammering APIs simultaneously
                time.sleep(0.1 * random.random())  # Random delay between 0-100ms
                new_price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
                if new_price:
                    # Use the new update_price method instead of direct assignment
                    instrument.update_price(new_price)
                    return True
                return False
            except Exception as e:
                logging.error(f"Error updating price for {instrument.symbol}: {str(e)}")
                return False
        
        # Use ThreadPoolExecutor for concurrent updates
        with ThreadPoolExecutor(max_workers=min(10, len(instruments))) as executor:
            results = list(executor.map(update_instrument, instruments))
            updated_count = sum(results)
            
        db.session.commit()
        flash(f'Updated prices for {updated_count} out of {len(instruments)} instruments', 'success')
        
    except Exception as e:
        # Fallback to sequential updates if ThreadPoolExecutor fails
        logging.error(f"Error with concurrent updates: {str(e)}")
        
        for instrument in instruments:
            try:
                new_price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
                if new_price:
                    instrument.current_price = new_price
                    instrument.last_updated = now
                    updated_count += 1
            except Exception as e:
                logging.error(f"Error updating price for {instrument.symbol}: {str(e)}")
        
        db.session.commit()
        flash(f'Updated prices for {updated_count} out of {len(instruments)} instruments', 'success')
        
    return redirect(url_for('webtrader.list_instruments'))

@webtrader.route("/cancel_order", methods=['POST'])
@login_required
def cancel_order():
    """Cancel a pending order and refund the reserved amount"""
    order_id = request.form.get('order_id')
    if not order_id:
        flash('No order ID provided', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))
        
    order = Trade.query.get_or_404(order_id)
    
    # Verify ownership
    if order.lead_id != current_user.id:
        flash('Access denied. This is not your order.', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))
        
    # Verify order is still pending
    if order.status != 'pending':
        flash('This order is not pending.', 'warning')
        return redirect(url_for('webtrader.webtrader_dashboard'))
        
    # Calculate amount to refund (amount of units * target price)
    refund_amount = round(order.amount * order.price, 2)
    
    # Refund the amount to the user's balance
    current_user.current_balance = round(current_user.current_balance + refund_amount, 2)
    
    # Delete the order
    db.session.delete(order)
    db.session.commit()
    
    flash(f'Order canceled and ${refund_amount} has been refunded to your balance.', 'success')
    return redirect(url_for('webtrader.webtrader_dashboard'))

@webtrader.route("/check_pending_orders", methods=['GET', 'POST'])
@login_required
def check_pending_orders():
    """Check all pending orders and execute them if conditions are met"""
    if not current_user.is_admin:
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('webtrader.list_instruments'))
        
    pending_orders = Trade.query.filter_by(status='pending').all()
    executed_count = 0
    
    for order in pending_orders:
        try:
            # Get current price for the instrument
            current_price = get_real_time_price(order.instrument.symbol, order.instrument.name, order.instrument.type)
            if not current_price:
                continue
                
            # Determine if order should be executed based on type and target price
            should_execute = False
            
            if order.order_type == 'limit':
                if order.trade_type == 'buy' and current_price <= order.target_price:
                    should_execute = True
                elif order.trade_type == 'sell' and current_price >= order.target_price:
                    should_execute = True
                    
            elif order.order_type == 'stop_loss':
                if order.trade_type == 'buy' and current_price >= order.target_price:
                    should_execute = True
                elif order.trade_type == 'sell' and current_price <= order.target_price:
                    should_execute = True
                    
            elif order.order_type == 'take_profit':
                if order.trade_type == 'buy' and current_price >= order.target_price:
                    should_execute = True
                elif order.trade_type == 'sell' and current_price <= order.target_price:
                    should_execute = True
                    
            # Execute the order if conditions are met
            if should_execute:
                # Convert pending order to open trade
                order.status = 'open'
                order.price = current_price
                executed_count += 1
                
                # Log the execution
                logging.info(f"Executed pending order {order.id}: {order.trade_type} {order.amount} {order.instrument.symbol} at {current_price}")
                
        except Exception as e:
            logging.error(f"Error processing pending order {order.id}: {str(e)}")
    
    db.session.commit()
    
    flash(f'Executed {executed_count} out of {len(pending_orders)} pending orders', 'success')
    return redirect(url_for('webtrader.list_instruments'))
