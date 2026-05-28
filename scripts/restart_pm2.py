import paramiko
import sys

hostname = '203.195.208.25'
port = 22
username = 'root'
password = 'yxCHEN@12345678'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname, port, username, password)

stdin, stdout, stderr = client.exec_command('cd /var/www/yexingchen/backend && pm2 restart all')
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print(out.encode('gbk', errors='replace').decode('gbk'), flush=True)
print(err.encode('gbk', errors='replace').decode('gbk'), flush=True)

client.close()
sys.exit(0)