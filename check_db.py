import sqlite3
import os
from flask import Flask
from flask_migrate import Migrate

def check_db_structure():
    """Check the structure of the dev.db database"""
    print("Checking database structure...")
    
    # Connect to the database
    conn = sqlite3.connect('dev.db')
    cursor = conn.cursor()
    
    # Check if alembic_version table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
    if not cursor.fetchone():
        print("No alembic_version table found. Creating it...")
        cursor.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        conn.commit()
    
    # Check what version is in the alembic_version table
    cursor.execute("SELECT version_num FROM alembic_version")
    current_version = cursor.fetchone()
    print(f"Current migration version: {current_version[0] if current_version else 'None'}")
    
    # Set the version to the head revision (from the migration history output)
    if current_version and current_version[0] != 'de1f187d2bb7':
        print(f"Updating version from {current_version[0]} to de1f187d2bb7...")
        cursor.execute("UPDATE alembic_version SET version_num = 'de1f187d2bb7'")
        conn.commit()
    elif not current_version:
        print("Setting version to de1f187d2bb7...")
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('de1f187d2bb7')")
        conn.commit()
    
    # Check our current lead_source table structure
    cursor.execute("PRAGMA table_info(lead_source)")
    columns = cursor.fetchall()
    print("Lead Source Table Columns:")
    for col in columns:
        print(f"{col[0]}: {col[1]} ({col[2]})")
    
    # Check if the columns already exist
    column_names = [col[1] for col in columns]
    if 'affiliate_id' in column_names:
        print("affiliate_id column already exists")
    else:
        print("Adding affiliate_id column...")
        cursor.execute("ALTER TABLE lead_source ADD COLUMN affiliate_id VARCHAR(40)")
        
    if 'api_key' in column_names:
        print("api_key column already exists")
    else:
        print("Adding api_key column...")
        cursor.execute("ALTER TABLE lead_source ADD COLUMN api_key VARCHAR(64)")
        
    if 'is_api_enabled' in column_names:
        print("is_api_enabled column already exists")
    else:
        print("Adding is_api_enabled column...")
        cursor.execute("ALTER TABLE lead_source ADD COLUMN is_api_enabled BOOLEAN NOT NULL DEFAULT 0")
    
    conn.commit()
    print("Database structure check and update complete.")
    conn.close()

if __name__ == "__main__":
    check_db_structure() 