"""
Database migration to add password reset tokens table
Run this script to add the password reset functionality
"""
import sqlite3
import os
from datetime import datetime

def create_password_reset_table():
    """Create the password reset tokens table"""
    
    # Try to connect to the database
    db_paths = [
        'omcrm/dev.db',
        'instance/site.db',
        'dev.db'
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
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='password_reset_tokens'
        """)
        
        if cursor.fetchone():
            print("✅ Password reset tokens table already exists")
            conn.close()
            return True
        
        # Create the password reset tokens table
        cursor.execute("""
            CREATE TABLE password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(120) NOT NULL,
                user_type VARCHAR(20) NOT NULL,
                user_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                used BOOLEAN DEFAULT 0,
                used_at DATETIME,
                ip_address VARCHAR(45),
                brand_name VARCHAR(100)
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX idx_password_reset_token ON password_reset_tokens(token)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_password_reset_email ON password_reset_tokens(email)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_password_reset_expires ON password_reset_tokens(expires_at)
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ Password reset tokens table created successfully")
        print("🔑 Indexes created for optimal performance")
        return True
        
    except Exception as e:
        print(f"❌ Error creating password reset table: {e}")
        return False

def test_table_creation():
    """Test that the table was created correctly"""
    
    db_paths = ['omcrm/dev.db', 'instance/site.db', 'dev.db']
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("PRAGMA table_info(password_reset_tokens)")
        columns = cursor.fetchall()
        
        expected_columns = [
            'id', 'token', 'email', 'user_type', 'user_id', 
            'created_at', 'expires_at', 'used', 'used_at', 
            'ip_address', 'brand_name'
        ]
        
        actual_columns = [col[1] for col in columns]
        
        for expected in expected_columns:
            if expected not in actual_columns:
                print(f"❌ Missing column: {expected}")
                return False
        
        # Check indexes
        cursor.execute("PRAGMA index_list(password_reset_tokens)")
        indexes = cursor.fetchall()
        
        print("✅ Table structure verified")
        print(f"📊 Columns: {len(actual_columns)}")
        print(f"🔍 Indexes: {len(indexes)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing table: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Creating Password Reset Table...")
    print("=" * 50)
    
    if create_password_reset_table():
        print("\n🧪 Testing table creation...")
        if test_table_creation():
            print("\n✅ Password reset functionality is ready!")
            print("\n📝 Next steps:")
            print("1. Configure SMTP settings in admin panel")
            print("2. Set SMTP_PASSWORD environment variable")
            print("3. Test email functionality")
            print("\n💡 Usage:")
            print("- Users can now use 'Forgot Password' links")
            print("- Admin can test email config at /admin/test-email")
        else:
            print("\n❌ Table verification failed")
    else:
        print("\n❌ Failed to create password reset table")
    
    print("=" * 50) 