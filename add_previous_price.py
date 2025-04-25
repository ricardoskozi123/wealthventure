from sqlalchemy import inspect
from omcrm import db, create_app

def add_previous_price_column():
    """Check if previous_price column exists in trading_instrument table, and add it if not"""
    app = create_app()
    with app.app_context():
        # Check if column exists
        insp = inspect(db.engine)
        columns = insp.get_columns('trading_instrument')
        has_previous_price = any(col['name'] == 'previous_price' for col in columns)
        
        print('previous_price column exists:', has_previous_price)
        
        # Add column if it doesn't exist
        if not has_previous_price:
            print('Adding previous_price column...')
            try:
                db.session.execute('ALTER TABLE trading_instrument ADD COLUMN previous_price FLOAT;')
                db.session.commit()
                print('previous_price column added successfully!')
            except Exception as e:
                print(f'Error adding column: {str(e)}')
                db.session.rollback()
        else:
            print('Column already exists, no changes needed.')
            
if __name__ == '__main__':
    add_previous_price_column() 
