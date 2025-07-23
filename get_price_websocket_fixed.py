@webtrader.route("/get_price/")
@login_required
def get_price():
    """Get current price for an instrument, prioritizing WebSocket data over HTTP APIs."""
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

    logging.debug(f"Cache expired or no recent price for {instrument.symbol}. Checking WebSocket first.")
    
    # FIRST: Try to get price from WebSocket real-time manager (Binance WebSocket is unlimited)
    new_price = None
    try:
        from omcrm.webtrader.realtime_data import real_time_manager
        cached_data = real_time_manager.get_cached_price(instrument.symbol)
        if cached_data:
            new_price = cached_data.get('price')
            logging.info(f"💰 Using WebSocket price for {instrument.symbol}: ${new_price} (unlimited Binance)")
        else:
            logging.warning(f"⚠️  No WebSocket data for {instrument.symbol}, falling back to HTTP API")
    except Exception as e:
        logging.error(f"Error accessing WebSocket data: {e}")
    
    # FALLBACK: Only use HTTP API if WebSocket data not available
    if new_price is None:
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