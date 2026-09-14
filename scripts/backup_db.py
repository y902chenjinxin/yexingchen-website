#!/usr/bin/env python3
"""# 玄黄生产数据库自动备份

# 用法：
#   python scripts/backup_db.py
#   python scripts/backup_db.py --keep 7
#   python scripts/backup_db.py --upload-cos  # 同时上传到腾讯云 COS

# 备份策略：
#   - 默认备份到 BACKUP_DIR（默认 /var/www/yexingchen/backups/db/）
#   - 文件名：yexingchen_YYYYMMDD-HHMMSS.db
#   - 自动保留最近 --keep 份（默认 7），更老的自动删除
#   - 可选 --upload-cos 上传到腾讯云 COS（需配置 COS_* 环境变量）

# 配合 cron（每天凌晨 2 点执行）：
#   0 2 * * * cd /var/www/yexingchen && /usr/bin/python3 scripts/backup_db.py --upload-cos >> /var/log/xuanhuang-backup.log 2>&1
"""
import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BACKEND_DIR / "yexingchen.db"
DEFAULT_BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/var/www/yexingchen/backups/db"))


def create_backup(db_path: Path, backup_dir: Path) -> Path:
    """创建本地备份文件，返回备份路径。"""
    if not db_path.exists():
        raise FileNotFoundError(f"数据库文件不存在: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"yexingchen_{timestamp}.db"

    # 使用 sqlite3 backup API（一致性快照，比直接 cp 安全）
    import sqlite3
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(backup_path))
    try:
        with dst:
            src.backup(dst)
    finally:
        src.close()
        dst.close()

    size_mb = backup_path.stat().st_size / 1024 / 1024
    print(f"[backup] 成功创建: {backup_path} ({size_mb:.2f} MB)")
    return backup_path


def cleanup_old_backups(backup_dir: Path, keep: int):
    """清理旧备份，只保留最近 keep 份。"""
    backups = sorted(backup_dir.glob("yexingchen_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(backups) <= keep:
        print(f"[cleanup] 当前 {len(backups)} 份备份 <= keep={keep}，无需清理")
        return
    to_delete = backups[keep:]
    for f in to_delete:
        f.unlink()
        print(f"[cleanup] 删除旧备份: {f.name}")
    print(f"[cleanup] 保留 {keep} 份最新备份")


def upload_to_cos(backup_path: Path):
    """上传到腾讯云 COS（需配置 COS_* 环境变量）。"""
    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError:
        print("[cos] 未安装 cos-python-sdk-v5，跳过上传", file=sys.stderr)
        return False

    region = os.environ.get("COS_REGION")
    secret_id = os.environ.get("COS_SECRET_ID")
    secret_key = os.environ.get("COS_SECRET_KEY")
    bucket = os.environ.get("COS_BUCKET", "yexingfiles-1409757734")
    if not all([region, secret_id, secret_key]):
        print("[cos] COS_REGION / COS_SECRET_ID / COS_SECRET_KEY 未配置，跳过上传", file=sys.stderr)
        return False

    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)
    key = f"backups/db/{backup_path.name}"
    with open(backup_path, "rb") as f:
        client.put_object(Bucket=bucket, Key=key, Body=f)
    print(f"[cos] 已上传: cos://{bucket}/{key}")
    return True


def main():
    parser = argparse.ArgumentParser(description="玄黄数据库备份")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="数据库文件路径")
    parser.add_argument("--out", type=Path, default=DEFAULT_BACKUP_DIR, help="备份输出目录")
    parser.add_argument("--keep", type=int, default=7, help="保留最近 N 份备份（默认 7）")
    parser.add_argument("--upload-cos", action="store_true", help="上传到腾讯云 COS")
    args = parser.parse_args()

    try:
        backup_path = create_backup(args.db, args.out)
        cleanup_old_backups(args.out, args.keep)
        if args.upload_cos:
            upload_to_cos(backup_path)
        return 0
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
