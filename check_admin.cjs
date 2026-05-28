import sqlite3
import hashlib

conn = sqlite3.connect('/var/www/yexingchen/backend/yexingchen.db')
cursor = conn.cursor()

# Check user
cursor.execute('SELECT id, email, password_hash FROM users WHERE email = ?', ('admin@yexingchen.cn',))
user = cursor.fetchone()
print(f'User: {user}')

conn.close()