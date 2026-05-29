#!/usr/bin/env python3
"""同步后端代码到服务器 - 包含依赖安装"""
import os
import paramiko
import io
import sys

def get_password():
    password = os.environ.get('SERVER_PASSWORD')
    if password:
        return password
    netrc_path = os.path.expanduser("~/.netrc")
    if os.path.exists(netrc_path):
        with open(netrc_path) as f:
            for line in f:
                if '203.195.208.25' in line:
                    parts = line.strip().split()
                    for i, part in enumerate(parts):
                        if part == 'password' and i + 1 < len(parts):
                            return parts[i + 1]
    raise ValueError("未找到服务器密码，请设置 SERVER_PASSWORD 环境变量或配置 ~/.netrc")

def sync_backend():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    host = "203.195.208.25"
    port = 22
    username = "root"
    password = get_password()

    print(f"正在连接 {host}...")
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, username, password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    backend_dir = "/var/www/yexingchen/backend"

    # 需要同步的后端文件
    backend_files = [
        ("backend/app", f"{backend_dir}/app"),
        ("backend/requirements.txt", f"{backend_dir}/requirements.txt"),
    ]

    print("同步后端文件...")
    for local_path, remote_path in backend_files:
        if os.path.isdir(local_path):
            # 目录同步
            for root, dirs, files in os.walk(local_path):
                rel_path = os.path.relpath(root, local_path)
                remote_root = remote_path if rel_path == '.' else f"{remote_path}/{rel_path.replace(os.sep, '/')}"
                try:
                    sftp.stat(remote_root)
                except:
                    sftp.mkdir(remote_root, 0o755)
                for file in files:
                    local_file = os.path.join(root, file)
                    remote_file = f"{remote_root}/{file}"
                    print(f"  上传 {local_file} -> {remote_file}")
                    sftp.put(local_file, remote_file)
        else:
            print(f"  上传 {local_path} -> {remote_path}")
            sftp.put(local_path, remote_path)

    sftp.close()

    # 安装依赖
    print("安装后端依赖...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {backend_dir} && pip install -r requirements.txt")
    output = stdout.read().decode('utf-8', errors='replace')
    error = stderr.read().decode('utf-8', errors='replace')
    if output:
        print(output)
    if error:
        print(f"错误: {error}")

    # 重启PM2
    print("重启 PM2...")
    stdin, stdout, stderr = ssh.exec_command("pm2 restart yexingchen-backend")
    output = stdout.read().decode('utf-8', errors='replace')
    if output:
        print(output)

    ssh.close()
    print("后端同步完成!")

if __name__ == "__main__":
    sync_backend()