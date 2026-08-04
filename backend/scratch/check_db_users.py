import sqlite3

conn = sqlite3.connect("test_analytics.db")
cursor = conn.cursor()

try:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print("Tables in database:", [row[0] for row in cursor.fetchall()])
    
    cursor.execute("SELECT id, email, hashed_password, full_name, role FROM users;")
    rows = cursor.fetchall()
    print(f"\nTotal users in database: {len(rows)}")
    for row in rows:
        print("User:", row)
except Exception as e:
    print("Error:", e)
finally:
    conn.close()
