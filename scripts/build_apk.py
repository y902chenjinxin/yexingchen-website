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
    """生成多平台下载页：Android 可下载；鸿蒙 / 苹果 先留入口（敬请期待）。

    后续接入新平台时，只需把对应平台的 status 从 soon 改成 ready，
    并补上 href / 版本 / 校验值即可。
    """
    platforms = [
        {
            "key": "android",
            "name": "Android",
            "desc": "安卓手机 / 平板",
            "status": "ready",
            "href": f"/download/{apk_filename}",
            "version": apk_filename.replace(".apk", "").split("yexingchen-")[-1],
            "extra": sha256,
            "note": "兼容鸿蒙 4（APK 方式安装）",
        },
        {
            "key": "harmony",
            "name": "HarmonyOS",
            "desc": "鸿蒙 NEXT（HAP 包）",
            "status": "soon",
            "href": "",
            "version": "",
            "extra": "",
            "note": "正在适配，敬请期待",
        },
        {
            "key": "ios",
            "name": "iOS",
            "desc": "iPhone / iPad",
            "status": "soon",
            "href": "",
            "version": "",
            "extra": "",
            "note": "正在适配，敬请期待",
        },
    ]

    cards = []
    for p in platforms:
        ready = p["status"] == "ready"
        if ready:
            action = (
                f'<a class="dl-btn" href="{p["href"]}">立即下载</a>'
                f'<div class="dl-hash">SHA-256 {p["extra"]}</div>'
            )
            badge = '<span class="badge badge-ok">可下载</span>'
        else:
            action = '<span class="dl-btn dl-btn-disabled">敬请期待</span>'
            badge = '<span class="badge badge-soon">即将上线</span>'
        ver = f'<span class="dl-ver">v{p["version"]}</span>' if p["version"] else ''
        cards.append(
            f'<section class="card{" card-ready" if ready else ""}">'
            f'<header class="card-head">'
            f'<span class="p-name">{p["name"]}</span>{badge}{ver}'
            f'</header>'
            f'<p class="p-desc">{p["desc"]}</p>'
            f'<p class="p-note">{p["note"]}</p>'
            f'{action}'
            f'</section>'
        )

    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{cfg['app_label']} · 手机软件下载</title>
<style>
  :root {{
    --bg: #fafafa; --surface: #ffffff; --line: rgba(24,24,27,.10);
    --text: #18181b; --text2: #52525b; --text3: #a1a1aa;
    --accent: #5b6ae0; --accent-faint: rgba(91,106,224,.10);
    --danger: #dc2626;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0b0b12; --surface: #161326; --line: rgba(167,139,250,.18);
      --text: #f5f3ff; --text2: #a8a3c2; --text3: #6e698a;
      --accent: #a78bfa; --accent-faint: rgba(167,139,250,.14);
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 40px 20px 56px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; }}
  h1 {{ font-size: 26px; font-weight: 700; margin: 0 0 6px; letter-spacing: -.01em; }}
  .sub {{ color: var(--text2); font-size: 13px; margin: 0 0 28px; }}
  .card {{
    background: var(--surface); border: 1px solid var(--line);
    border-radius: 14px; padding: 18px 20px; margin-bottom: 14px;
  }}
  .card-ready {{ box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 10px 28px rgba(0,0,0,.06); }}
  .card-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
  .p-name {{ font-size: 16px; font-weight: 650; }}
  .badge {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 500; }}
  .badge-ok {{ background: var(--accent-faint); color: var(--accent); }}
  .badge-soon {{ background: rgba(150,150,150,.14); color: var(--text3); }}
  .dl-ver {{ font-size: 11px; color: var(--text3); margin-left: auto; font-variant-numeric: tabular-nums; }}
  .p-desc {{ font-size: 13px; color: var(--text2); margin: 0 0 2px; }}
  .p-note {{ font-size: 12px; color: var(--text3); margin: 0 0 14px; }}
  .dl-btn {{
    display: block; text-align: center; padding: 12px; border-radius: 10px;
    background: var(--accent); color: #fff; text-decoration: none;
    font-weight: 600; font-size: 14px; transition: opacity .15s;
  }}
  .dl-btn:hover {{ opacity: .9; }}
  .dl-btn-disabled {{
    background: transparent; color: var(--text3);
    border: 1px dashed var(--line); cursor: not-allowed; font-weight: 500;
  }}
  .dl-hash {{
    font-size: 10px; color: var(--text3); word-break: break-all;
    margin-top: 8px; font-family: ui-monospace, Menlo, Consolas, monospace;
  }}
  .steps {{ margin-top: 28px; }}
  .steps h2 {{ font-size: 13px; color: var(--text2); font-weight: 600; margin: 0 0 8px; }}
  .steps ol {{ margin: 0; padding-left: 20px; color: var(--text2); font-size: 13px; }}
  .steps li {{ margin-bottom: 4px; }}
  .tip {{
    margin-top: 20px; padding: 12px 14px; border-radius: 10px;
    background: var(--accent-faint); color: var(--text2); font-size: 12.5px;
  }}
  .tip a {{ color: var(--accent); }}
</style></head><body>
<div class="wrap">
  <h1>{cfg['app_label']} · 手机软件</h1>
  <p class="sub">选择你的设备平台下载安装。包名 <code>{cfg['package_id']}</code></p>

  {''.join(cards)}

  <div class="steps">
    <h2>安装步骤（Android）</h2>
    <ol>
      <li>首次下载需在系统设置中允许「外部来源应用」安装</li>
      <li>打开下载好的 APK，按提示允许本次安装</li>
      <li>桌面出现「{cfg['app_label']}」图标即安装完成</li>
    </ol>
  </div>

  <div class="tip">
    App 打开的就是 <a href="/">{cfg['web_host']}</a>，站点更新无需重装客户端。
  </div>
</div>
</body></html>
"""
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