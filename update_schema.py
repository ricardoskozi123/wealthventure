import sqlite3

def update_schema():
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect('dev.db')
        cursor = conn.cursor()
        
        # Check if team table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='team'")
        team_exists = cursor.fetchone() is not None
        
        if not team_exists:
            print("Creating team table...")
            cursor.execute("""
            CREATE TABLE team (
                id INTEGER NOT NULL, 
                name VARCHAR(50) NOT NULL,
                description VARCHAR(200),
                leader_id INTEGER,
                PRIMARY KEY (id),
                FOREIGN KEY(leader_id) REFERENCES user (id) ON DELETE SET NULL
            )
            """)
            print("Team table created.")
        
        # Check if user table has team_id column
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'team_id' not in column_names:
            print("Adding team_id column to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN team_id INTEGER REFERENCES team(id) ON DELETE SET NULL")
            print("Added team_id column to user table.")
        
        # Check if client_id column exists
        cursor.execute("PRAGMA table_info(deal)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'client_id' not in column_names:
            print("Adding client_id column to the deal table...")
            # Add client_id column to deal table
            cursor.execute("ALTER TABLE deal ADD COLUMN client_id INTEGER REFERENCES lead(id) ON DELETE CASCADE NOT NULL DEFAULT 1")
            print("Added client_id column")
        else:
            print("client_id column already exists")
        
        # Check if account_id or contact_id columns exist
        if 'account_id' in column_names or 'contact_id' in column_names:
            print("Removing old columns from the deal table...")
            # Create a new table without the account_id and contact_id columns
            cursor.execute("""
            CREATE TABLE deal_new (
                id INTEGER NOT NULL, 
                title VARCHAR(100), 
                expected_close_price FLOAT NOT NULL, 
                expected_close_date DATETIME, 
                deal_stage_id INTEGER NOT NULL, 
                client_id INTEGER NOT NULL,
                owner_id INTEGER, 
                notes VARCHAR(200), 
                date_created DATETIME NOT NULL, 
                PRIMARY KEY (id), 
                FOREIGN KEY(deal_stage_id) REFERENCES deal_stage (id) ON DELETE SET NULL, 
                FOREIGN KEY(client_id) REFERENCES lead (id) ON DELETE CASCADE, 
                FOREIGN KEY(owner_id) REFERENCES user (id) ON DELETE SET NULL
            )
            """)
            
            # Copy data from old table to new table
            cursor.execute("""
            INSERT INTO deal_new (id, title, expected_close_price, expected_close_date, deal_stage_id, 
                               client_id, owner_id, notes, date_created)
            SELECT id, title, expected_close_price, expected_close_date, deal_stage_id, 
                  client_id, owner_id, notes, date_created FROM deal
            """)
            
            # Drop old table and rename new table
            cursor.execute("DROP TABLE deal")
            cursor.execute("ALTER TABLE deal_new RENAME TO deal")
            
            print("Removed old columns")
        else:
            print("No old columns to remove")

        # Commit changes and close the connection
        conn.commit()
        conn.close()
        print("Database schema updated successfully!")
    except Exception as e:
        print(f"Error updating schema: {e}")
        if conn:
            conn.close()

if __name__ == "__main__":
    update_schema() 
