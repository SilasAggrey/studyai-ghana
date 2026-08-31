import sqlite3
import os

db_path = 'studyai.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    print('users table columns:')
    for col in columns:
        print(f'  {col[1]}: {col[2]}')
    conn.close()
else:
    print(f"Database {db_path} does not exist")