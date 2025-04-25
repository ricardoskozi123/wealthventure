import sqlite3

def add_impersonate_column():
    """Add the can_impersonate column to the resource table"""
    print("Adding can_impersonate column to resource table...")
    
    # Connect to the database
    conn = sqlite3.connect('dev.db')
    cursor = conn.cursor()
    
    # Check if the column already exists
    cursor.execute("PRAGMA table_info(resource)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    if 'can_impersonate' in column_names:
        print("can_impersonate column already exists")
    else:
        print("Adding can_impersonate column...")
        cursor.execute("ALTER TABLE resource ADD COLUMN can_impersonate BOOLEAN NOT NULL DEFAULT 0")
        conn.commit()
    
    # Update migration version to include the new migration
    cursor.execute("SELECT version_num FROM alembic_version")
    current_version = cursor.fetchone()
    
    if current_version and current_version[0] == 'de1f187d2bb7':
        print("Updating version to 11275332481d (can_impersonate migration)...")
        cursor.execute("UPDATE alembic_version SET version_num = '11275332481d'")
        conn.commit()
    
    print("Database update complete.")
    conn.close()

if __name__ == "__main__":
    add_impersonate_column() 