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
import json

logging.basicConfig(level=logging.DEBUG)

webtrader = Blueprint('webtrader', __name__)

# 🎯 ONLY TWELVE DATA API - Old Binance WebSocket code removed

def get_real_time_price(symbol, name, instrument_type):
    """Get real-time price ONLY from Twelve Data API - NO MORE MIXED SOURCES"""
    
    # 🎯 TWELVE DATA API ONLY - Clean and Consistent
    try:
        logging.info(f"🎯 Getting Twelve Data price for {symbol} ({instrument_type})")
        price = get_twelve_data_price(symbol, instrument_type)
        
        if price:
            # Format based on type with proper precision
            if instrument_type == 'crypto':
                return round(float(price), 6)
            elif instrument_type == 'forex':
                return round(float(price), 5)
            elif instrument_type == 'commodity':
                return round(float(price), 2)
            else:  # stocks
                return round(float(price), 2)
        else:
            logging.warning(f"⚠️ Twelve Data API returned None for {symbol}")
            
    except Exception as e:
        logging.error(f"❌ Twelve Data API error for {symbol}: {str(e)}")
    
    # 🚫 NO MORE FALLBACKS - Only use Twelve Data or return None
    # This prevents price conflicts and ensures consistency
    logging.error(f"❌ Could not get Twelve Data price for {symbol}")
    return None


@webtrader.route("/get_price/")
@login_required
def get_price():
    """Get current price for an instrument - ONLY from database (background worker handles updates)"""
    instrument_id = request.args.get('instrument_id')
    instrument = TradingInstrument.query.get_or_404(instrument_id)
    
    # 🚀 MAIN APP PERFORMANCE FIX: Never call APIs, only read from DB
    # The dedicated price_worker handles all external API calls
    logging.debug(f"📊 Reading cached price for {instrument.symbol}: ${instrument.current_price}")
    
    # Always return the database price (updated by background worker)
    current_price = instrument.current_price if instrument.current_price else 0.0
    change = instrument.change if instrument.change else 0.0
    
    return jsonify({
        'current_price': current_price,
        'change': change
    })

@webtrader.route("/", methods=['GET', 'POST'])
@login_required
def webtrader_dashboard():
    if not current_user.is_client:
        flash('Access denied. This area is for clients only.', 'danger')
        return redirect(url_for('main.home'))

    form = TradeForm()
    instruments = TradingInstrument.query.all()
    
    # 🚫 WEBSOCKET DISABLED FOR PERFORMANCE TESTING
    # Commenting out WebSocket to test if it's causing the performance issues
    try:
        logging.info("⚠️  WebSocket disabled for performance testing")
        # Get all crypto instruments from database
        # crypto_instruments = TradingInstrument.query.filter_by(type='crypto').all()
        
        # if crypto_instruments:
        #     # Extract symbols and convert to Binance format (lowercase + usdt)
        #     binance_symbols = []
        #     for instrument in crypto_instruments:
        #         symbol = instrument.symbol
        #         if '/' in symbol:
        #             # Convert BTC/USD -> btcusdt
        #             base_symbol = symbol.split('/')[0].lower()
        #             binance_symbol = f"{base_symbol}usdt"
        #             binance_symbols.append(binance_symbol)
        #             logging.info(f"📈 Mapping {symbol} → {binance_symbol}")
        #     
        #     if binance_symbols:
        #         # Start WebSocket connection using the EXACT working pattern
        #         start_crypto_websocket(binance_symbols)
        #         logging.info(f"🎉 Started Binance WebSocket for {len(binance_symbols)} crypto instruments!")
        #         logging.info(f"🔗 Symbols: {', '.join(binance_symbols)}")
        #     else:
        #         logging.warning("⚠️  No valid crypto symbols found for WebSocket")
        # else:
        #     logging.warning("⚠️  No crypto instruments found in database")
            
    except Exception as e:
        logging.error(f"Error starting crypto WebSocket: {e}")
    
    # Ensure all instruments have valid values - but don't make API calls
    for instrument in instruments:
        if instrument.current_price is None:
            # Set default price if None - background worker will update it
            instrument.current_price = 100.0  # Default placeholder
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

        # 🚀 PERFORMANCE: Get current price from database only (no API calls)
        current_price = instrument.current_price
        if not current_price or current_price <= 0:
            flash('Price not available. Please try again in a moment.', 'danger')
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

# 🎯 ONLY TWELVE DATA API FUNCTIONS REMAIN ACTIVE

# Twelve Data WebSocket Integration
def get_twelve_data_websocket_config():
    """Get WebSocket configuration for Twelve Data real-time feeds"""
    return {
        'url': 'wss://ws.twelvedata.com/v1/quotes/price',
        'api_key': '902d8585e8c040f591a3293d1b79ab88',  # Your actual Twelve Data API key
        'subscription_limit': 500  # Pro plan WebSocket credits
    }

def get_twelve_data_price(symbol, instrument_type='forex'):
    """Get real-time price from Twelve Data API with commodity support - FOR PRICE WORKER ONLY"""
    try:
        # Map internal symbols to Twelve Data format
        symbol_mapping = {
            # Forex - already compatible
            'EUR/USD': 'EUR/USD',
            'GBP/USD': 'GBP/USD',
            'USD/JPY': 'USD/JPY',
            'USD/CHF': 'USD/CHF',
            'AUD/USD': 'AUD/USD',
            'USD/CAD': 'USD/CAD',
            'NZD/USD': 'NZD/USD',
            'EUR/GBP': 'EUR/GBP',
            'EUR/JPY': 'EUR/JPY',
            'GBP/JPY': 'GBP/JPY',
            'EUR/CHF': 'EUR/CHF',
            'GBP/CHF': 'GBP/CHF',
            'AUD/JPY': 'AUD/JPY',
            'CAD/JPY': 'CAD/JPY',
            'CHF/JPY': 'CHF/JPY',
            'USD/TRY': 'USD/TRY',
            'USD/ZAR': 'USD/ZAR',
            'USD/MXN': 'USD/MXN',
            'USD/SGD': 'USD/SGD',
            'USD/NOK': 'USD/NOK',
            'USD/SEK': 'USD/SEK',
            
            # Crypto - Twelve Data format
            'BTC/USD': 'BTC/USD',
            'ETH/USD': 'ETH/USD',
            'ADA/USD': 'ADA/USD',
            'SOL/USD': 'SOL/USD',
            'DOT/USD': 'DOT/USD',
            'AVAX/USD': 'AVAX/USD',
            'MATIC/USD': 'MATIC/USD',
            'LINK/USD': 'LINK/USD',
            'UNI/USD': 'UNI/USD',
            'LTC/USD': 'LTC/USD',
            'XRP/USD': 'XRP/USD',
            'DOGE/USD': 'DOGE/USD',
            'SHIB/USD': 'SHIB/USD',
            'ATOM/USD': 'ATOM/USD',
            'ALGO/USD': 'ALGO/USD',
            'XLM/USD': 'XLM/USD',
            'VET/USD': 'VET/USD',
            'FIL/USD': 'FIL/USD',
            
            # Commodities - Twelve Data symbols
            'XAU/USD': 'XAU/USD',  # Gold
            'XAG/USD': 'XAG/USD',  # Silver
            'XPT/USD': 'XPT/USD',  # Platinum
            'XPD/USD': 'XPD/USD',  # Palladium
            'COPPER': 'COPPER',
            'WTI': 'WTI',          # Crude Oil
            'BRENT': 'BRENT',      # Brent Oil
            'NATGAS': 'NATGAS',    # Natural Gas
            'GASOLINE': 'GASOLINE',
            'HEATING_OIL': 'HEATING_OIL',
            'WHEAT': 'WHEAT',
            'CORN': 'CORN',
            'SOYBEANS': 'SOYBEANS',
            'COFFEE': 'COFFEE',
            'SUGAR': 'SUGAR',
            'COTTON': 'COTTON',
            
            # Stocks
            'AAPL': 'AAPL',
            'MSFT': 'MSFT',
            'GOOGL': 'GOOGL',
            'AMZN': 'AMZN',
            'TSLA': 'TSLA',
            'META': 'META',
            'NVDA': 'NVDA',
            'NFLX': 'NFLX',
            'DIS': 'DIS',
            'PYPL': 'PYPL',
            'ADBE': 'ADBE',
            'CRM': 'CRM',
            'ZOOM': 'ZOOM',
            'UBER': 'UBER',
            'SPOT': 'SPOT'
        }
        
        # Get mapped symbol
        twelve_data_symbol = symbol_mapping.get(symbol, symbol)
        
        # API endpoint for real-time price
        url = f'https://api.twelvedata.com/price'
        params = {
            'symbol': twelve_data_symbol,
            'apikey': '902d8585e8c040f591a3293d1b79ab88'  # Your actual Twelve Data API key
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if 'price' in data:
            price = float(data['price'])
            logging.info(f"Got Twelve Data price {price} for {symbol}")
            return price
        elif 'message' in data:
            logging.warning(f"Twelve Data API message for {symbol}: {data['message']}")
            
    except Exception as e:
        logging.warning(f"Twelve Data API call for {symbol} failed: {str(e)}")
    
    # Fallback to existing methods
    if instrument_type == 'crypto':
        return get_twelve_data_price(symbol.split('/')[0])  # Use base currency
    elif instrument_type == 'commodity':
        return get_twelve_data_price(symbol)
    else:
        return get_twelve_data_price(symbol)


def execute_market_order(user, instrument, amount, current_price, trade_type):
    """Execute a market order for buying or selling - using DB price only"""
    # Check if user is allowed to trade
    if hasattr(user, 'available_to_trade') and not user.available_to_trade:
        flash('Your account is currently not allowed to open new trades. Please contact support.', 'danger')
        return False
        
    # 🚀 PERFORMANCE: Use the passed current_price (from DB) directly, no API calls
    if not current_price or current_price <= 0:
        flash('Invalid price. Please try again.', 'danger')
        return False
        
    # FIXED: Treat 'amount' as the number of units (e.g., 2 ETH), not USD value
    units = round(amount, 6)  # Amount is already the units the user wants
    usd_cost = round(units * current_price, 2)  # Calculate USD cost = units * price
    
    # Check if user has sufficient balance for the USD cost
    if user.current_balance >= usd_cost:
        trade = Trade(
            lead_id=user.id,
            instrument_id=instrument.id,
            amount=units,
            price=round(current_price, 6),
            trade_type=trade_type,  # Use the passed trade_type parameter
            date=datetime.utcnow(),
            status='open'
        )
        
        # Deduct the USD cost from user's balance
        user.current_balance = round(user.current_balance - usd_cost, 2)
        
        db.session.add(trade)
        db.session.commit()
        flash(f'{trade_type.capitalize()} position opened successfully! {units} units for ${usd_cost:.2f}', 'success')
        return True
    else:
        flash(f'Insufficient balance. Need ${usd_cost:.2f} for {units} units.', 'danger')
        return False

def store_order(user, instrument, amount, order_type, target_price, trade_type):
    """Store a pending order with target price"""
    # Check if user is allowed to trade
    if hasattr(user, 'available_to_trade') and not user.available_to_trade:
        flash('Your account is currently not allowed to open new trades. Please contact support.', 'danger')
        return False
        
    # FIXED: Treat 'amount' as the number of units (e.g., 2 ETH), not USD value
    units = round(amount, 6)  # Amount is already the units the user wants
    usd_cost = round(units * target_price, 2)  # Calculate USD cost = units * target_price
    
    # Check if user has sufficient balance for the USD cost
    if user.current_balance < usd_cost:
        flash(f'Insufficient balance. Need ${usd_cost:.2f} for {units} units at ${target_price:.2f}.', 'danger')
        return False
    
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
    
    # Reserve the USD cost from the user's balance
    user.current_balance = round(user.current_balance - usd_cost, 2)
    
    db.session.add(trade)
    db.session.commit()
    flash(f'{order_type.replace("_", " ").title()} {trade_type} order placed for {units} units at ${target_price:.2f}!', 'success')
    return True

@webtrader.route("/start_realtime_feeds", methods=['POST'])
@login_required
def start_realtime_feeds():
    """🚫 WEBSOCKET DISABLED - Background worker handles all price updates"""
    logging.info("🚫 WebSocket feeds disabled - using dedicated background price worker")
    
    return jsonify({
        'success': False,
        'message': 'WebSocket feeds disabled for performance. Background worker handles price updates.',
        'status': 'disabled'
    })

# Add remaining routes here - keeping this short to avoid file being too long
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
        current_price = get_twelve_data_price(form.symbol.data.upper(), form.type.data)
        if current_price:
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
        else:
            flash('Could not fetch price from Twelve Data API. Please check the symbol.', 'danger')
    return render_template("add_instrument.html", form=form, title="New Instrument")

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
        instrument.current_price = get_twelve_data_price(form.symbol.data.upper(), form.name.data, form.type.data)
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
                new_price = get_twelve_data_price(instrument.symbol, instrument.name, instrument.type)
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
                new_price = get_twelve_data_price(instrument.symbol, instrument.name, instrument.type)
                if new_price:
                    instrument.current_price = new_price
                    instrument.last_updated = now
                    updated_count += 1
            except Exception as e:
                logging.error(f"Error updating price for {instrument.symbol}: {str(e)}")
        
        db.session.commit()
        flash(f'Updated prices for {updated_count} out of {len(instruments)} instruments', 'success')
        
    return redirect(url_for('webtrader.list_instruments'))

@webtrader.route("/update_price", methods=['POST'])
@login_required
def update_price_from_websocket():
    """Update instrument price from WebSocket - SUPPLEMENTARY to price worker"""
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        price = data.get('price')
        
        if not symbol or not price:
            return jsonify({'success': False, 'message': 'Missing symbol or price'}), 400
            
        # Find instrument by symbol
        instrument = TradingInstrument.query.filter_by(symbol=symbol).first()
        if not instrument:
            return jsonify({'success': False, 'message': f'Instrument {symbol} not found'}), 404
            
        # Update price using the model's update_price method
        instrument.update_price(float(price))
        db.session.commit()
        
        logging.info(f"📡 WebSocket updated {symbol}: ${price}")
        
        return jsonify({
            'success': True, 
            'symbol': symbol, 
            'price': price,
            'change': instrument.change
        })
        
    except Exception as e:
        logging.error(f"Error updating price from WebSocket: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@webtrader.route("/cancel_order", methods=['POST'])
@login_required
def cancel_order():
    """Cancel a pending order and refund the reserved amount"""
    order_id = request.form.get('order_id')
    
    if not order_id:
        flash('No order ID provided', 'error')
        return redirect(url_for('webtrader.webtrader_dashboard'))
    
    # Find the pending order
    order = Trade.query.filter_by(id=order_id, lead_id=current_user.id, status='pending').first()
    
    if not order:
        flash('Order not found or already processed', 'error')
        return redirect(url_for('webtrader.webtrader_dashboard'))

    try:
        # 🔧 CRITICAL FIX: Calculate the reserved amount to refund
        reserved_amount = order.amount * order.target_price
        
        # Cancel the order
        order.status = 'cancelled'
        
        # 🔧 CRITICAL FIX: Refund the reserved money
        if current_user.current_balance is None:
            current_user.current_balance = 0.0
            
        current_user.current_balance += reserved_amount
        
        db.session.commit()
        
        flash(f'Order cancelled successfully! Refunded: ${reserved_amount:.2f}', 'success')
        logging.info(f"💰 Order {order_id} cancelled, refunded ${reserved_amount:.2f} to user {current_user.id}")
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"❌ Error cancelling order: {str(e)}")
        flash(f'Error cancelling order: {str(e)}', 'error')

    return redirect(url_for('webtrader.webtrader_dashboard'))

@webtrader.route("/check_pending_orders", methods=['GET', 'POST'])
@login_required
def check_pending_orders():
    """Check all pending orders and execute them if conditions are met - using database prices only"""
    if not current_user.is_admin:
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('webtrader.list_instruments'))
        
    pending_orders = Trade.query.filter_by(status='pending').all()
    executed_count = 0
    
    for order in pending_orders:
        try:
            # 🚀 PERFORMANCE: Get current price from database only (no API calls)
            current_price = order.instrument.current_price
            if not current_price or current_price <= 0:
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

@webtrader.route("/stop_realtime_feeds", methods=['POST'])
@login_required
def stop_realtime_feeds():
    try:
        from omcrm.webtrader.realtime_data import real_time_manager
        
        if real_time_manager.is_running:
            real_time_manager.stop_real_time_feeds()
            logging.info("🛑 Stopped real-time WebSocket feeds")
            
            return jsonify({
                'success': True,
                'status': 'stopped'
            })
        else:
            return jsonify({
                'success': False,
                'status': 'already_stopped'
            })
            
    except Exception as e:
        logging.error(f"Error stopping real-time feeds: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to stop real-time feeds: {str(e)}'
        })

@webtrader.route("/close_trade", methods=['POST'])
@login_required
def close_trade():
    """Close an open trade - using database prices only"""
    trade_id = request.form.get('trade_id')
    
    if not trade_id:
        flash('No trade ID provided', 'error')
        return redirect(url_for('webtrader.webtrader_dashboard'))
    
    # 🔧 FIX: Use 'lead_id' instead of 'user_id' (Trade model uses lead_id)
    trade = Trade.query.filter_by(id=trade_id, lead_id=current_user.id, status='open').first()
    
    if not trade:
        flash('Trade not found or already closed', 'error')
        return redirect(url_for('webtrader.webtrader_dashboard'))
    
    try:
        # 🚀 PERFORMANCE: Get current price from database only (no API calls)
        current_price = trade.instrument.current_price
        
        if not current_price or current_price <= 0:
            flash('Price not available. Please try again in a moment.', 'error')
            return redirect(url_for('webtrader.webtrader_dashboard'))
        
        # Calculate profit/loss
        if trade.trade_type == 'buy':
            # For buy trades: profit = (current_price - entry_price) * amount
            profit_loss = (current_price - trade.price) * trade.amount
        else:
            # For sell trades: profit = (entry_price - current_price) * amount
            profit_loss = (trade.price - current_price) * trade.amount
        
        # 🔧 CRITICAL FIX: Calculate the original trade cost that was deducted when opening
        original_trade_cost = trade.amount * trade.price
        
        # 🔧 DEBUG: Log balance update details
        old_balance = current_user.current_balance
        logging.info(f"💰 BALANCE UPDATE: Trade ID={trade_id}, Old Balance=${old_balance:.2f}")
        logging.info(f"💰 TRADE DETAILS: Amount={trade.amount}, Entry Price=${trade.price:.2f}, Original Cost=${original_trade_cost:.2f}")
        logging.info(f"💰 CURRENT PRICE: ${current_price:.2f}, P/L=${profit_loss:.2f}")
        
        # Update trade
        trade.status = 'closed'
        trade.closing_price = current_price  # Changed from close_price to closing_price
        trade.profit_loss = profit_loss
        trade.closing_date = datetime.utcnow()  # Changed from close_date to closing_date
        
        # 🔧 CRITICAL FIX: Refund original trade cost AND add profit/loss
        if current_user.current_balance is None:
            current_user.current_balance = 0.0
        
        # Refund the original money that was "locked up" in the trade
        current_user.current_balance += original_trade_cost
        logging.info(f"💰 AFTER REFUNDING ORIGINAL COST: ${current_user.current_balance:.2f} (+${original_trade_cost:.2f})")
        
        # Add the profit or loss
        current_user.current_balance += profit_loss
        new_balance = current_user.current_balance
        
        # 🔧 DEBUG: Log new balance
        logging.info(f"💰 FINAL BALANCE: ${new_balance:.2f} (Original Cost: +${original_trade_cost:.2f}, P/L: {'+' if profit_loss >= 0 else ''}${profit_loss:.2f})")
        
        # Force explicit commit with error handling
        db.session.commit()
        
        # 🔧 VERIFY: Check if balance was actually saved
        db.session.refresh(current_user)
        actual_balance = current_user.current_balance
        logging.info(f"💰 VERIFIED BALANCE AFTER COMMIT: ${actual_balance:.2f}")
        
        # Calculate total change for user message
        total_change = original_trade_cost + profit_loss
        
        if profit_loss >= 0:
            flash(f'Trade closed successfully! Refunded: ${original_trade_cost:.2f} + Profit: ${profit_loss:.2f} = +${total_change:.2f}. New balance: ${actual_balance:.2f}', 'success')
        else:
            flash(f'Trade closed. Refunded: ${original_trade_cost:.2f} + Loss: ${profit_loss:.2f} = +${total_change:.2f}. New balance: ${actual_balance:.2f}', 'warning')
            
    except Exception as e:
        db.session.rollback()
        logging.error(f"❌ Error closing trade: {str(e)}")
        flash(f'Error closing trade: {str(e)}', 'error')
    
    return redirect(url_for('webtrader.webtrader_dashboard'))

@webtrader.route("/execute_trade", methods=['POST'])
@login_required
def execute_trade():
    """Execute a trade order - using database prices only"""
    if not current_user.is_client:
        flash('Access denied. This area is for clients only.', 'danger')
        return redirect(url_for('main.home'))

    # Check if the user is allowed to trade
    if hasattr(current_user, 'available_to_trade') and not current_user.available_to_trade:
        flash('Your account is currently not allowed to open new trades. Please contact support.', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))
        
    instrument_id = request.form.get('instrument_id')
    amount = float(request.form.get('amount', 0))
    trade_type = request.form.get('trade_type')
    order_type = request.form.get('order_type', 'market')
    target_price = request.form.get('target_price')

    # Validate inputs
    if amount <= 0:
        flash('Amount must be greater than zero.', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))
        
    instrument = TradingInstrument.query.get(instrument_id)
    if not instrument:
        flash('Invalid instrument selected.', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))

    # 🚀 PERFORMANCE: Get current price from database only (no API calls)
    current_price = instrument.current_price
    if not current_price or current_price <= 0:
        flash('Price not available. Please try again in a moment.', 'danger')
        return redirect(url_for('webtrader.webtrader_dashboard'))

    if order_type == 'market':
        success = execute_market_order(current_user, instrument, amount, current_price, trade_type)
        if success:
            flash(f'{trade_type.capitalize()} order executed successfully!', 'success')
        else:
            flash('Failed to execute order.', 'danger')
    elif order_type in ['limit', 'stop_loss', 'take_profit']:
        if not target_price or float(target_price) <= 0:
            flash('Target price is required for limit, stop-loss, and take-profit orders.', 'danger')
            return redirect(url_for('webtrader.webtrader_dashboard'))
            
        success = store_order(current_user, instrument, amount, order_type, float(target_price), trade_type)
        if success:
            flash(f'{order_type.replace("_", " ").title()} order placed successfully!', 'success')
        else:
            flash('Failed to place order.', 'danger')
    else:
        flash('Invalid order type.', 'danger')
        
    return redirect(url_for('webtrader.webtrader_dashboard'))

@webtrader.route("/liquidate_account", methods=['POST'])
@login_required
def liquidate_account():
    """Liquidate all open trades for the current user"""
    if not current_user.is_client:
        flash('Access denied. This area is for clients only.', 'danger')
        return redirect(url_for('main.home'))

    try:
        # Get all open trades for the user
        open_trades = Trade.query.filter_by(lead_id=current_user.id, status='open').all()
        
        if not open_trades:
            flash('No open trades to liquidate.', 'info')
            return redirect(url_for('webtrader.webtrader_dashboard'))
        
        liquidated_count = 0
        total_pnl = 0.0
        total_refund = 0.0
        
        for trade in open_trades:
            try:
                # 🚀 PERFORMANCE: Get current price from database only (no API calls)
                current_price = trade.instrument.current_price
                
                if current_price and current_price > 0:
                    # Calculate profit/loss
                    if trade.trade_type == 'buy':
                        profit_loss = (current_price - trade.price) * trade.amount
                    else:
                        profit_loss = (trade.price - current_price) * trade.amount
                    
                    # 🔧 CRITICAL FIX: Calculate original trade cost to refund
                    original_trade_cost = trade.amount * trade.price
                    
                    # Close the trade
                    trade.status = 'closed'
                    trade.close_price = current_price
                    trade.profit_loss = profit_loss
                    trade.close_date = datetime.utcnow()
                    
                    total_pnl += profit_loss
                    total_refund += original_trade_cost
                    liquidated_count += 1
                    
                    logging.info(f"Liquidated trade {trade.id}: {trade.instrument.symbol} Original Cost: ${original_trade_cost:.2f}, P/L: ${profit_loss:.2f}")
                    
            except Exception as e:
                logging.error(f"Error liquidating trade {trade.id}: {str(e)}")
                continue
        
        # 🔧 CRITICAL FIX: Refund original trade costs AND add profit/loss
        current_user.current_balance += total_refund  # Refund all original trade costs
        current_user.current_balance += total_pnl     # Add all profit/loss
        
        total_change = total_refund + total_pnl
        
        db.session.commit()
        
        if total_pnl >= 0:
            flash(f'Account liquidated! {liquidated_count} trades closed. Refunded: ${total_refund:.2f} + Profit: ${total_pnl:.2f} = +${total_change:.2f}', 'success')
        else:
            flash(f'Account liquidated! {liquidated_count} trades closed. Refunded: ${total_refund:.2f} + Loss: ${total_pnl:.2f} = +${total_change:.2f}', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error during liquidation: {str(e)}', 'error')
        logging.error(f"Account liquidation error: {str(e)}")
    
    return redirect(url_for('webtrader.webtrader_dashboard'))

@webtrader.route("/test_twelve_data_api")
@login_required
def test_twelve_data_api():
    """Test endpoint to verify Twelve Data API is working"""
    test_results = []
    
    # Test symbols from different asset classes
    test_symbols = [
        ('AAPL', 'stock'),
        ('EUR/USD', 'forex'),
        ('BTC/USD', 'crypto'),
        ('XAU/USD', 'commodity')
    ]
    
    for symbol, asset_type in test_symbols:
        try:
            price = get_twelve_data_price(symbol, asset_type)
            if price:
                test_results.append({
                    'symbol': symbol,
                    'type': asset_type,
                    'price': price,
                    'status': 'SUCCESS',
                    'formatted_price': f"${price:,.6f}" if asset_type == 'crypto' else f"${price:,.2f}"
                })
            else:
                test_results.append({
                    'symbol': symbol,
                    'type': asset_type,
                    'price': None,
                    'status': 'FAILED',
                    'formatted_price': 'N/A'
                })
        except Exception as e:
            test_results.append({
                'symbol': symbol,
                'type': asset_type,
                'price': None,
                'status': 'ERROR',
                'formatted_price': str(e)
            })
    
    return jsonify({
        'api_key': '902d8585e8c040f591a3293d1b79ab88',
        'test_results': test_results,
        'total_tests': len(test_symbols),
        'successful': len([r for r in test_results if r['status'] == 'SUCCESS'])
    })

@webtrader.route("/market_status")
@login_required
def market_status():
    """Check if stock markets are open - for overlay display"""
    from datetime import datetime, time
    import pytz
    
    # Market definitions
    markets = {
        'US': {
            'timezone': 'US/Eastern',
            'open_time': time(9, 30),
            'close_time': time(16, 0),
            'weekdays_only': True
        },
        'London': {
            'timezone': 'Europe/London', 
            'open_time': time(8, 0),
            'close_time': time(16, 30),
            'weekdays_only': True
        },
        'Frankfurt': {
            'timezone': 'Europe/Berlin',
            'open_time': time(8, 0), 
            'close_time': time(22, 0),
            'weekdays_only': True
        },
        'Tokyo': {
            'timezone': 'Asia/Tokyo',
            'open_time': time(9, 0),
            'close_time': time(15, 0),  # 3:00 PM (simplified - ignoring lunch break)
            'weekdays_only': True
        },
        'Hong_Kong': {
            'timezone': 'Asia/Hong_Kong',
            'open_time': time(9, 30),
            'close_time': time(16, 0),  # 4:00 PM (simplified - ignoring lunch break)
            'weekdays_only': True
        },
        'Australia': {
            'timezone': 'Australia/Sydney',
            'open_time': time(10, 0),
            'close_time': time(16, 0),
            'weekdays_only': True
        }
    }
    
    market_status = {}
    
    for market_name, market_info in markets.items():
        try:
            tz = pytz.timezone(market_info['timezone'])
            market_time = datetime.now(tz)
            
            # Check if it's a weekday (Monday=0, Sunday=6)
            is_weekday = market_time.weekday() < 5
            
            # Check if current time is within market hours
            current_time = market_time.time()
            is_open = (current_time >= market_info['open_time'] and 
                      current_time <= market_info['close_time'])
            
            # Market is open if it's a weekday and within hours
            market_open = is_weekday and is_open if market_info['weekdays_only'] else is_open
            
            market_status[market_name] = {
                'open': market_open,
                'local_time': market_time.strftime('%H:%M %Z'),
                'next_open': 'Monday 09:30' if not is_weekday else 'Today' if not is_open else 'Now'
            }
            
        except Exception as e:
            # Fallback - assume market is closed if timezone fails
            market_status[market_name] = {
                'open': False,
                'local_time': 'Unknown',
                'next_open': 'Unknown'
            }
    
    # Determine overall stock market status (any major market open = trading allowed)
    major_markets = ['US', 'London', 'Tokyo', 'Frankfurt']
    any_major_open = any(market_status.get(market, {}).get('open', False) for market in major_markets)
    
    return jsonify({
        'stocks_trading_allowed': any_major_open,
        'markets': market_status,
        'message': 'Stock trading is available' if any_major_open else 'Stock markets are currently closed'
    })
