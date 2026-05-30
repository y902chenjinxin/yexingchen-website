#!/usr/bin/env python3
"""上传前端构建文件到服务器 - 带部署前检查门控"""
import os
import re
import sys

CHECKLIST_FILE = "DEPLOY_CHECKLIST.md"
WORKFLOW_CHECK = "workflow_progress.py"

def check_workflow_gate(target_step):
    """在开始某步骤前检查前置步骤是否完成"""
    if not os.path.exists(WORKFLOW_CHECK):
        return True  # 如果工作流脚本不存在，跳过检查

    # 导入工作流检查模块
    sys.path.insert(0, '.')
    try:
        from workflow_progress import check_prerequisites, WORKFLOW_STEPS
    except ImportError:
        return True

    ready, incomplete = check_prerequisites(target_step)

    if not ready:
        print(f"\n{'='*60}")
        print(f"[BLOCKED] {target_step} requires prerequisite steps first")
        print(f"{'='*60}\n")
        print(f"  To start {target_step} ({WORKFLOW_STEPS.get(target_step, '')})")
        print(f"  You need to complete:\n")

        for step in incomplete:
            step_desc = WORKFLOW_STEPS.get(step, step)
            print(f"     [NO] {step} ({step_desc})")

        print(f"\n  Complete the above steps first.")
        print(f"{'='*60}\n")
        return False

    return True

def check_workflow_complete():
    """在提交或部署前确保关键步骤都已完成"""
    if not os.path.exists(WORKFLOW_CHECK):
        return True

    sys.path.insert(0, '.')
    try:
        from workflow_progress import check_step_completed, WORKFLOW_STEPS
    except ImportError:
        return True

    # 部署前必须完成的步骤
    required_for_deploy = ['Step 2', 'Step 5', 'Step 7', 'Step 8', 'Step 11']

    incomplete = []
    for step in required_for_deploy:
        if not check_step_completed(step):
            incomplete.append(step)

    if incomplete:
        print(f"\n{'='*60}")
        print(f"[BLOCKED] These required steps are not completed:")
        print(f"{'='*60}\n")
        for step in incomplete:
            step_desc = WORKFLOW_STEPS.get(step, step)
            print(f"     [NO] {step} ({step_desc})")
        print(f"\n  Complete these steps before deploying.")
        print(f"{'='*60}\n")
        return False

    # Step 8 完成后，必须验证 dist 未被修改，且 build 来自当前 commit
    if os.path.exists('.workflow_completion_log.json'):
        try:
            import json
            with open('.workflow_completion_log.json', 'r') as f:
                log = json.load(f)
            if 'Step 8' in log and 'dist_hash' in log['Step 8']:
                # 检查 dist hash 是否匹配
                current_hash = hashlib.sha256()
                with open('frontend/dist/index.html', 'rb') as hf:
                    current_hash.update(hf.read())
                current_hash = current_hash.hexdigest()[:16]
                recorded_hash = log['Step 8']['dist_hash']

                if current_hash != recorded_hash:
                    print(f"\n{'='*60}")
                    print(f"[BLOCKED] Build output modified after Step 8 verification")
                    print(f"{'='*60}\n")
                    print(f"  Recorded hash: {recorded_hash}")
                    print(f"  Current hash:  {current_hash}")
                    print(f"\n  Run 'npm run build' again to regenerate, then re-verify Step 8.")
                    print(f"{'='*60}\n")
                    return False

                # 检查 dist 是否在 record 之后被重新 build 过（基于 git commit 时间戳）
                # 如果 dist 的修改时间早于 git commit 时间，说明 dist 不是从当前代码构建的
                import subprocess
                result = subprocess.run(['git', 'log', '-1', '--format=%ct', 'HEAD'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    git_timestamp = int(result.stdout.strip())
                    dist_mtime = int(os.path.getmtime('frontend/dist/index.html'))
                    if dist_mtime < git_timestamp:
                        print(f"\n{'='*60}")
                        print(f"[BLOCKED] dist/ was built BEFORE current commit")
                        print(f"{'='*60}\n")
                        print(f"  Git commit time: {git_timestamp}")
                        print(f"  dist build time:  {dist_mtime}")
                        print(f"\n  Your code has changed since last build.")
                        print(f"  Run 'cd frontend && npm run build' to rebuild from current code.")
                        print(f"{'='*60}\n")
                        return False
        except:
            pass

    return True

REQUIRED_SECTIONS = [
    "Step 8: 自测（最关键）",
    "Step 11: Git 提交",
    "Step 12: 部署生产",
]

def read_checklist():
    """读取检查清单内容"""
    if not os.path.exists(CHECKLIST_FILE):
        return None
    with open(CHECKLIST_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def parse_checklist(content):
    """解析检查清单，返回每个检查项的状态"""
    lines = content.split('\n')
    items = []
    current_section = None

    for line in lines:
        # 检测 section 标题（处理 markdown 标题格式 ### Step X: ...）
        stripped = line.strip()
        for section in REQUIRED_SECTIONS:
            # Remove markdown heading prefix and whitespace for matching
            section_key = section.split(':')[0]  # "Step 8" from "Step 8: 自测（最关键）"
            if stripped.startswith('### ') and section_key in stripped:
                current_section = section

        # 检测 checkbox 项
        if '- [ ]' in line or '- [x]' in line:
            is_checked = '- [x]' in line
            item_text = line.replace('- [ ]', '').replace('- [x]', '').strip()
            items.append({
                'section': current_section,
                'text': item_text,
                'checked': is_checked
            })

    return items

def check_deploy_blocked(items):
    """检查是否有未完成的必填项，返回被阻塞的项列表"""
    blocked = []
    for item in items:
        if not item['checked']:
            blocked.append(item)
    return blocked

def require_checked(description):
    """要求某项必须已勾选，未勾选则阻塞并退出"""
    content = read_checklist()
    if content is None:
        print(f"\n[ERROR] {CHECKLIST_FILE} not found")
        print(f"   Please ensure the deployment checklist exists in current directory")
        sys.exit(1)

    items = parse_checklist(content)
    blocked = check_deploy_blocked(items)

    if blocked:
        print(f"\n{'='*60}")
        print(f"[BLOCKED] {len(blocked)} checklist items not completed")
        print(f"{'='*60}\n")

        # 按 section 分组显示
        by_section = {}
        for item in blocked:
            section = item['section'] or 'Uncategorized'
            if section not in by_section:
                by_section[section] = []
            by_section[section].append(item)

        for section, section_items in by_section.items():
            print(f"[Section] {section}:")
            for item in section_items:
                print(f"   [ ] {item['text']}")
            print()

        print(f"{'='*60}")
        print(f"Complete the above items ([ ] -> [x]) then run deploy again")
        print(f"Tip: Edit DEPLOY_CHECKLIST.md, fill in actual test results, check [x]")
        print(f"{'='*60}\n")
        sys.exit(1)

def require_all_checked():
    """验证所有检查项都已完成"""
    content = read_checklist()
    if content is None:
        print(f"[ERROR] {CHECKLIST_FILE} not found")
        sys.exit(1)

    items = parse_checklist(content)
    blocked = check_deploy_blocked(items)

    if blocked:
        require_checked("")  # 会打印详细错误并退出
    else:
        print(f"[OK] All checklist items completed, deploy check passed")

def get_self_test_description():
    """获取自测描述"""
    content = read_checklist()
    if content is None:
        return None

    # 查找"自测描述"部分
    match = re.search(r'\*\*自测描述\*\*.*?\*\*.*?\*\*:\s*(.*?)(?=\n\n|\Z)', content, re.DOTALL)
    if match:
        desc = match.group(1).strip()
        if desc and len(desc) > 20:  # 至少要有实质内容
            return desc
    return None

# ==================== 以下是实际上传逻辑 ====================

import paramiko
import getpass

def get_password():
    """从环境变量或安全存储获取密码"""
    password = os.environ.get('SERVER_PASSWORD')
    if password:
        return password
    netrc_path = os.path.expanduser("~/.netrc")
    if os.path.exists(netrc_path):
        with open(netrc_path) as f:
            for line in f:
                if '203.195.208.25' in line:
                    parts = line.strip().split()
                    for i, part in enumerate(parts):
                        if part == 'password' and i + 1 < len(parts):
                            return parts[i + 1]
    raise ValueError("SERVER_PASSWORD not set. Set it via environment variable.")

def check_browser_verification():
    """通过用户浏览器验证网站效果 - 强制门控"""
    import subprocess
    import sys

    print("\n" + "="*60)
    print("[Browser] Running automated verification")
    print("="*60)

    # 检查 Chrome 是否以调试模式启动
    try:
        import urllib.request
        urllib.request.urlopen('http://localhost:9222/json', timeout=2)
    except:
        print("[ERROR] Chrome not running with --remote-debugging-port=9222")
        print("        Please start Chrome: chrome.exe --remote-debugging-port=9222")
        print("        Then run this script again.")
        return False

    # 运行浏览器验证脚本（部署后验证生产环境）
    result = subprocess.run(
        [sys.executable, 'browser_verify.js'],
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode == 0:
        print("[OK] Browser verification passed (production)")
        return True
    else:
        print("[FAIL] Browser verification failed")
        print("       Output:", result.stdout)
        print("       Error:", result.stderr)
        return False

def upload_to_server():
    # 在部署前检查工作流关键步骤是否完成
    if not check_workflow_complete():
        print("[TIP] Run 'python workflow_progress.py Step 8' to see how to complete missing steps")
        sys.exit(1)

    # 强制浏览器验证 - 必须通过才能部署
    if not check_browser_verification():
        print("\n[BLOCKED] Browser verification failed")
        print("          Fix the issues above, then run this script again.")
        print("          Make sure Chrome is running with --remote-debugging-port=9222")
        sys.exit(1)

    print("\n" + "="*60)
    print("[Step 2/2] Uploading files to server")
    print("="*60 + "\n")

    local_dist = "frontend/dist"
    remote_dist = "/var/www/yexingchen/dist"

    host = "203.195.208.25"
    port = 22
    username = "root"
    password = get_password()

    print(f"Connecting to {host}...")
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    # 清空远程目录
    print(f"Clearing remote directory {remote_dist}...")
    try:
        sftp.stat(remote_dist)
        for item in sftp.listdir(remote_dist):
            filepath = os.path.join(remote_dist, item)
            try:
                sftp.remove(filepath)
            except:
                pass
    except FileNotFoundError:
        sftp.mkdir(remote_dist, 0o755)

    # 上传本地文件
    print(f"Uploading {local_dist}/* to {remote_dist}/...")
    for root, dirs, files in os.walk(local_dist):
        rel_path = os.path.relpath(root, local_dist).replace("\\", "/")
        if rel_path != '.':
            remote_path = remote_dist + "/" + rel_path
            try:
                sftp.mkdir(remote_path, 0o755)
            except:
                pass
        for file in files:
            local_file = os.path.join(root, file)
            if rel_path == '.':
                remote_file = remote_dist + "/" + file
            else:
                remote_file = remote_path + "/" + file
            print(f"  Upload {local_file} -> {remote_file}")
            sftp.put(local_file, remote_file)

    sftp.close()
    transport.close()

    print("\n" + "="*60)
    print("[OK] Upload completed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    upload_to_server()