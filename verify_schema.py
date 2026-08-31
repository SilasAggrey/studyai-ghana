import sqlite3
conn = sqlite3.connect('studyai.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
print('users table columns:')
for col in columns:
    print(f'  {col[1]}: {col[2]}')
conn.close()