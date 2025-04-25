import sqlite3

def check_db(db_file):
    print(f"\n\nCHECKING {db_file}...")
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        print("Tables in database:", tables)
        
        # Check deal_stage table
        if 'deal_stage' in tables:
            cursor.execute("PRAGMA table_info(deal_stage);")
            columns = cursor.fetchall()
            print("\nDeal Stage Table Columns:")
            for col in columns:
                print(f"{col[0]}: {col[1]} ({col[2]}), {'PRIMARY KEY' if col[5] else ''}")
            
            cursor.execute("SELECT * FROM deal_stage LIMIT 5;")
            rows = cursor.fetchall()
            print("\nSample Deal Stage rows:")
            for row in rows:
                print(row)
        
        # Check deal table
        if 'deal' in tables:
            cursor.execute("PRAGMA table_info(deal);")
            columns = cursor.fetchall()
            print("\nDeal Table Columns:")
            for col in columns:
                print(f"{col[0]}: {col[1]} ({col[2]}), {'PRIMARY KEY' if col[5] else ''}")
            
            cursor.execute("SELECT count(*) FROM deal;")
            count = cursor.fetchone()[0]
            print(f"\nTotal Deal rows: {count}")
            
            cursor.execute("SELECT * FROM deal LIMIT 5;")
            rows = cursor.fetchall()
            print("\nSample Deal rows:")
            for row in rows:
                print(row)
        
        # Check sequences
        try:
            cursor.execute("SELECT name FROM sqlite_sequence;")
            sequences = cursor.fetchall()
            if sequences:
                print("\nSequences in database:")
                for seq in sequences:
                    print(seq[0])
                    cursor.execute(f"SELECT seq FROM sqlite_sequence WHERE name='{seq[0]}';")
                    val = cursor.fetchone()
                    print(f"  Current value: {val[0]}")
        except sqlite3.OperationalError:
            print("\nNo sequences table found in this database")
        
        # Check configuration
        if 'config' in tables:
            cursor.execute("SELECT * FROM config LIMIT 5;")
            rows = cursor.fetchall()
            print("\nConfiguration settings:")
            for row in rows:
                print(row)
    
        conn.close()
    except Exception as e:
        print(f"Error checking {db_file}: {str(e)}")

if __name__ == "__main__":
    databases = ["app.db", "dev.db", "omcrm.db"]
    for db in databases:
        check_db(db) 