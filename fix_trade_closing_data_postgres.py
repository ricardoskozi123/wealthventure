#!/usr/bin/env python3
"""
PostgreSQL Database Migration: Fix Trade Closing Data
Fix any trades that have status='closed' but missing closing_date or closing_price
"""
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta

def fix_trade_closing_data_postgres():
    """Fix trade closing data in PostgreSQL"""
    
    # PostgreSQL connection parameters
    db_config = {
        'host': 'db',  # Docker service name
        'database': 'omcrm_trading',
        'user': 'omcrm_user',
        'password': 'omcrm_password_2024',
        'port': 5432
    }
    
    print(f"🐘 Connecting to PostgreSQL database: {db_config['database']}")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        print("✅ Connected to PostgreSQL successfully!")
        
        # Find closed trades missing closing data
        cursor.execute("""
            SELECT id, instrument_id, trade_type, price, amount, profit_loss, 
                   date, opening_date, closing_date, closing_price, status
            FROM trade 
            WHERE status = 'closed' 
            AND (closing_date IS NULL OR closing_price IS NULL)
            ORDER BY id
        """)
        trades_to_fix = cursor.fetchall()
        
        print(f"Found {len(trades_to_fix)} closed trades with missing closing data:")
        
        for trade in trades_to_fix:
            print(f"  Trade ID {trade['id']}: closing_date={trade['closing_date']}, closing_price={trade['closing_price']}")
            
            update_fields = []
            update_values = []
            
            # Fix missing closing_date
            if trade['closing_date'] is None:
                opening_date = trade['opening_date'] or trade['date']
                if opening_date:
                    estimated_closing_date = opening_date + timedelta(hours=1)
                else:
                    estimated_closing_date = datetime.utcnow()
                
                update_fields.append("closing_date = %s")
                update_values.append(estimated_closing_date)
                print(f"    ✅ Will set closing_date to {estimated_closing_date}")
            
            # Fix missing closing_price
            if trade['closing_price'] is None:
                if trade['profit_loss'] is not None and trade['amount'] and trade['amount'] > 0:
                    # Reverse-calculate closing price from profit/loss
                    if trade['trade_type'] == 'buy':
                        # profit_loss = (closing_price - entry_price) * amount
                        estimated_closing_price = trade['price'] + (trade['profit_loss'] / trade['amount'])
                    else:  # sell
                        # profit_loss = (entry_price - closing_price) * amount
                        estimated_closing_price = trade['price'] - (trade['profit_loss'] / trade['amount'])
                    
                    update_fields.append("closing_price = %s")
                    update_values.append(estimated_closing_price)
                    print(f"    ✅ Will set closing_price to ${estimated_closing_price:.4f} (calculated from P/L)")
                else:
                    # Use entry price as fallback
                    update_fields.append("closing_price = %s")
                    update_values.append(trade['price'])
                    print(f"    ✅ Will set closing_price to ${trade['price']:.4f} (entry price fallback)")
            
            # Execute update
            if update_fields:
                update_sql = f"UPDATE trade SET {', '.join(update_fields)} WHERE id = %s"
                update_values.append(trade['id'])
                cursor.execute(update_sql, update_values)
        
        if trades_to_fix:
            conn.commit()
            print(f"\n✅ Fixed {len(trades_to_fix)} trades with missing closing data!")
        else:
            print("✅ All closed trades already have proper closing data!")
        
        # Show a summary of all closed trades
        cursor.execute("""
            SELECT t.id, i.symbol, t.trade_type, t.price, t.closing_price, 
                   t.date, t.opening_date, t.closing_date, t.profit_loss
            FROM trade t
            LEFT JOIN trading_instrument i ON t.instrument_id = i.id
            WHERE t.status = 'closed'
            ORDER BY t.id
            LIMIT 10
        """)
        all_closed_trades = cursor.fetchall()
        
        print(f"\n📊 Summary: Found {len(all_closed_trades)} closed trades (showing first 10)")
        
        for trade in all_closed_trades:
            symbol = trade['symbol'] or 'Unknown'
            opening_date = trade['opening_date'] or trade['date']
            print(f"  Trade ID {trade['id']}: {symbol} {trade['trade_type'].upper()}")
            print(f"    Entry: ${trade['price']:.4f} on {opening_date}")
            print(f"    Exit: ${trade['closing_price']:.4f} on {trade['closing_date']}")
            print(f"    P/L: ${trade['profit_loss']:.2f}")
            print()
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    print("🚀 Starting PostgreSQL trade closing data fix...")
    success = fix_trade_closing_data_postgres()
    if success:
        print("🎉 Trade closing data fix completed successfully!")
        print("")
        print("📋 Next steps:")
        print("1. Restart your Flask application: docker-compose restart")
        print("2. Check the edit trade page - closing dates should now be visible")
        print("3. Verify the Trading Analytics charts are working")
    else:
        print("💥 Fix failed. Please check the errors above.") 