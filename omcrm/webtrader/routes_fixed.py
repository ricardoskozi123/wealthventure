from datetime import datetime
import requests
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify as flask_jsonify, session, g, current_app
from flask_login import login_required, current_user
from omcrm import db
from omcrm.leads.models import Lead, Trade
from omcrm.webtrader.forms import TradeForm, InstrumentForm
from omcrm.webtrader.models import TradingInstrument
from omcrm.webtrader.realtime_data import real_time_manager
import logging
import random
import time  # Add time import for delays
from functools import wraps

# Ensure we don't override the Flask jsonify function
jsonify = flask_jsonify

logging.basicConfig(level=logging.DEBUG)

webtrader = Blueprint('webtrader', __name__)

# Global cache for instrument prices
PRICE_CACHE = {}
CACHE_LAST_UPDATED = {}
CACHE_DURATION = 30  # Increased cache duration to 30 seconds to reduce API calls

# Rate limiting for API calls
API_CALL_TRACKER = {}
API_RATE_LIMIT = 1  # Maximum 1 API call per minute per instrument
API_RATE_WINDOW = 60  # 60 seconds

def get_cached_price(instrument_id):
    """Get a price from cache or fetch a new one if expired"""
    current_time = time.time()
    
    # First try to get from real-time manager cache (this should be the primary source)
    instrument = TradingInstrument.query.get(instrument_id)
    if instrument:
        cached_data = real_time_manager.get_cached_price(instrument.symbol)
        if cached_data:
            current_app.logger.debug(f"Using real-time manager cache for {instrument.symbol}")
            return cached_data.get('price')
    
    # Check if we're within rate limits for API calls
    symbol_key = f"{instrument.symbol}_{instrument.type}" if instrument else str(instrument_id)
    
    # Clean old API call records
    if symbol_key in API_CALL_TRACKER:
        API_CALL_TRACKER[symbol_key] = [
            call_time for call_time in API_CALL_TRACKER[symbol_key] 
            if current_time - call_time < API_RATE_WINDOW
        ]
    
    # Check if we've exceeded rate limit
    call_count = len(API_CALL_TRACKER.get(symbol_key, []))
    if call_count >= API_RATE_LIMIT:
        current_app.logger.warning(f"Rate limit exceeded for {symbol_key}. Using cached price.")
        # Return cached price or database price
        if instrument_id in PRICE_CACHE:
            return PRICE_CACHE[instrument_id]
        elif instrument and instrument.current_price:
            return instrument.current_price
        return None
    
    # If the price doesn't exist in cache or is expired
    if (instrument_id not in PRICE_CACHE or 
            instrument_id not in CACHE_LAST_UPDATED or 
            current_time - CACHE_LAST_UPDATED.get(instrument_id, 0) > CACHE_DURATION):
        
        # Get fresh price from the pricing source
        try:
            # Fetch the current price (using your existing price fetching logic)
            if not instrument:
                return None
            
            # Record this API call attempt
            if symbol_key not in API_CALL_TRACKER:
                API_CALL_TRACKER[symbol_key] = []
            API_CALL_TRACKER[symbol_key].append(current_time)
                
            # Add a small delay to prevent hitting APIs too quickly
            time.sleep(0.5)
                
            # Your existing price generation logic
            current_price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
            
            # Update the cache
            if current_price is not None:
                PRICE_CACHE[instrument_id] = current_price
                CACHE_LAST_UPDATED[instrument_id] = current_time
                current_app.logger.debug(f"API CALL: Fetched fresh price for {instrument.symbol}: {current_price}")
            else:
                current_app.logger.warning(f"Failed to get price for {instrument.symbol}, using cached/DB price")
                # Return cached price or database price as fallback
                if instrument_id in PRICE_CACHE:
                    return PRICE_CACHE[instrument_id]
                elif instrument.current_price:
                    return instrument.current_price
            
        except Exception as e:
            current_app.logger.error(f"Error fetching price for instrument {instrument_id}: {str(e)}")
            return PRICE_CACHE.get(instrument_id)  # Return last known price if available
    
    return PRICE_CACHE.get(instrument_id) 