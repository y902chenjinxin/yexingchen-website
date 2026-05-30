import paramiko
import os

password = os.environ.get('SERVER_PASSWORD')
t = paramiko.Transport(('203.195.208.25', 22))
t.connect(username='root', password=password)
sftp = paramiko.SFTPClient.from_transport(t)

# Check HomeView CSS
f = sftp.file('/var/www/yexingchen/dist/assets/HomeView-lmOsS9zM.css', 'r')
content = f.read().decode('utf-8')
f.close()

# Find cloud-sea styles
import re
cloud_sea_match = re.search(r'\.cloud-sea[^{]*\{[^}]+\}', content)
array_layer_match = re.search(r'\.array-symbol-layer[^{]*\{[^}]+\}', content)

print('=== Cloud-sea CSS ===')
if cloud_sea_match:
    print(cloud_sea_match.group())

print('\n=== Array-symbol-layer CSS ===')
if array_layer_match:
    print(array_layer_match.group())

# Check for key properties
print('\n=== Key Properties ===')
print('inset:0 found:', 'inset:0' in content)
print('opacity: 0.08 found:', 'opacity: .08' in content or 'opacity:.08' in content)
print('opacity: 0.6 found (cloud):', 'opacity: .6' in content or 'opacity:.6' in content)

sftp.close()
t.close()