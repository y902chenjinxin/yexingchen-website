import paramiko
import os

hostname = '203.195.208.25'
port = 22
username = 'root'
password = 'yxCHEN@12345678'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname, port, username, password)
sftp = client.open_sftp()

# Clean dist
stdin, stdout, stderr = client.exec_command('rm -rf /var/www/yexingchen/dist && mkdir -p /var/www/yexingchen/dist/assets')
print(stdout.read().decode('utf-8', errors='replace'))

base_local = 'D:/software/Claude Code/个人网站设计/frontend/dist'
base_remote = '/var/www/yexingchen/dist'

uploaded = 0
for root, dirs, files in os.walk(base_local):
    rel_path = os.path.relpath(root, base_local)
    if rel_path == '.':
        remote_dir = base_remote
    else:
        remote_dir = base_remote + '/' + rel_path.replace('\\', '/')

    try:
        sftp.stat(remote_dir)
    except:
        sftp.mkdir(remote_dir)

    for file in files:
        local_file = os.path.join(root, file)
        remote_file = remote_dir + '/' + file.replace('\\', '/')
        sftp.put(local_file, remote_file)
        uploaded += 1

print(f'Uploaded {uploaded} files')
files = sftp.listdir('/var/www/yexingchen/dist/assets')
print(f'Assets count: {len(files)}')

sftp.close()
client.close()
print('Done')