from omcrm import db, create_app
from flask_migrate import Migrate
import sqlite3

app = create_app()
migrate = Migrate(app, db)

def add_notes_column():
    # Connect to the SQLite database
    with app.app_context():
        try:
            conn = sqlite3.connect('instance/site.db')
            cursor = conn.cursor()
            
            # Check if the column already exists
            cursor.execute("PRAGMA table_info(trade)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'notes' not in columns:
                print("Adding 'notes' column to trade table...")
                cursor.execute("ALTER TABLE trade ADD COLUMN notes TEXT")
                conn.commit()
                print("Column 'notes' added successfully!")
            else:
                print("Column 'notes' already exists in trade table")
            
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding column: {str(e)}")
            return False

if __name__ == "__main__":
    add_notes_column() 