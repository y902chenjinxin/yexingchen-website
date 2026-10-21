"""前端部署（抗断连版，v2.46.187）

## 为什么另开一个脚本

原 `deploy_frontend.py` 是「先 rm -rf 线上目录 → 逐个 sftp.put 100+ 文件」。
2026-10-21 连续三次 SSH 断连，每次断在传输途中，线上目录已经被清空 → 站点白屏。

本脚本改成：
1. 本地把 dist 打成 **单个 tar.gz**
2. **只传 1 个文件**（一次 sftp.put，传输窗口从 100+ 次降到 1 次）
3. 服务器解压到 `dist.new`
4. 校验入口 JS（HTTP 200 且 >10KB）
5. **原子 mv 切换**：`dist` → `dist.old`，`dist.new` → `dist`
6. 成功后删 `dist.old`；失败则自动回滚

`download/`（APK/HAP）与 `.well-known/` 不归构建管，切换时从旧目录搬过去。

用法：
    backend/.venv/Scripts/python.exe scripts/deploy_fast.py
    DEPLOY_DIST=dist-deploy187 backend/.venv/Scripts/python.exe scripts/deploy_fast.py
"""
from __future__ import annotations

import io
import os
import sys
import tarfile
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
DIST_NAME = os.environ.get("DEPLOY_DIST", "dist")
LOCAL_DIST = ROOT / "frontend" / DIST_NAME
TAR_LOCAL = ROOT / "frontend" / f".{DIST_NAME}.tar.gz"

HOST = "203.195.208.25"
USER = "root"
BASE = "/var/www/yexingchen"
DIST = f"{BASE}/dist"
DIST_NEW = f"{BASE}/dist.new"
DIST_OLD = f"{BASE}/dist.old"
TAR_REMOTE = f"{BASE}/.deploy.tar.gz"
SITE = "https://yexingchen.cn"


def read_credential(key: str) -> str:
    env_path = ROOT.parent / ".secrets" / "local.env"
    for line in io.open(env_path, encoding="utf-8"):
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"未找到 {key} in {env_path}")


def main() -> int:
    if not LOCAL_DIST.is_dir():
        print(f"本地产物不存在：{LOCAL_DIST}")
        return 1
    files = [p for p in LOCAL_DIST.rglob("*") if p.is_file()]
    print(f"本地产物 {LOCAL_DIST.name}：{len(files)} 个文件")

    # 1) 打包
    t0 = time.time()
    if TAR_LOCAL.exists():
        TAR_LOCAL.unlink()
    with tarfile.open(TAR_LOCAL, "w:gz", compresslevel=6) as tar:
        for p in files:
            tar.add(p, arcname=str(p.relative_to(LOCAL_DIST)).replace("\\", "/"))
    print(f"  打包完成 {TAR_LOCAL.stat().st_size / 1024 / 1024:.1f} MB（{time.time() - t0:.1f}s）")

    # 2) 连接
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=read_credential("SSH_PASSWORD"), timeout=30)
    sftp = client.open_sftp()

    def run(cmd: str, quiet: bool = True) -> str:
        _, out, err = client.exec_command(cmd, timeout=180)
        o = out.read().decode(errors="replace").strip()
        e = err.read().decode(errors="replace").strip()
        if not quiet and (o or e):
            print(f"    $ {cmd}\n      {o or e}")
        return o or e

    # 3) 传 tar（唯一一次大传输）
    t1 = time.time()
    sftp.put(str(TAR_LOCAL), TAR_REMOTE)
    size_mb = Path(TAR_LOCAL).stat().st_size / 1024 / 1024
    print(f"  上传完成 {size_mb:.1f} MB（{time.time() - t1:.1f}s）")

    # 4) 解压到 dist.new（同时把旧目录里不归构建管的 download / .well-known 搬过来）
    run(f"rm -rf {DIST_NEW} && mkdir -p {DIST_NEW}")
    run(f"tar xzf {TAR_REMOTE} -C {DIST_NEW}")
    run(f"[ -d {DIST}/download ] && cp -a {DIST}/download {DIST_NEW}/download || true")
    run(f"[ -d {DIST}/.well-known ] && cp -a {DIST}/.well-known {DIST_NEW}/.well-known || true")
    n_new = run(f"find {DIST_NEW} -type f | wc -l")
    print(f"  服务器解压后文件数：{n_new}")

    # 5) 原子切换
    run(f"rm -rf {DIST_OLD} && mv {DIST} {DIST_OLD} && mv {DIST_NEW} {DIST}")
    print("  已切换 dist（旧目录保留为 dist.old）")

    # 6) 校验：入口 JS 真的能取到（只看 home=200 是无效的，SPA 的 index.html 必然 200）
    time.sleep(1)
    entry = run(f"grep -oE '/assets/index-[A-Za-z0-9_-]+\\.js' {DIST}/index.html | head -1")
    code = run(f"curl -s -o /dev/null -w '%{{http_code}} %{{size_download}}' {SITE}{entry}")
    print(f"  entry {entry} → {code}")
    ok = False
    parts = code.split()
    if len(parts) == 2 and parts[0] == "200" and int(parts[1]) > 10240:
        ok = True

    if ok:
        run(f"rm -rf {DIST_OLD} {TAR_REMOTE}")
        print("  ✓ 校验通过，旧目录已清理")
        rc = 0
    else:
        print("  !! 校验失败，回滚到 dist.old")
        run(f"rm -rf {DIST} && mv {DIST_OLD} {DIST}")
        run(f"rm -f {TAR_REMOTE}")
        rc = 3

    sftp.close()
    client.close()
    TAR_LOCAL.unlink(missing_ok=True)
    print("== deploy_fast done ==")
    return rc


if __name__ == "__main__":
    sys.exit(main())
