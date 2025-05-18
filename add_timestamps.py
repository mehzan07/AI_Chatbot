# This script connects to a SQLite database, finds all rows in the 'chats' table without a timestamp,
# and updates them with simulated timestamps based on the current time.

import sqlite3
from datetime import datetime, timedelta

# Connect to your SQLite database (update this path if needed)
conn = sqlite3.connect("chatbot.db")  # 🔁 Replace with your actual DB file
cursor = conn.cursor()

# Find all rows without a timestamp
cursor.execute("SELECT rowid FROM chats WHERE timestamp IS NULL OR timestamp = ''")
rows = cursor.fetchall()

# Set base time and generate timestamps incrementally
base_time = datetime.now() - timedelta(minutes=len(rows))

for i, (rowid,) in enumerate(rows):
    simulated_time = (base_time + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE chats SET timestamp = ? WHERE rowid = ?", (simulated_time, rowid))

# Save and close
conn.commit()
conn.close()

print(f"✅ Updated {len(rows)} rows with simulated timestamps.")
# This script connects to a SQLite database, finds all rows in the 'chats' table without a timestamp,
# and updates them with simulated timestamps based on the current time.