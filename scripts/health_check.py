#!/usr/bin/env python3
"""
健康检查与告警脚本
配合cron或PM2监控使用
"""
import os
import sys
import sqlite3
import httpx
from datetime import datetime

# 配置
API_URL = "https://yexingchen.cn/api/health"
DB_PATH = "/var/www/yexingchen/backend/yexingchen.db"
PM2_API = "http://127.0.0.1:9610"

def check_api_health():
    """检查API健康状态"""
    try:
        resp = httpx.get(API_URL, timeout=5)
        if resp.status_code == 200:
            print(f"✅ API健康检查通过")
            return True
        else:
            print(f"❌ API返回状态码: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ API健康检查失败: {e}")
        return False

def check_database():
    """检查数据库状态"""
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在")
        return False

    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"✅ 数据库正常 (users表: {count}条)")
        return True
    except Exception as e:
        print(f"❌ 数据库错误: {e}")
        return False

def check_disk_space():
    """检查磁盘空间"""
    import shutil
    stat = shutil.disk_usage("/")
    free_gb = stat.free / (1024**3)
    if free_gb < 1:
        print(f"⚠️ 磁盘空间不足: {free_gb:.2f} GB")
        return False
    print(f"✅ 磁盘空间充足: {free_gb:.2f} GB")
    return True

if __name__ == "__main__":
    print(f"=== 健康检查 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")

    results = []
    results.append(("API健康", check_api_health()))
    results.append(("数据库", check_database()))
    results.append(("磁盘空间", check_disk_space()))

    print("\n=== 检查结果汇总 ===")
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"{status} {name}")

    if not all(r[1] for r in results):
        sys.exit(1)
    sys.exit(0)