"""
Direct migration script to add credit_balance to the Lead model
"""
import sqlite3
import os

def find_db_file():
    # Common locations for the SQLite database in Flask projects
    possible_paths = [
        'instance/site.db',
        'omcrm/site.db',
        'site.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def main():
    db_path = find_db_file()
    
    if not db_path:
        print("ERROR: Database file not found. Please specify the path manually.")
        return
    
    print(f"Found database at: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(lead)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'credit_balance' not in column_names:
            print("Adding credit_balance column to lead table...")
            cursor.execute("ALTER TABLE lead ADD COLUMN credit_balance FLOAT NOT NULL DEFAULT 0.0")
            
            # Set default values
            cursor.execute("UPDATE lead SET credit_balance = 0.0 WHERE credit_balance IS NULL")
            
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("The credit_balance column already exists. No changes needed.")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    main() 
