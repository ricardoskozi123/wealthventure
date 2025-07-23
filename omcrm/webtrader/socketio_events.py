"""
Socket.IO event handlers for real-time WebTrader functionality
"""

from flask_socketio import emit, join_room, leave_room, disconnect
from flask_login import current_user
from omcrm import socketio
from omcrm.webtrader.realtime_data import real_time_manager
from omcrm.webtrader.models import TradingInstrument
import logging

logger = logging.getLogger(__name__)

@socketio.on('connect', namespace='/webtrader')
def on_connect():
    """Handle client connection to WebTrader namespace"""
    if not current_user.is_authenticated:
        disconnect()
        return False
    
    # Join a room based on user ID for personalized updates
    join_room(f"user_{current_user.id}")
    
    # Join the general trading room for price updates
    join_room("trading_room")
    
    logger.info(f"User {current_user.id} connected to WebTrader")
    
    # Send current connection status
    connection_status = real_time_manager.get_connection_status()
    emit('connection_status', connection_status)

@socketio.on('disconnect', namespace='/webtrader')
def on_disconnect():
    """Handle client disconnection"""
    if current_user.is_authenticated:
        leave_room(f"user_{current_user.id}")
        leave_room("trading_room")
        logger.info(f"User {current_user.id} disconnected from WebTrader")

@socketio.on('subscribe_to_instruments', namespace='/webtrader')
def on_subscribe_to_instruments(data):
    """Handle subscription to specific trading instruments"""
    if not current_user.is_authenticated:
        return
    
    instrument_ids = data.get('instrument_ids', [])
    
    try:
        # Get instrument details
        instruments = []
        for instrument_id in instrument_ids:
            instrument = TradingInstrument.query.get(instrument_id)
            if instrument:
                instruments.append({
                    'id': instrument.id,
                    'symbol': instrument.symbol,
                    'name': instrument.name,
                    'type': instrument.type
                })
        
        if instruments:
            # Start real-time feeds if not already running
            if not real_time_manager.is_running:
                real_time_manager.start_real_time_feeds(instruments)
                logger.info(f"Started real-time feeds for user {current_user.id}")
            
            # Send current cached prices
            for instrument in instruments:
                cached_price = real_time_manager.get_cached_price(instrument['symbol'])
                if cached_price:
                    emit('price_update', cached_price)
            
            emit('subscription_success', {
                'message': f'Subscribed to {len(instruments)} instruments',
                'instruments': instruments
            })
        else:
            emit('subscription_error', {'message': 'No valid instruments found'})
            
    except Exception as e:
        logger.error(f"Error subscribing to instruments: {e}")
        emit('subscription_error', {'message': 'Failed to subscribe to instruments'})

@socketio.on('unsubscribe_from_instruments', namespace='/webtrader')
def on_unsubscribe_from_instruments(data):
    """Handle unsubscription from trading instruments"""
    if not current_user.is_authenticated:
        return
    
    # For now, we'll keep the feeds running as other users might be subscribed
    # In a production environment, you'd want to track subscriptions per user
    emit('unsubscription_success', {'message': 'Unsubscribed from instruments'})

@socketio.on('get_price_history', namespace='/webtrader')
def on_get_price_history(data):
    """Handle request for price history data"""
    if not current_user.is_authenticated:
        return
    
    symbol = data.get('symbol')
    timeframe = data.get('timeframe', '1h')  # 1m, 5m, 15m, 1h, 4h, 1d
    limit = data.get('limit', 100)
    
    try:
        # For demo purposes, generate sample historical data
        # In production, you'd fetch this from your database or API
        import time
        import random
        
        current_time = int(time.time())
        interval_seconds = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }.get(timeframe, 3600)
        
        # Generate sample OHLCV data
        history = []
        base_price = random.uniform(50, 200)
        
        for i in range(limit):
            timestamp = current_time - (i * interval_seconds)
            
            # Generate realistic price movements
            open_price = base_price + random.uniform(-5, 5)
            close_price = open_price + random.uniform(-2, 2)
            high_price = max(open_price, close_price) + random.uniform(0, 1)
            low_price = min(open_price, close_price) - random.uniform(0, 1)
            volume = random.uniform(1000, 10000)
            
            history.append({
                'timestamp': timestamp,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': round(volume, 2)
            })
            
            base_price = close_price  # Use close as next base
        
        # Reverse to get chronological order
        history.reverse()
        
        emit('price_history', {
            'symbol': symbol,
            'timeframe': timeframe,
            'data': history
        })
        
    except Exception as e:
        logger.error(f"Error getting price history for {symbol}: {e}")
        emit('price_history_error', {'message': 'Failed to get price history'})

@socketio.on('ping', namespace='/webtrader')
def on_ping():
    """Handle ping from client for connection testing"""
    if current_user.is_authenticated:
        emit('pong', {'timestamp': int(time.time())})

@socketio.on('get_market_status', namespace='/webtrader')
def on_get_market_status():
    """Handle request for market status"""
    if not current_user.is_authenticated:
        return
    
    try:
        import datetime
        
        # Simple market hours check (NYSE hours as example)
        now = datetime.datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        is_market_hours = (market_open <= now <= market_close and 
                          now.weekday() < 5)  # Monday=0, Sunday=6
        
        # Get connection status
        connection_status = real_time_manager.get_connection_status()
        active_connections = sum(1 for api in connection_status.values() if api['active'])
        
        emit('market_status', {
            'is_market_hours': is_market_hours,
            'market_open': market_open.isoformat(),
            'market_close': market_close.isoformat(),
            'active_data_feeds': active_connections,
            'total_data_feeds': len(connection_status),
            'connection_status': connection_status
        })
        
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        emit('market_status_error', {'message': 'Failed to get market status'})

# Additional utility functions
def emit_to_user(user_id, event, data):
    """Emit an event to a specific user"""
    socketio.emit(event, data, room=f"user_{user_id}", namespace='/webtrader')

def emit_to_all_traders(event, data):
    """Emit an event to all connected traders"""
    socketio.emit(event, data, room="trading_room", namespace='/webtrader')

def emit_trade_update(user_id, trade_data):
    """Emit a trade update to a specific user"""
    emit_to_user(user_id, 'trade_update', trade_data)

def emit_balance_update(user_id, balance_data):
    """Emit a balance update to a specific user"""
    emit_to_user(user_id, 'balance_update', balance_data) 