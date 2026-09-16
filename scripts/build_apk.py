"""
一键重打 APK（v2.22.2+ 流程固化）。

所有路径、密钥、签名常量从 `.secrets/apk-build.local.env` 读取；缺哪项就报错。
不在脚本里写真实密码或 hash —— 重新生成 keystore 后只改 secrets 文件即可。

用法：
    backend/.venv/Scripts/python.exe scripts/build_apk.py [--version 1.0.1]

首次环境搭建：
  - 服务器上建 keystore（keytool）、twa-manifest.json、Android 项目骨架
  - .secrets/apk-build.local.env 里填入 KEYSTORE_PATH / CERT_SHA256 / 路径常量
  - ~/.gradle/init.d/aliyun-mirror.gradle 配阿里云镜像（避免 AGP 卡顿）

工作流前提：
  /opt/android-build/twa/yexingchen/{twa-manifest.json, android-project/}
  /opt/android-build/yexingchen.keystore
  /root/.gradle/init.d/aliyun-mirror.gradle
  ~/.gradle/wrapper/dists/gradle-<VERSION>-bin/<hash>/
"""
from __future__ import annotations

import argparse
import base64
import os
import re
import sys

import paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 部署/SSH 仍从 local.env 读；APK 常量从 apk-build.local.env 读
SSH_ENV_PATH = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
APK_ENV_PATH = os.path.join(os.path.dirname(ROOT), ".secrets", "apk-build.local.env")


# ====================================================================
# 配置加载
# ====================================================================

def _load_env(path: str) -> dict[str, str]:
    """简单的 KEY=VALUE 文件解析（不展开 source/export 命令）。"""
    env = {}
    if not os.path.exists(path):
        return env
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, val = s.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def _required(env: dict, key: str, hint: str = "") -> str:
    val = env.get(key, "")
    if not val:
        raise SystemExit(f"缺少配置 {key}（{hint}）。请编辑 {APK_ENV_PATH}")
    return val


def load_apk_config() -> dict:
    env = _load_env(APK_ENV_PATH)
    return {
        "keystore_path": _required(env, "KEYSTORE_PATH"),
        "keystore_alias": _required(env, "KEYSTORE_ALIAS"),
        "keystore_pass": _required(env, "KEYSTORE_PASS"),
        "package_id": _required(env, "PACKAGE_ID"),
        "app_label": env.get("APP_LABEL", "玄黄"),
        "launcher_label": env.get("LAUNCHER_LABEL", env.get("APP_LABEL", "玄黄")),
        "cert_sha256": env.get("CERT_SHA256", "").lower(),  # 可空：build 后再回填
        "jdk17_home": _required(env, "JDK17_HOME"),
        "android_build_tools_dir": _required(env, "ANDROID_BUILD_TOOLS_DIR"),
        "apksigner_jar": env.get("APKSIGNER_JAR", "") or _required(env, "APKSIGNER_JAR", hint="apksigner.jar"),
        "gradle_version": _required(env, "GRADLE_VERSION"),
        "bubblewrap_node_modules": _required(env, "BUBBLEWRAP_NODE_MODULES"),
        "bubblewrap_core_node_modules": _required(env, "BUBBLEWRAP_CORE_NODE_MODULES"),
        "twa_project_dir": _required(env, "TWA_PROJECT_DIR"),
        "web_host": _required(env, "WEB_HOST"),
        "web_start_url": _required(env, "WEB_START_URL"),
        "web_apk_dir": _required(env, "WEB_APK_DIR"),
        "web_assetlinks_path": _required(env, "WEB_ASSETLINKS_PATH"),
        "web_download_page": _required(env, "WEB_DOWNLOAD_PAGE"),
        "theme_color": env.get("THEME_COLOR", "#8e6a2c"),
        "background_color": env.get("BACKGROUND_COLOR", "#f6f4ee"),
        "fallback_type": env.get("FALLBACK_TYPE", "customtabs"),
        "min_sdk_version": int(env.get("MIN_SDK_VERSION", "21")),
    }


def load_ssh_password() -> str:
    env = _load_env(SSH_ENV_PATH)
    for line in open(SSH_ENV_PATH, encoding="utf-8"):
        s = line.strip()
        if s.startswith("SSH_PASSWORD="):
            return s.split("=", 1)[1].strip()
    raise SystemExit("SSH_PASSWORD not found in .secrets/local.env")


# ====================================================================
# SSH 工具
# ====================================================================

def ssh_connect() -> paramiko.Transport:
    t = paramiko.Transport(("203.195.208.25", 22))
    t.connect(username="root", password=load_ssh_password())
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
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    run(t, f"mkdir -p $(dirname {dest_path}) && echo {b64} | base64 -d > {dest_path}")


def find_cert_sha(t: paramiko.Transport, apk_path: str, apksigner_jar: str) -> str:
    out = run(t, f"java -jar {apksigner_jar} verify --print-certs {apk_path} 2>&1")
    m = re.search(r"SHA-256 digest:\s*([0-9a-fA-F]{64})", out)
    if not m:
        raise SystemExit(f"failed to extract cert SHA-256:\n{out}")
    return m.group(1).lower()


def patch_version(t: paramiko.Transport, twa_dir: str, version: str | None, code: int | None) -> None:
    if not version and code is None:
        return
    mf = f"{twa_dir}/twa-manifest.json"
    text = run(t, f"cat {mf}")
    if version:
        text = re.sub(r'"versionName"\s*:\s*"[^"]*"', f'"versionName": "{version}"', text)
        text = re.sub(r'"appVersion"\s*:\s*"[^"]*"', f'"appVersion": "{version}"', text)
    if code is not None:
        text = re.sub(r'"versionCode"\s*:\s*\d+', f'"versionCode": {code}', text)
        text = re.sub(r'"appVersionCode"\s*:\s*\d+', f'"appVersionCode": {code}', text)
    write_remote(t, text, mf)


def gradle_build(t: paramiko.Transport, twa_dir: str, cfg: dict) -> None:
    android_project = f"{twa_dir}/android-project"
    env = (
        f"export JAVA_HOME={cfg['jdk17_home']}; "
        f"export PATH=$JAVA_HOME/bin:{cfg['android_build_tools_dir']}/../../platform-tools:$PATH; "
        f"export ANDROID_HOME=/opt/android-build; "
        f"export ANDROID_SDK_ROOT=/opt/android-build; "
        f"export GRADLE_OPTS='-Xmx1024m -Dorg.gradle.daemon=false'"
    )
    print("[build] gradle assembleRelease ...", flush=True)
    out = run(
        t,
        f"{env}; cd {android_project} && "
        "./gradlew assembleRelease --no-daemon --warning-mode=none 2>&1 | tail -8",
        timeout=900,
    )
    print(out)


def sign_apk(t: paramiko.Transport, unsigned: str, signed: str, cfg: dict) -> None:
    print("[sign] apksigner ...", flush=True)
    out = run(
        t,
        f"java -jar {cfg['apksigner_jar']} sign "
        f"--ks {cfg['keystore_path']} --ks-key-alias {cfg['keystore_alias']} "
        f"--ks-pass pass:{cfg['keystore_pass']} --key-pass pass:{cfg['keystore_pass']} "
        f"--out {signed} {unsigned}",
    )
    print(out or "(signed)")


def deploy_apk(t: paramiko.Transport, signed: str, apk_filename: str, cfg: dict) -> None:
    print(f"[deploy] copy -> {cfg['web_apk_dir']}/{apk_filename}", flush=True)
    run(t, f"mkdir -p {cfg['web_apk_dir']} {os.path.dirname(cfg['web_assetlinks_path'])}")
    run(t, f"cp {signed} {cfg['web_apk_dir']}/{apk_filename}")


def write_assetlinks(t: paramiko.Transport, cert_sha: str, cfg: dict) -> None:
    fp = ":".join(cert_sha[i:i + 2] for i in range(0, len(cert_sha), 2))
    assetlinks = (
        "[{\n"
        '  "relation": ["delegate_permission/common.handle_all_urls"],\n'
        '  "target": {\n'
        '    "namespace": "android_app",\n'
        f'    "package_name": "{cfg["package_id"]}",\n'
        f'    "sha256_cert_fingerprints": ["{fp}"]\n'
        "  }\n"
        "}]\n"
    )
    write_remote(t, assetlinks, cfg["web_assetlinks_path"])


def write_download_page(t: paramiko.Transport, apk_filename: str, sha256: str, cfg: dict) -> None:
    page = (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        f"<title>{cfg['app_label']} · 安卓 APK 下载</title>\n"
        "<style>body{font-family:-apple-system,\"PingFang SC\",sans-serif;max-width:480px;margin:40px auto;padding:24px;background:#f6f4ee;color:#2c2c2a}"
        "h1{color:#8e6a2c;font-size:22px;margin:0 0 8px}"
        ".box{background:#fff;border:0.5px solid rgba(0,0,0,0.1);border-radius:12px;padding:20px;margin:16px 0}"
        ".btn{display:block;background:#8e6a2c;color:#fff;text-align:center;padding:14px;border-radius:8px;text-decoration:none;font-weight:500}"
        ".note{font-size:13px;color:#5f5e5a;line-height:1.7}.warn{background:#fbe8d4;padding:12px;border-radius:8px;color:#7a4d10;font-size:13px;margin-top:12px}"
        "small{font-size:11px;color:#888}</style></head><body>\n"
        f"<h1>{cfg['app_label']} · 安卓 App</h1>\n"
        f"<p class=\"note\">下载 APK 装到安卓手机（鸿蒙 4 兼容）。包名 <code>{cfg['package_id']}</code>。</p>\n"
        "<div class=\"box\"><a href=\"/download/" + apk_filename + "\" class=\"btn\">下载 APK</a>\n"
        f"<p class=\"note\" style=\"margin-top:10px\"><small>SHA-256: {sha256}</small></p></div>\n"
        "<div class=\"box\"><p class=\"note\"><b>安装步骤：</b></p>"
        "<p class=\"note\">1. 第一次下载需开启「外部来源应用下载」<br>"
        "2. 打开 APK → 允许本次安装<br>"
        f"3. 桌面出现「{cfg['app_label']}」图标</p></div>\n"
        f"<div class=\"warn\"><b>提示：</b>App 实际打开的是 <a href=\"/\">{cfg['web_host']}</a>，"
        "站点更新时不用重新装 APK。</div>\n"
        "</body></html>\n"
    )
    write_remote(t, page, cfg["web_download_page"])


# ====================================================================
# 主流程
# ====================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="一键重打玄黄 APK 并部署")
    parser.add_argument("--version", help="覆写 versionName/appVersion（默认沿用 twa-manifest.json）")
    parser.add_argument("--code", type=int, help="覆写 versionCode/appVersionCode（默认沿用 twa-manifest.json）")
    parser.add_argument(
        "--name", default=None,
        help="APK 输出文件名（默认 yexingchen-<versionName>.apk）",
    )
    parser.add_argument(
        "--update-cert", action="store_true",
        help="把新计算的 CERT_SHA256 回写到 apk-build.local.env",
    )
    args = parser.parse_args()

    cfg = load_apk_config()
    print(f"== build_apk.py 启动（包名 {cfg['package_id']}）===")

    t = ssh_connect()

    # 1) 改版本号（可选）
    patch_version(t, cfg["twa_project_dir"], args.version, args.code)

    # 2) 拉 twa-manifest.json 里的 versionName 决定文件名
    mf = run(t, f"cat {cfg['twa_project_dir']}/twa-manifest.json")
    m = re.search(r'"versionName"\s*:\s*"([^"]+)"', mf)
    version_name = m.group(1) if m else "1.0.0"
    apk_filename = args.name or f"yexingchen-{version_name}.apk"
    print(f"  versionName={version_name}, APK 文件名={apk_filename}")

    unsigned = f"{cfg['twa_project_dir']}/android-project/app/build/outputs/apk/release/app-release-unsigned.apk"
    signed = f"{cfg['twa_project_dir']}/android-project/app/build/outputs/apk/release/app-release.apk"

    # 3) gradle build + 签名
    gradle_build(t, cfg["twa_project_dir"], cfg)
    sign_apk(t, unsigned, signed, cfg)

    # 4) 拿证书 SHA256
    cert_sha = find_cert_sha(t, signed, cfg["apksigner_jar"])
    print(f"  证书 SHA-256: {cert_sha}")

    # 5) APK 字节 SHA256
    apk_sha = run(t, f"sha256sum {signed}").split()[0]
    print(f"  APK 字节 SHA-256: {apk_sha}")

    # 6) 部署
    deploy_apk(t, signed, apk_filename, cfg)
    write_assetlinks(t, cert_sha, cfg)
    write_download_page(t, apk_filename, apk_sha, cfg)

    # 7) 公网验证
    print("\n== 公网验证 ==")
    for path in [f"/download/{apk_filename}", "/download/", "/.well-known/assetlinks.json"]:
        code = run(t, f"curl -s -o /dev/null -w '%{{http_code}}' https://{cfg['web_host']}{path}")
        print(f"  https://{cfg['web_host']}{path}  ->  {code}")

    # 8) 回填 CERT_SHA256 到 secrets（可选）
    if args.update_cert and cert_sha != cfg["cert_sha256"]:
        print(f"\n[CERT] 新证书 SHA256: {cert_sha}（与 secrets 里的 {cfg['cert_sha256']} 不一致，回填）")
        text = open(APK_ENV_PATH, encoding="utf-8").read()
        text = re.sub(
            r"CERT_SHA256=[0-9a-fA-F]*",
            f"CERT_SHA256={cert_sha}",
            text,
        )
        open(APK_ENV_PATH, "w", encoding="utf-8").write(text)
        print("[CERT] apk-build.local.env 已更新")

    t.close()
    print("\n== build_apk.py 完成 ==")
    print(f"APK 下载：https://{cfg['web_host']}/download/{apk_filename}")
    print(f"下载页：https://{cfg['web_host']}/download/")
    return 0


if __name__ == "__main__":
    sys.exit(main())