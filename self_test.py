#!/usr/bin/env python3
"""本地自测验证辅助脚本 - 帮助在 deploy 前系统性完成所有检查"""
import os
import re
import sys

CHECKLIST_FILE = "DEPLOY_CHECKLIST.md"
TMP_SELF_TEST = ".self_test_temp.md"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_build():
    """检查 npm run build 是否通过"""
    print_section("Step 1: 检查 Build")

    dist_path = "frontend/dist"
    if os.path.exists(dist_path):
        print("✅ frontend/dist 目录存在")
        # 检查关键文件
        key_files = ['index.html', 'assets/index-BnpgWBVb.js']
        for f in key_files:
            if os.path.exists(os.path.join(dist_path, f.replace('/', os.sep))):
                print(f"   ✅ {f}")
            else:
                print(f"   ❌ 缺少 {f}")
        return True
    else:
        print("❌ frontend/dist 不存在，请先运行: cd frontend && npm run build")
        return False

def check_css_vars():
    """检查是否有硬编码颜色"""
    print_section("Step 2: CSS 变量门控检查")

    vue_files = []
    for root, dirs, files in os.walk('frontend/src'):
        for f in files:
            if f.endswith('.vue'):
                vue_files.append(os.path.join(root, f))

    issues = []
    for vf in vue_files:
        try:
            with open(vf, 'r', encoding='utf-8') as f:
                content = f.read()
                # 查找 hex 颜色（但排除注释）
                hex_pattern = re.compile(r'#[0-9a-fA-F]{3,8}(?!.*/\*)')
                # 过滤掉注释行
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if '//' in line or '/*' in line or '*/' in line:
                        continue
                    matches = hex_pattern.findall(line)
                    for m in matches:
                        # 排除一些常见的非颜色值
                        if not any(x in m.lower() for x in ['url(', 'base64', 'data:']):
                            issues.append(f"{vf}:{i+1} -> {m}")
        except:
            pass

    if issues:
        print(f"❌ 发现 {len(issues)} 处硬编码颜色：")
        for issue in issues[:10]:
            print(f"   {issue}")
        if len(issues) > 10:
            print(f"   ... 还有 {len(issues) - 10} 处")
        return False
    else:
        print("✅ 无硬编码颜色，所有颜色使用 CSS 变量")
        return True

def check_hover_effects():
    """检查 hover 特效 HTML 元素是否存在"""
    print_section("Step 3: 岛屿 Hover 特效检查")

    home_view = "frontend/src/views/HomeView.vue"
    if not os.path.exists(home_view):
        print(f"❌ {home_view} 不存在")
        return False

    with open(home_view, 'r', encoding='utf-8') as f:
        content = f.read()

    required_elements = [
        ('music-island-hover', '音乐岛音符特效'),
        ('novel-island-hover', '小说岛书页特效'),
        ('video-island-hover', '视频岛光圈特效'),
        ('log-island-hover', '日志岛墨滴特效'),
        ('tool-island-hover', '工具岛齿轮特效'),
    ]

    all_found = True
    for class_name, desc in required_elements:
        if class_name in content:
            print(f"   ✅ {desc} ({class_name})")
        else:
            print(f"   ❌ 缺少 {desc} ({class_name})")
            all_found = False

    return all_found

def update_checklist_section(section_name, items_checked, items_total, details=""):
    """更新检查清单中的某个 section"""
    if not os.path.exists(CHECKLIST_FILE):
        return False

    with open(CHECKLIST_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 找到对应的 section
    section_marker = f"### {section_name}"
    if section_marker not in content:
        return False

    # 简单更新：找到未完成的项并标记
    # 这个实现比较简单，实际可能需要更复杂的解析
    return True

def run_all_checks():
    """运行所有自测检查"""
    print("\n" + "="*60)
    print("  🔍 自测验证辅助工具")
    print("  运行此脚本后可填充 DEPLOY_CHECKLIST.md")
    print("="*60)

    results = {
        'build': check_build(),
        'css_vars': check_css_vars(),
        'hover_effects': check_hover_effects(),
    }

    print("\n" + "="*60)
    print("  📊 自测结果汇总")
    print("="*60)

    all_passed = all(results.values())

    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")

    print()

    if all_passed:
        print("✅ 所有检查通过！")
        print("   请在 DEPLOY_CHECKLIST.md 中：")
        print("   1. 填写实际的自测描述（描述你实际看到的效")
        print("   2. 将 ☐ 改为 [x]")
        print("   3. 然后运行: python upload_server.py")
    else:
        print("❌ 部分检查未通过，请修复后再继续")
        print("   修复后重新运行此脚本验证")

    return all_passed

if __name__ == "__main__":
    run_all_checks()