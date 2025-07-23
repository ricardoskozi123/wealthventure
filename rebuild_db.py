import os
import shutil
from datetime import datetime
import sqlite3

# Define SQLite database path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'site.db')

def rebuild_database():
    print("Starting database rebuild...")
    
    # Create a backup of the existing database
    if os.path.exists(DB_PATH):
        backup_path = f"{DB_PATH}.backup-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            shutil.copy2(DB_PATH, backup_path)
            print(f"Created backup at {backup_path}")
        except Exception as e:
            print(f"Failed to create backup: {str(e)}")
            return
        
        # Remove the existing database
        try:
            os.remove(DB_PATH)
            print(f"Removed old database at {DB_PATH}")
        except Exception as e:
            print(f"Failed to remove old database: {str(e)}")
            return
    
    # Make sure instance directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Create new empty database file
    conn = sqlite3.connect(DB_PATH)
    conn.close()
    print(f"Created new empty database at {DB_PATH}")
    
    # Now initialize the database with Flask-SQLAlchemy
    from omcrm import create_app, db
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Created all tables")
        
        print("Database rebuild complete!")

if __name__ == "__main__":
    rebuild_database() 