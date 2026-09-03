import os, paramiko

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PORT = "203.195.208.25", "root", 22
BASE = "/var/www/yexingchen/parse-service"
_sec = os.path.join(os.path.dirname(ROOT), ".secrets", "local.env")
PW = None
for line in open(_sec, encoding="utf-8"):
    s = line.strip()
    if s.startswith("SSH_PASSWORD="):
        PW = s.split("=", 1)[1].strip()

FILES = [
    (os.path.join(ROOT, "parse-service", "main.py"), f"{BASE}/main.py"),
    (os.path.join(ROOT, "parse-service", "run.py"), f"{BASE}/run.py"),
    (os.path.join(ROOT, "parse-service", "requirements.txt"), f"{BASE}/requirements.txt"),
]

t = paramiko.Transport((HOST, PORT))
t.connect(username=USER, password=PW)
s = paramiko.SFTPClient.from_transport(t)


def cexec(cmd, timeout=600):
    ch = t.open_session(); ch.settimeout(timeout)
    ch.exec_command(cmd)
    out = b""; err = b""
    while True:
        if ch.recv_ready(): out += ch.recv(8192)
        if ch.recv_stderr_ready(): err += ch.recv_stderr(8192)
        if ch.exit_status_ready():
            while ch.recv_ready(): out += ch.recv(8192)
            while ch.recv_stderr_ready(): err += ch.recv_stderr(8192)
            break
    code = ch.recv_exit_status(); ch.close()
    return code, out.decode(errors="replace"), err.decode(errors="replace")


print("== 1/4 mkdir + upload parse-service files ==")
cexec(f"mkdir -p {BASE}", 30)
for local, remote in FILES:
    s.put(local, remote)
    print("  ->", remote)

print("== 2/4 create venv + install deps (parse-video-py from github) ==")
code, out, err = cexec(
    f"cd {BASE} && /usr/bin/python3 -m venv venv && "
    f"venv/bin/pip install -q --upgrade pip && "
    f"venv/bin/pip install -q fastapi==0.110.0 'uvicorn[standard]==0.29.0' httpx && "
    f"venv/bin/pip install -q 'git+https://github.com/wujunwei928/parse-video-py.git'; echo RC=$?",
    timeout=600,
)
print("  code:", code)
print("  OUT:", (out + err)[-1500:])

print("== 3/4 verify import + start via pm2 on 8070 ==")
code, out, err = cexec(
    f"cd {BASE} && venv/bin/python -c 'from parse_video_py import parse_video_share_url; print(\"import OK\")'; "
    f"pm2 delete parse-service >/dev/null 2>&1; "
    f"pm2 start venv/bin/python --name parse-service --cwd {BASE} -- run.py 2>&1 | tail -3; "
    f"sleep 3; pm2 save >/dev/null 2>&1; "
    f"curl -s http://127.0.0.1:8070/health; echo ''",
    timeout=180,
)
print("  code:", code)
print("  OUT:", out[-900:])
print("  ERR:", err[-300:])

s.close(); t.close()
print("== parse-service deploy done ==")