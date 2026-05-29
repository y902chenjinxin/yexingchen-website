#!/usr/bin/env python3
"""重新上传前端构建文件到服务器（修复版）"""
import os
import paramiko

def get_password():
    password = os.environ.get('SERVER_PASSWORD')
    if password:
        return password
    raise ValueError("未找到服务器密码，请设置 SERVER_PASSWORD 环境变量")

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

    # 删除旧目录
    print(f"删除旧目录 {remote_dist}...")
    try:
        for item in sftp.listdir(remote_dist):
            filepath = remote_dist + "/" + item
            try:
                sftp.remove(filepath)
            except:
                pass
        sftp.rmdir(remote_dist)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"清理旧目录时出错: {e}")

    # 创建新目录
    print(f"创建新目录 {remote_dist}...")
    sftp.mkdir(remote_dist, 0o755)

    # 上传文件
    print(f"上传 {local_dist}/* 到 {remote_dist}/...")
    upload_count = 0
    for root, dirs, files in os.walk(local_dist):
        rel_path = os.path.relpath(root, local_dist)
        rel_path_slash = rel_path.replace("\\", "/")

        if rel_path != '.':
            remote_base = remote_dist + "/" + rel_path_slash
            try:
                sftp.mkdir(remote_base, 0o755)
            except:
                pass
        else:
            remote_base = remote_dist

        for file in files:
            local_file = os.path.join(root, file)
            remote_file = remote_base + "/" + file
            print(f"  上传 {file}")
            sftp.put(local_file, remote_file)
            upload_count += 1

    print(f"上传完成! 共 {upload_count} 个文件")

    # 验证
    print("\n=== 验证远程目录 ===")
    try:
        for item in sftp.listdir(remote_dist):
            stat = sftp.stat(remote_dist + "/" + item)
            print(f"{item}: {'DIR' if stat.st_mode > 2147483647 else stat.st_size}")
    except Exception as e:
        print(f"验证出错: {e}")

    sftp.close()
    transport.close()
    print("\n部署完成! 请访问 https://yexingchen.cn 验证")

if __name__ == "__main__":
    upload_to_server()