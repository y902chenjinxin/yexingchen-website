#!/usr/bin/env python3
import paramiko
import os
import io
import sys

# Fix stdout encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

password = os.environ.get('SERVER_PASSWORD', 'yxCHEN@12345678')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('203.195.208.25', 22, 'root', password)

# Check PM2 status
stdin, stdout, stderr = ssh.exec_command('pm2 list')
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print("PM2 list output:")
print(out)
if err:
    print("STDERR:", err)

# Check if backend is running
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8000/api/health')
out = stdout.read().decode('utf-8', errors='replace')
print("\nBackend health check:")
print(out if out else "(empty)")

ssh.close()