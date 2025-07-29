#!/usr/bin/env python
"""
PostgreSQL migration to add client tracking fields
Run this script to add last_login_at, last_seen_at, and login_count fields to PostgreSQL
"""
import psycopg2
import os
from datetime import datetime

def add_client_tracking_fields_postgres():
    """Add client tracking fields to Lead table in PostgreSQL"""
    
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
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL successfully!")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='lead' AND table_schema='public'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Current columns in lead table: {len(existing_columns)} columns")
        
        # Define columns to add
        columns_to_add = [
            ('last_login_at', 'TIMESTAMP'),
            ('last_seen_at', 'TIMESTAMP'), 
            ('login_count', 'INTEGER DEFAULT 0')
        ]
        
        # Add missing columns
        for column_name, column_type in columns_to_add:
            if column_name not in existing_columns:
                try:
                    sql = f'ALTER TABLE lead ADD COLUMN {column_name} {column_type}'
                    cursor.execute(sql)
                    print(f"✅ Added column: {column_name} ({column_type})")
                except psycopg2.Error as e:
                    print(f"⚠️  Error adding column {column_name}: {e}")
            else:
                print(f"ℹ️  Column {column_name} already exists")
        
        # Commit changes
        conn.commit()
        print("✅ Client tracking fields migration completed successfully!")
        
        # Verify columns were added
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='lead' AND table_schema='public'
            ORDER BY ordinal_position
        """)
        all_columns = cursor.fetchall()
        print(f"📊 Updated lead table has {len(all_columns)} columns")
        
        # Show the new columns specifically
        new_columns = [col for col in all_columns if col[0] in ['last_login_at', 'last_seen_at', 'login_count']]
        if new_columns:
            print("🆕 New tracking columns:")
            for col_name, col_type in new_columns:
                print(f"   - {col_name}: {col_type}")
        
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
    print("🚀 Starting PostgreSQL client tracking fields migration...")
    success = add_client_tracking_fields_postgres()
    if success:
        print("🎉 Migration completed successfully!")
        print("")
        print("📋 Next steps:")
        print("1. Restart your Flask application: docker-compose restart")
        print("2. Clients will start tracking online activity")
        print("3. Check the clients list to see online status")
    else:
        print("💥 Migration failed. Please check the errors above.") 