import sqlite3

conn = sqlite3.connect('/var/www/yexingchen/backend/yexingchen.db')
cursor = conn.cursor()

cursor.execute('SELECT id, email, role, is_super_admin FROM users')
rows = cursor.fetchall()
for row in rows:
    print(f'ID: {row[0]}, Email: {row[1]}, Role: {row[2]}, is_super_admin: {row[3]}')

conn.close()