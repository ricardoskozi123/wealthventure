#!/usr/bin/env python3
"""
Check what trading instruments are in your SQLite database
"""

import sqlite3
import os

def check_database():
    """Check the SQLite database for trading instruments"""
    
    print("🔍 Checking SQLite Database for Trading Instruments...")
    
    # Common SQLite database locations - prioritize dev.db
    possible_db_paths = [
        'dev.db',           # User requested this one
        'instance/dev.db',
        'instance/database.db',
        'instance/db.sqlite',
        'app.db',
        'database.db',
        'db.sqlite',
        'omcrm.db'
    ]
    
    db_path = None
    for path in possible_db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ SQLite database not found!")
        print("🔍 Looking for database files...")
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.db') or file.endswith('.sqlite'):
                    full_path = os.path.join(root, file)
                    print(f"   Found: {full_path}")
        print("\n💡 Please specify the correct database path manually.")
        return
    
    print(f"📁 Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if trading_instrument table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='trading_instrument';
        """)
        
        if not cursor.fetchone():
            print("❌ No 'trading_instrument' table found!")
            print("🔍 Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table in tables:
                print(f"   - {table[0]}")
            
            # Check for alternative table names
            print("\n🔍 Checking for alternative table names...")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%instrument%';")
            alt_tables = cursor.fetchall()
            if alt_tables:
                print("📋 Found instrument-related tables:")
                for table in alt_tables:
                    print(f"   - {table[0]}")
            
            return
        
        print("✅ Found 'trading_instrument' table")
        
        # Get all instruments
        cursor.execute("SELECT id, symbol, name, type, current_price FROM trading_instrument")
        instruments = cursor.fetchall()
        
        print(f"\n📊 Found {len(instruments)} trading instruments:")
        
        if not instruments:
            print("❌ No instruments in database!")
            print("💡 You need to add some crypto instruments with type='crypto'")
            return
        
        crypto_count = 0
        stock_count = 0
        other_count = 0
        
        print("\nAll Instruments:")
        for instrument in instruments:
            id_val, symbol, name, type_val, price = instrument
            price_str = f"${price:.2f}" if price else "No price"
            print(f"   ID: {id_val}, Symbol: {symbol}, Name: {name}, Type: {type_val}, Price: {price_str}")
            
            if type_val == 'crypto':
                crypto_count += 1
            elif type_val == 'stock':
                stock_count += 1
            else:
                other_count += 1
        
        print(f"\n📈 Summary:")
        print(f"   🪙 Crypto instruments: {crypto_count}")
        print(f"   📊 Stock instruments: {stock_count}")
        print(f"   🔧 Other instruments: {other_count}")
        
        if crypto_count == 0:
            print(f"\n❌ PROBLEM FOUND: No crypto instruments with type='crypto'!")
            print(f"💡 This is why your WebSocket isn't starting automatically.")
            print(f"🔧 Solutions:")
            print(f"   1. Add crypto instruments via your Flask admin interface")
            print(f"   2. Or run this SQL to add some test crypto instruments:")
            print(f"""
   INSERT INTO trading_instrument (symbol, name, type, current_price) VALUES
   ('BTC/USD', 'Bitcoin', 'crypto', 109748.95),
   ('ETH/USD', 'Ethereum', 'crypto', 2581.30),
   ('SOL/USD', 'Solana', 'crypto', 180.70),
   ('BNB/USD', 'Binance Coin', 'crypto', 673.16),
   ('ADA/USD', 'Cardano', 'crypto', 0.7858);
            """)
        else:
            print(f"\n✅ You have {crypto_count} crypto instruments!")
            print(f"🔍 The issue might be with the auto-start code in your Flask app.")
            print(f"\n📋 Crypto instruments found:")
            for instrument in instruments:
                id_val, symbol, name, type_val, price = instrument
                if type_val == 'crypto':
                    print(f"   - {symbol} ({name}) - ID: {id_val}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_database() 