#!/usr/bin/env python3
"""数据库备份脚本 - 部署前后自动执行"""
import os
import shutil
from datetime import datetime

def backup_database():
    """备份SQLite数据库到备份目录"""
    db_path = "/var/www/yexingchen/backend/yexingchen.db"
    backup_dir = "/var/www/yexingchen/backups"

    # 创建备份目录
    os.makedirs(backup_dir, exist_ok=True)

    # 生成带时间戳的备份文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{backup_dir}/yexingchen.db.{timestamp}"

    # 复制数据库
    shutil.copy2(db_path, backup_path)
    print(f"数据库已备份: {backup_path}")

    # 保留最近10个备份
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('yexingchen.db.')])
    while len(backups) > 10:
        oldest = backups.pop(0)
        os.remove(os.path.join(backup_dir, oldest))
        print(f"删除旧备份: {oldest}")

    return backup_path

def restore_database(backup_file):
    """从备份恢复数据库"""
    db_path = "/var/www/yexingchen/backend/yexingchen.db"
    backup_path = f"/var/www/yexingchen/backups/{backup_file}"

    if not os.path.exists(backup_path):
        print(f"备份文件不存在: {backup_path}")
        return False

    # 先备份当前数据库
    current_backup = f"{db_path}.before_restore.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, current_backup)

    # 恢复
    shutil.copy2(backup_path, db_path)
    print(f"数据库已恢复: {backup_file}")
    print(f"当前数据库已备份为: {current_backup}")

    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) > 2:
            restore_database(sys.argv[2])
        else:
            print("用法: python backup_db.py restore <backup_file>")
    else:
        backup_database()