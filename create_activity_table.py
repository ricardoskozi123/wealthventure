import sqlite3

# Connect to the SQLite database directly
conn = sqlite3.connect('omcrm.db')
cursor = conn.cursor()

# Create the activity table with all required columns
cursor.execute('''
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    lead_id INTEGER,
    action_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    target_type VARCHAR(50),
    target_id INTEGER,
    data JSON,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (lead_id) REFERENCES lead(id)
)
''')
conn.commit()
conn.close()
print('Activity table created successfully!') 