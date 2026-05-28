import sqlite3
from passlib.hash import pbkdf2_sha256

# Reset admin password
conn = sqlite3.connect('/var/www/yexingchen/backend/yexingchen.db')
cursor = conn.cursor()

new_hash = pbkdf2_sha256.hash('Chen@12345678')
cursor.execute('UPDATE users SET password_hash = ? WHERE email = ?', (new_hash, 'admin@yexingchen.cn'))
conn.commit()

# Verify
cursor.execute('SELECT password_hash FROM users WHERE email = ?', ('admin@yexingchen.cn',))
hash_result = cursor.fetchone()[0]
verify = pbkdf2_sha256.verify('Chen@12345678', hash_result)
print(f'Password reset and verified: {verify}')

conn.close()