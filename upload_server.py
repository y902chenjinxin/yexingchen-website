#!/usr/bin/env python3
"""上传前端构建文件到服务器 - 带部署前检查门控"""
import os
import re
import sys

CHECKLIST_FILE = "DEPLOY_CHECKLIST.md"
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
        # 检测 section 标题
        for section in REQUIRED_SECTIONS:
            if section in line:
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
        print(f"❌ 错误：找不到 {CHECKLIST_FILE}")
        print(f"   请确认部署检查清单存在于当前目录")
        sys.exit(1)

    items = parse_checklist(content)
    blocked = check_deploy_blocked(items)

    if blocked:
        print(f"\n{'='*60}")
        print(f"❌ 部署被阻塞 - 存在 {len(blocked)} 个未完成的检查项")
        print(f"{'='*60}\n")

        # 按 section 分组显示
        by_section = {}
        for item in blocked:
            section = item['section'] or '未分类'
            if section not in by_section:
                by_section[section] = []
            by_section[section].append(item)

        for section, section_items in by_section.items():
            print(f"📋 {section}:")
            for item in section_items:
                print(f"   ☐ {item['text']}")
            print()

        print(f"{'='*60}")
        print(f"请先完成以上检查项（将 ☐ 改为 [x]），然后重新运行 deploy")
        print(f"提示：在 DEPLOY_CHECKLIST.md 中找到对应项，填入实际验证结果后勾选")
        print(f"{'='*60}\n")
        sys.exit(1)

def require_all_checked():
    """验证所有检查项都已完成"""
    content = read_checklist()
    if content is None:
        print(f"❌ 错误：找不到 {CHECKLIST_FILE}")
        sys.exit(1)

    items = parse_checklist(content)
    blocked = check_deploy_blocked(items)

    if blocked:
        require_checked("")  # 会打印详细错误并退出
    else:
        print(f"✅ 所有检查项已完成，部署检查通过")

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
    raise ValueError("未找到服务器密码，请设置 SERVER_PASSWORD 环境变量或配置 ~/.netrc")

def upload_to_server():
    print("\n" + "="*60)
    print("🚀 步骤 1/2：执行部署前检查")
    print("="*60)

    # 执行检查门控
    require_all_checked()

    # 获取自测描述用于日志
    desc = get_self_test_description()
    if desc:
        print(f"\n📝 自测验证记录：")
        print(f"   {desc[:100]}..." if len(desc) > 100 else f"   {desc}")

    print("\n" + "="*60)
    print("🚀 步骤 2/2：上传文件到服务器")
    print("="*60 + "\n")

    local_dist = "frontend/dist"
    remote_dist = "/var/www/yexingchen/dist"

    host = "203.195.208.25"
    port = 22
    username = "root"
    password = get_password()

    print(f"正在连接 {host}...")
    transport = paramiko.Transport((host, port))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    # 清空远程目录
    print(f"清空远程目录 {remote_dist}...")
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
    print(f"上传 {local_dist}/* 到 {remote_dist}/...")
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
            print(f"  上传 {local_file} -> {remote_file}")
            sftp.put(local_file, remote_file)

    sftp.close()
    transport.close()

    print("\n" + "="*60)
    print("✅ 上传完成！")
    print("="*60 + "\n")

if __name__ == "__main__":
    upload_to_server()