from omcrm import db, create_app
from omcrm.webtrader.models import TradingInstrument

def test_price_update():
    app = create_app()
    with app.app_context():
        # Get the first instrument
        instrument = TradingInstrument.query.first()
        if not instrument:
            print("No instruments found in database")
            return
            
        print(f'Before update: price={instrument.current_price}, previous={instrument.previous_price}, change={instrument.change}')
        
        # Update price
        old_price = instrument.current_price or 0
        new_price = old_price * 1.05  # 5% increase
        instrument.update_price(new_price)
        db.session.commit()
        
        print(f'After update: price={instrument.current_price}, previous={instrument.previous_price}, change={instrument.change}')
        
        # Verify the change percentage is correct
        if instrument.previous_price:
            expected_change = ((new_price - instrument.previous_price) / instrument.previous_price) * 100
            print(f'Expected change: {round(expected_change, 2)}%, Actual: {instrument.change}%')
            
if __name__ == '__main__':
    test_price_update() 
