import sqlite3

conn = sqlite3.connect('/var/www/yexingchen/backend/yexingchen.db')
cursor = conn.cursor()

cursor.execute('SELECT id, key FROM global_settings')
rows = cursor.fetchall()
for row in rows:
    print(f'ID: {row[0]}, Key: {row[1]}')

conn.close()