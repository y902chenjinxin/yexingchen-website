#!/usr/bin/env python3
"""上传前端构建文件到服务器"""
import os
import paramiko

def get_password():
    """从环境变量或安全存储获取密码"""
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

def upload_to_test():
    local_dist = "frontend/dist"
    remote_test = "/var/www/yexingchen/test"

    host = "203.195.208.25"
    port = 22
    username = "root"
    password = get_password()

    print(f"清理远程测试目录 {remote_test}...")