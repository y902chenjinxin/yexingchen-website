import sqlite3
import hashlib
from passlib.hash import pbkdf2_sha256

conn = sqlite3.connect('/var/www/yexingchen/backend/yexingchen.db')
cursor = conn.cursor()

# Test password
test_password = 'Chen@12345678'
stored_hash = '$pbkdf2-sha256$29000$lrL2/p.z9p7Tes.5N.Y8Bw$Yc2FSNPvroiC1lhjFVQiw3arxy6.xt7CYUJ1gAistL8'

# Try to verify
try:
    match = pbkdf2_sha256.verify(test_password, stored_hash)
    print(f'Password verification: {match}')
except Exception as e:
    print(f'Error: {e}')

# Generate new hash
new_hash = pbkdf2_sha256.hash(test_password)
print(f'New hash: {new_hash}')

# Update password
cursor.execute('UPDATE users SET password_hash = ? WHERE email = ?', (new_hash, 'admin@yexingchen.cn'))
conn.commit()
print('Password updated')

conn.close()