#!/usr/bin/env python3
"""
Database Migration: Fix Trade Closing Data
Fix any trades that have status='closed' but missing closing_date or closing_price
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omcrm import create_app, db
from omcrm.webtrader.models import Trade
from datetime import datetime, timedelta

def fix_trade_closing_data():
    app = create_app()
    with app.app_context():
        try:
            # Find closed trades missing closing data
            closed_trades_missing_data = Trade.query.filter(
                Trade.status == 'closed',
                (Trade.closing_date.is_(None)) | (Trade.closing_price.is_(None))
            ).all()
            
            print(f"Found {len(closed_trades_missing_data)} closed trades with missing closing data:")
            
            for trade in closed_trades_missing_data:
                print(f"  Trade ID {trade.id}: closing_date={trade.closing_date}, closing_price={trade.closing_price}")
                
                # For missing closing_date, estimate it as opening_date + 1 hour (or use current time if very old)
                if trade.closing_date is None:
                    estimated_closing_date = trade.opening_date + timedelta(hours=1) if trade.opening_date else trade.date + timedelta(hours=1)
                    trade.closing_date = estimated_closing_date
                    print(f"    ✅ Set closing_date to {estimated_closing_date}")
                
                # For missing closing_price, use current instrument price or estimate based on profit_loss
                if trade.closing_price is None:
                    if trade.profit_loss is not None and trade.amount > 0:
                        # Reverse-calculate closing price from profit/loss
                        if trade.trade_type == 'buy':
                            # profit_loss = (closing_price - entry_price) * amount
                            estimated_closing_price = trade.price + (trade.profit_loss / trade.amount)
                        else:  # sell
                            # profit_loss = (entry_price - closing_price) * amount
                            estimated_closing_price = trade.price - (trade.profit_loss / trade.amount)
                        
                        trade.closing_price = estimated_closing_price
                        print(f"    ✅ Set closing_price to ${estimated_closing_price:.4f} (calculated from P/L)")
                    else:
                        # Use current instrument price as fallback
                        trade.closing_price = trade.instrument.current_price if trade.instrument else trade.price
                        print(f"    ✅ Set closing_price to ${trade.closing_price:.4f} (current/entry price)")
            
            if closed_trades_missing_data:
                db.session.commit()
                print(f"\n✅ Fixed {len(closed_trades_missing_data)} trades with missing closing data!")
            else:
                print("✅ All closed trades already have proper closing data!")
                
            # Show a summary of all closed trades
            all_closed_trades = Trade.query.filter_by(status='closed').all()
            print(f"\n📊 Summary: {len(all_closed_trades)} total closed trades")
            
            for trade in all_closed_trades[:5]:  # Show first 5 as examples
                holding_period = trade.get_holding_period()
                print(f"  Trade ID {trade.id}: {trade.instrument.symbol} {trade.trade_type.upper()}")
                print(f"    Entry: ${trade.price:.4f} on {trade.opening_date or trade.date}")
                print(f"    Exit: ${trade.closing_price:.4f} on {trade.closing_date}")
                print(f"    P/L: ${trade.profit_loss:.2f}, Holding: {holding_period}")
                print()
                
        except Exception as e:
            print(f"❌ Error fixing trade closing data: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    fix_trade_closing_data() 