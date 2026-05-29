#!/usr/bin/env python3
"""上传前端构建文件到服务器"""
import os
import paramiko
import getpass

def get_password():
    """从环境变量或安全存储获取密码"""
    # 优先从环境变量读取
    password = os.environ.get('SERVER_PASSWORD')
    if password:
        return password
    # 从.netrc读取
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

def upload_to_server():
    local_dist = "frontend/dist"
    remote_dist = "/var/www/yexingchen/dist"

    host = "203.195.208.25"
    port = 22
    username = "root"
    password = get_password()

    print(f"正在连接 {host}...")
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    # 清空远程目录
    print(f"清空远程目录 {remote_dist}...")
    try:
        sftp.stat(remote_dist)
        # 目录存在，清空内容
        for item in sftp.listdir(remote_dist):
            filepath = os.path.join(remote_dist, item)
            try:
                sftp.remove(filepath)
            except:
                pass
    except FileNotFoundError:
        sftp.mkdir(remote_dist, 0o755)

    # 上传本地文件
    print(f"上传 {local_dist}/* 到 {remote_dist}/...")
    for root, dirs, files in os.walk(local_dist):
        # 创建远程目录
        rel_path = os.path.relpath(root, local_dist)
        if rel_path != '.':
            remote_path = os.path.join(remote_dist, rel_path)
            try:
                sftp.mkdir(remote_path, 0o755)
            except:
                pass
        # 上传文件
        for file in files:
            local_file = os.path.join(root, file)
            if rel_path == '.':
                remote_file = os.path.join(remote_dist, file)
            else:
                remote_file = os.path.join(remote_dist, rel_path, file)
            print(f"  上传 {local_file} -> {remote_file}")
            sftp.put(local_file, remote_file)

    sftp.close()
    transport.close()
    print("上传完成!")

if __name__ == "__main__":
    upload_to_server()