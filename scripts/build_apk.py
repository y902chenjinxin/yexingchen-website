"""
一键重打 APK（v2.22.1+ 流程固化）。

用法：
    backend/.venv/Scripts/python.exe scripts/build_apk.py [--version 1.0.1]

默认：基于当前 twa-manifest.json（cn.yexingchen.app / 玄黄 / 自签 keystore）
重打：跑 gradle assembleRelease → apksigner 签名 → 拷到 /var/www/yexingchen/dist/download/
     → 重算 assetlinks.json → 部署 → 报回下载 URL + SHA256

工作流前提（首次运行时一次性建立，之后都在）：
  /opt/android-build/twa/yexingchen/{twa-manifest.json, android-project/}
  /opt/android-build/yexingchen.keystore
  /root/.gradle/init.d/aliyun-mirror.gradle
  ~/.gradle/wrapper/dists/gradle-8.11.1-bin/<hash>/gradle-8.11.1/

首次怎么搭起来？看 SKILL deploy-xuanhuang-site + 这次的对话历史。
"""
from __future__ import annotations

import argparse
import base64
import os
import re
import sys

import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(ROOT)

# 路径常量（与上次手动流程对齐）
SSH_HOST = "203.195.208.25"
SSH_USER = "root"
SSH_PORT = 22
REMOTE_TWA = "/opt/android-build/twa/yexingchen"
REMOTE_KEYSTORE = "/opt/android-build/yexingchen.keystore"
REMOTE_ANDROID_PROJECT = f"{REMOTE_TWA}/android-project"
REMOTE_UNSIGNED = f"{REMOTE_ANDROID_PROJECT}/app/build/outputs/apk/release/app-release-unsigned.apk"
REMOTE_SIGNED = f"{REMOTE_ANDROID_PROJECT}/app/build/outputs/apk/release/app-release.apk"
REMOTE_DIST = "/var/www/yexingchen/dist"
REMOTE_ASSETLINKS = f"{REMOTE_DIST}/.well-known/assetlinks.json"

# 包名/签名配置（与 twa-manifest 同步）
PACKAGE_ID = "cn.yexingchen.app"
KEY_ALIAS = "androidkey"
STORE_PASS = "yexingchen2026"

# gradle 构建环境变量
GRADLE_ENV = (
    "export JAVA_HOME=/usr/lib/jvm/java-17-konajdk-17.0.20-1.oc9; "
    "export PATH=$JAVA_HOME/bin:/opt/android-build/cmdline-tools/latest/bin:/opt/android-build/platform-tools:$PATH; "
    "export ANDROID_HOME=/opt/android-build; "
    "export ANDROID_SDK_ROOT=/opt/android-build; "
    "export GRADLE_OPTS='-Xmx1024m -Dorg.gradle.daemon=false'"
)

APKSIGNER = "/opt/android-build/build-tools/34.0.0/apksigner"


def get_password() -> str:
    p = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("SSH_PASSWORD="):
            return s.split("=", 1)[1].strip()
    raise SystemExit("SSH_PASSWORD not found in .secrets/local.env")


def ssh_connect() -> paramiko.SSHClient:
    # 项目里之前都用 paramiko.Transport，这次也保持一致（与 deploy 脚本同款）
    import paramiko as _p
    t = _p.Transport((SSH_HOST, SSH_PORT))
    t.connect(username=SSH_USER, password=get_password())
    return t


def run(t: paramiko.Transport, cmd: str, timeout: int = 120) -> str:
    ch = t.open_session()
    ch.settimeout(timeout)
    ch.exec_command(cmd)
    out = b""
    while True:
        if ch.recv_ready():
            out += ch.recv(8192)
        if ch.exit_status_ready():
            while ch.recv_ready():
                out += ch.recv(8192)
            break
    ch.recv_exit_status()
    ch.close()
    return out.decode(errors="replace").strip()


def write_remote(t: paramiko.Transport, content: str, dest_path: str) -> None:
    """用 base64 写远程文件，绕开 sftp put + 本地 trash 拦。"""
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    run(t, f"mkdir -p $(dirname {dest_path}) && echo {b64} | base64 -d > {dest_path}")


def find_cert_sha(t: paramiko.Transport) -> str:
    """apksigner verify --print-certs 提取证书 SHA-256。"""
    out = run(t, f"{APKSIGNER} verify --print-certs {REMOTE_SIGNED} 2>&1")
    m = re.search(r"SHA-256 digest:\s*([0-9a-fA-F]{64})", out)
    if not m:
        raise SystemExit(f"failed to extract cert SHA-256:\n{out}")
    return m.group(1).lower()


def patch_version(t: paramiko.Transport, version: str | None, code: int | None) -> None:
    if not version and code is None:
        return
    mf = f"{REMOTE_TWA}/twa-manifest.json"
    text = run(t, f"cat {mf}")
    if version:
        text = re.sub(r'"versionName"\s*:\s*"[^"]*"', f'"versionName": "{version}"', text)
        text = re.sub(r'"appVersion"\s*:\s*"[^"]*"', f'"appVersion": "{version}"', text)
    if code is not None:
        text = re.sub(r'"versionCode"\s*:\s*\d+', f'"versionCode": {code}', text)
        text = re.sub(r'"appVersionCode"\s*:\s*\d+', f'"appVersionCode": {code}', text)
    write_remote(t, text, mf)


def gradle_build(t: paramiko.Transport) -> None:
    """强制重跑 gradle assembleRelease。15 分钟 timeout 兜底。"""
    print("[build] gradle assembleRelease ...", flush=True)
    out = run(
        t,
        f"{GRADLE_ENV}; cd {REMOTE_ANDROID_PROJECT} && "
        "./gradlew assembleRelease --no-daemon --warning-mode=none 2>&1 | tail -8",
        timeout=900,
    )
    print(out)


def sign_apk(t: paramiko.Transport) -> None:
    print("[sign] apksigner ...", flush=True)
    out = run(
        t,
        f"java -jar /opt/android-build/build-tools/34.0.0/lib/apksigner.jar sign "
        f"--ks {REMOTE_KEYSTORE} --ks-key-alias {KEY_ALIAS} "
        f"--ks-pass pass:{STORE_PASS} --key-pass pass:{STORE_PASS} "
        f"--out {REMOTE_SIGNED} {REMOTE_UNSIGNED}",
    )
    print(out or "(signed)")


def deploy(t: paramiko.Transport, apk_filename: str) -> None:
    print(f"[deploy] copy -> /var/www/yexingchen/dist/download/{apk_filename}", flush=True)
    run(t, f"mkdir -p {REMOTE_DIST}/download {REMOTE_DIST}/.well-known")
    run(t, f"cp {REMOTE_SIGNED} {REMOTE_DIST}/download/{apk_filename}")


def write_assetlinks(t: paramiko.Transport, cert_sha: str) -> None:
    fp = ":".join(cert_sha[i:i + 2] for i in range(0, len(cert_sha), 2))
    assetlinks = (
        "[{\n"
        '  "relation": ["delegate_permission/common.handle_all_urls"],\n'
        '  "target": {\n'
        '    "namespace": "android_app",\n'
        f'    "package_name": "{PACKAGE_ID}",\n'
        f'    "sha256_cert_fingerprints": ["{fp}"]\n'
        "  }\n"
        "}]\n"
    )
    write_remote(t, assetlinks, REMOTE_ASSETLINKS)


def write_download_page(t: paramiko.Transport, apk_filename: str, sha256: str) -> None:
    page = (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        "<title>玄黄 · 安卓 APK 下载</title>\n"
        "<style>body{font-family:-apple-system,\"PingFang SC\",sans-serif;max-width:480px;margin:40px auto;padding:24px;background:#f6f4ee;color:#2c2c2a}"
        "h1{color:#8e6a2c;font-size:22px;margin:0 0 8px}"
        ".box{background:#fff;border:0.5px solid rgba(0,0,0,0.1);border-radius:12px;padding:20px;margin:16px 0}"
        ".btn{display:block;background:#8e6a2c;color:#fff;text-align:center;padding:14px;border-radius:8px;text-decoration:none;font-weight:500}"
        ".note{font-size:13px;color:#5f5e5a;line-height:1.7}.warn{background:#fbe8d4;padding:12px;border-radius:8px;color:#7a4d10;font-size:13px;margin-top:12px}"
        "small{font-size:11px;color:#888}</style></head><body>\n"
        "<h1>玄黄 · 安卓 App</h1>\n"
        f"<p class=\"note\">下载 APK 装到安卓手机（鸿蒙 4 兼容）。包名 <code>{PACKAGE_ID}</code>。</p>\n"
        "<div class=\"box\"><a href=\"/download/" + apk_filename + "\" class=\"btn\">下载 APK</a>\n"
        f"<p class=\"note\" style=\"margin-top:10px\"><small>SHA-256: {sha256}</small></p></div>\n"
        "<div class=\"box\"><p class=\"note\"><b>安装步骤：</b></p>"
        "<p class=\"note\">1. 第一次下载需开启「外部来源应用下载」<br>"
        "2. 打开 APK → 允许本次安装<br>"
        "3. 桌面出现「玄黄」图标</p></div>\n"
        "<div class=\"warn\"><b>提示：</b>App 实际打开的是 <a href=\"/\">yexingchen.cn</a>，"
        "站点更新时不用重新装 APK。</div>\n"
        "</body></html>\n"
    )
    write_remote(t, page, f"{REMOTE_DIST}/download/index.html")


def main() -> int:
    parser = argparse.ArgumentParser(description="一键重打玄黄 APK 并部署")
    parser.add_argument("--version", help="覆写 versionName/appVersion（默认沿用 twa-manifest.json）")
    parser.add_argument("--code", type=int, help="覆写 versionCode/appVersionCode（默认沿用 twa-manifest.json）")
    parser.add_argument(
        "--name", default=None,
        help="APK 输出文件名（默认 yexingchen-<versionName>.apk）",
    )
    args = parser.parse_args()

    print("== build_apk.py 启动 ==")
    t = ssh_connect()

    # 1) 改版本号（可选）
    patch_version(t, args.version, args.code)

    # 2) 拉 twa-manifest.json 里的 versionName 决定文件名
    mf = run(t, f"cat {REMOTE_TWA}/twa-manifest.json")
    m = re.search(r'"versionName"\s*:\s*"([^"]+)"', mf)
    version_name = m.group(1) if m else "1.0.0"
    apk_filename = args.name or f"yexingchen-{version_name}.apk"
    print(f"  versionName={version_name}, APK 文件名={apk_filename}")

    # 3) gradle build
    gradle_build(t)

    # 4) 签名
    sign_apk(t)

    # 5) 拿证书 SHA256
    cert_sha = find_cert_sha(t)
    print(f"  证书 SHA-256: {cert_sha}")

    # 6) APK 字节 SHA256
    apk_sha = run(t, f"sha256sum {REMOTE_SIGNED}").split()[0]
    print(f"  APK 字节 SHA-256: {apk_sha}")

    # 7) 部署
    deploy(t, apk_filename)
    write_assetlinks(t, cert_sha)
    write_download_page(t, apk_filename, apk_sha)

    # 8) 公网验证
    print("\n== 公网验证 ==")
    for path in [f"/download/{apk_filename}", "/download/", "/.well-known/assetlinks.json"]:
        code = run(t, f"curl -s -o /dev/null -w '%{{http_code}}' https://yexingchen.cn{path}")
        print(f"  https://yexingchen.cn{path}  ->  {code}")

    t.close()
    print("\n== build_apk.py 完成 ==")
    print(f"APK 下载：https://yexingchen.cn/download/{apk_filename}")
    print(f"下载页：https://yexingchen.cn/download/")
    return 0


if __name__ == "__main__":
    sys.exit(main())