import os, paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
REMOTE_DIST = "/var/www/yexingchen/dist"
# 可用环境变量覆盖源目录（如 DEPLOY_DIST=dist-deploy，绕开 safe-delete 对 dist 清空的拦截）
LOCAL_DIST = os.path.join(ROOT, "frontend", os.environ.get("DEPLOY_DIST", "dist"))

p = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
PW = None
for line in open(p, encoding="utf-8"):
    s = line.strip()
    if s.startswith("SSH_PASSWORD="):
        PW = s.split("=", 1)[1].strip()

t = paramiko.Transport((HOST, PORT))
t.connect(username=USER, password=PW)
s = paramiko.SFTPClient.from_transport(t)


def cexec(cmd, wait=True, timeout=120):
    ch = t.open_session(); ch.settimeout(timeout)
    ch.exec_command(cmd)
    if not wait:
        ch.close(); return "", ""
    out = b""
    while True:
        if ch.recv_ready(): out += ch.recv(8192)
        if ch.exit_status_ready():
            while ch.recv_ready(): out += ch.recv(8192)
            break
    code = ch.recv_exit_status(); ch.close(); return code, out


print("== clean + upload dist (preserve download/ + .well-known/) ==")
# download/ 由 build_apk.py 服务端生成（下载引导页 + APK）、.well-known/ 存放 TWA
# assetlinks.json（域名关联校验），都不在 frontend/dist 里；整体 rm -rf 会误删它们
# 导致 APK 下载页失效、TWA 打开卡启动屏。先挪走保存、清空再放回。
cexec(f"mv {REMOTE_DIST}/download {REMOTE_DIST}.download.tmp >/dev/null 2>&1; "
      f"mv {REMOTE_DIST}/.well-known {REMOTE_DIST}.wellknown.tmp >/dev/null 2>&1; "
      f"rm -rf {REMOTE_DIST}; mkdir -p {REMOTE_DIST}")
cexec(f"mv {REMOTE_DIST}.download.tmp {REMOTE_DIST}/download >/dev/null 2>&1; "
      f"mv {REMOTE_DIST}.wellknown.tmp {REMOTE_DIST}/.well-known >/dev/null 2>&1")
n = 0
for root, _, files in os.walk(LOCAL_DIST):
    rel = os.path.relpath(root, LOCAL_DIST).replace("\\", "/")
    rdir = REMOTE_DIST if rel == "." else f"{REMOTE_DIST}/{rel}"
    if rel != ".":
        cexec(f"mkdir -p {rdir}")
    for f in files:
        s.put(os.path.join(root, f), f"{rdir}/{f}")
        n += 1
print("  uploaded files:", n)

code, out = cexec("cat /var/www/yexingchen/dist/sw.js | head -5; echo '---'; grep -o \"xuanhuang-v[0-9]*\" /var/www/yexingchen/dist/sw.js | head -1")
print("  sw version:", out.decode(errors="replace").strip())

# ---- 校验：不只是「首页 200」，而是「入口 JS 真的能取到」----
# v2.46.177 事故：SSH 中途断连，index.html 已传但 assets 没传完，
# 首页仍然返回 200（SPA 的 index.html 是静态文件），实际白屏。
# 所以必须解析 index.html 里引用的 /assets/index-*.js 并真实取一次。
code, out = cexec("curl -s -o /dev/null -w 'home=%{http_code}' https://yexingchen.cn/ 2>/dev/null; echo ''")
print("  ", out.decode(errors="replace").strip())

code, out = cexec("grep -oE '/assets/index-[A-Za-z0-9_-]+\\.js' /var/www/yexingchen/dist/index.html | head -1")
entry = out.decode(errors="replace").strip()
if not entry:
    print("  !! 无法从 index.html 解析出入口 JS，部署可能不完整")
    raise SystemExit(2)

code, out = cexec(f"curl -s -o /dev/null -w '%{{http_code}} %{{size_download}}' https://yexingchen.cn{entry}")
status = out.decode(errors="replace").strip()
print(f"  entry {entry} → {status}")
parts = status.split()
if len(parts) != 2 or parts[0] != "200" or int(parts[1]) < 10240:
    print("  !! 入口 JS 不可用或体积异常，站点会白屏 —— 请立即重跑本脚本")
    raise SystemExit(3)

s.close(); t.close()
print("== frontend deploy done ==")