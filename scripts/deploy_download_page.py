"""仅重写「多平台下载页」，不重新构建 APK。

用途：下载页模板改动时（新增平台入口 / 改样式），无需跑 gradle 重打包装包，
      直接读取服务器上已有 APK 的文件名与 SHA-256，重新生成并写入下载页。

用法：
    python scripts/deploy_download_page.py
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_apk import (  # noqa: E402
    load_apk_config,
    ssh_connect,
    run,
    write_download_page,
)


def main() -> int:
    cfg = load_apk_config()
    print(f"== deploy_download_page.py 启动（{cfg['web_host']}）==")

    t = ssh_connect()
    download_dir = os.path.dirname(cfg["web_download_page"])

    # 1) 找服务器上现存的 APK（取最新一个）
    listing = run(t, f"ls -1t {download_dir}/*.apk 2>/dev/null")
    apks = [p.strip() for p in listing.splitlines() if p.strip().endswith(".apk")]
    if not apks:
        print("!! 未在服务器上找到 APK，请先跑 build_apk.py")
        t.close()
        return 1
    apk_path = apks[0]
    apk_filename = os.path.basename(apk_path)
    print(f"  APK: {apk_filename}")

    # 2) 取版本号（从文件名解析）与 SHA-256
    m = re.search(r"yexingchen-(.+)\.apk$", apk_filename)
    version = m.group(1) if m else ""
    apk_sha = run(t, f"sha256sum {apk_path}").split()[0]
    print(f"  版本: {version}")
    print(f"  SHA-256: {apk_sha}")

    # 3) 重写下载页
    write_download_page(t, apk_filename, apk_sha, cfg)
    print("  下载页已重写")

    # 4) 公网验证
    print("\n== 公网验证 ==")
    for path in ["/download/", f"/download/{apk_filename}"]:
        code = run(t, f"curl -s -o /dev/null -w '%{{http_code}}' https://{cfg['web_host']}{path}")
        print(f"  https://{cfg['web_host']}{path}  ->  {code}")

    t.close()
    print("\n== 完成 ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
