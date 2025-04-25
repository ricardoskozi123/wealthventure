from omcrm import db, create_app
from omcrm.webtrader.models import TradingInstrument
from omcrm.webtrader.routes import get_real_time_price
from datetime import datetime

def fix_instrument_nulls():
    """Fix any NULL values in the TradingInstrument table to prevent errors"""
    app = create_app()
    with app.app_context():
        instruments = TradingInstrument.query.all()
        fixed_count = 0
        
        for instrument in instruments:
            needs_update = False
            
            # Check for NULL values and fix them
            if instrument.current_price is None:
                print(f"Fixing NULL current_price for {instrument.symbol}")
                # Get a real price if possible
                price = get_real_time_price(instrument.symbol, instrument.name, instrument.type)
                if price:
                    instrument.current_price = price
                else:
                    # Use a default price as last resort
                    instrument.current_price = 100.0
                needs_update = True
                
            if instrument.previous_price is None:
                print(f"Fixing NULL previous_price for {instrument.symbol}")
                instrument.previous_price = instrument.current_price
                needs_update = True
                
            if instrument.change is None:
                print(f"Fixing NULL change for {instrument.symbol}")
                instrument.change = 0.0
                needs_update = True
                
            if instrument.last_updated is None:
                print(f"Fixing NULL last_updated for {instrument.symbol}")
                instrument.last_updated = datetime.utcnow()
                needs_update = True
                
            if needs_update:
                db.session.add(instrument)
                fixed_count += 1
                
        if fixed_count > 0:
            print(f"Committing fixes for {fixed_count} instruments")
            db.session.commit()
        else:
            print("No NULL values found, all instruments are good!")

if __name__ == "__main__":
    fix_instrument_nulls() 
