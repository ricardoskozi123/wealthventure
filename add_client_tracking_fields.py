#!/usr/bin/env python
"""
Database migration to add client tracking fields
Run this script to add last_login_at, last_seen_at, and login_count fields
"""
import sqlite3
import os
from datetime import datetime

def add_client_tracking_fields():
    """Add client tracking fields to Lead table"""
    
    # Try to connect to the database
    db_paths = [
        'dev.db',
        'omcrm/dev.db',
        'instance/site.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database file not found. Tried:")
        for path in db_paths:
            print(f"   - {path}")
        return False
    
    print(f"📊 Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(lead)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"📋 Current columns in lead table: {len(columns)} columns")
        
        # Add missing columns
        columns_to_add = [
            ('last_login_at', 'DATETIME'),
            ('last_seen_at', 'DATETIME'), 
            ('login_count', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_type in columns_to_add:
            if column_name not in columns:
                try:
                    cursor.execute(f'ALTER TABLE lead ADD COLUMN {column_name} {column_type}')
                    print(f"✅ Added column: {column_name}")
                except sqlite3.Error as e:
                    print(f"⚠️  Column {column_name} might already exist: {e}")
            else:
                print(f"ℹ️  Column {column_name} already exists")
        
        # Commit changes
        conn.commit()
        print("✅ Client tracking fields migration completed successfully!")
        
        # Show updated table structure
        cursor.execute("PRAGMA table_info(lead)")
        columns = cursor.fetchall()
        print(f"📊 Updated lead table has {len(columns)} columns")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting client tracking fields migration...")
    success = add_client_tracking_fields()
    if success:
        print("🎉 Migration completed successfully!")
        print("")
        print("📋 Next steps:")
        print("1. Restart your Flask application")
        print("2. Clients will start tracking online activity")
        print("3. Check the clients list to see online status")
    else:
        print("💥 Migration failed. Please check the errors above.") 