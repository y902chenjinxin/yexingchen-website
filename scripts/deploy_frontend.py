import os, paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
REMOTE_DIST = "/var/www/yexingchen/dist"
LOCAL_DIST = os.path.join(ROOT, "frontend", "dist")

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


print("== clean + upload dist ==")
cexec(f"rm -rf {REMOTE_DIST}")
cexec(f"mkdir -p {REMOTE_DIST}")
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

# verify served homepage returns 200 with new index
code, out = cexec("curl -s -o /dev/null -w 'home=%{http_code}' https://yexingchen.cn/ 2>/dev/null; echo ''")
print("  ", out.decode(errors="replace").strip())

s.close(); t.close()
print("== frontend deploy done ==")