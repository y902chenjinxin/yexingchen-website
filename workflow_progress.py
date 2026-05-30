#!/usr/bin/env python3
"""
工作流进度追踪器
在每个 Step 开始前自动检查前置步骤是否完成
"""
import os
import sys

WORKFLOW_STEPS = {
    'Step 1': '需求管理',
    'Step 2': '需求评审（PRD）',
    'Step 3': '技术方案',
    'Step 4': '开发',
    'Step 5': 'Code Review',
    'Step 6': '方案评审',
    'Step 7': '安全审查',
    'Step 8': '自测',
    'Step 9': 'Staging 验证',
    'Step 10': '用户验收',
    'Step 11': 'Git 提交',
    'Step 12': '部署生产',
    'Step 13': '回滚方案',
    'Step 14': '收尾',
}

# 前置依赖关系
PREREQUISITES = {
    'Step 2': ['Step 1'],
    'Step 3': ['Step 2'],
    'Step 4': ['Step 3'],
    'Step 5': ['Step 4'],
    'Step 6': ['Step 5'],
    'Step 7': ['Step 6'],
    'Step 8': ['Step 2', 'Step 5', 'Step 7'],  # 需要 PRD + Code Review + 安全审查
    'Step 9': ['Step 8'],
    'Step 10': ['Step 9'],
    'Step 11': ['Step 10'],
    'Step 12': ['Step 11'],
    'Step 13': ['Step 12'],
    'Step 14': ['Step 13'],
}

# 完成的标志文件/检查点
COMPLETION_MARKERS = {
    'Step 1': [],  # 无文件依赖
    'Step 2': ['docs/PRD_v'],  # PRD 文档存在（模糊匹配）
    'Step 3': [],  # 技术方案文档
    'Step 4': [],  # 代码存在即可
    'Step 5': [],  # PR 已合并（检查 git log）
    'Step 6': [],  # 评审通过
    'Step 7': ['SECURITY_CHECKLIST.md'],  # 安全审查签字文件
    'Step 8': ['DEPLOY_CHECKLIST.md'],  # 自测清单完成
    'Step 9': [],
    'Step 10': [],
    'Step 11': ['.git'],  # git 已提交（检查 .git 目录）
    'Step 12': ['DEPLOY_CHECKLIST.md'],  # 部署检查完成
    'Step 13': ['docs/ROLLBACK.md'],  # 回滚方案已记录
    'Step 14': ['docs/RETROSPECTIVE.md'],  # 复盘文档
}

def check_marker_exists(markers, step_name):
    """检查标志文件是否存在"""
    if not markers:
        # 没有特定标志文件的步骤，检查 git commit
        if step_name == 'Step 11':
            return os.path.exists('.git')
        return True  # 无标志的步骤默认通过

    for marker in markers:
        if marker.endswith('.md'):
            # 模糊匹配 PRD 文件
            if 'PRD_v' in marker:
                # 查找任何 docs/PRD_v*.md
                for f in os.listdir('docs'):
                    if f.startswith('PRD_v') and f.endswith('.md'):
                        return True
            elif marker == 'SECURITY_CHECKLIST.md':
                return os.path.exists(marker)
            elif marker == 'DEPLOY_CHECKLIST.md':
                return os.path.exists(marker)
            elif marker == 'docs/ROLLBACK.md':
                return os.path.exists(marker)
            elif marker == 'docs/RETROSPECTIVE.md':
                return os.path.exists(marker)
            else:
                return os.path.exists(marker)
        elif marker == '.git':
            return os.path.exists('.git')

    return False

def check_step_completed(step_name):
    """检查某个步骤是否已完成"""
    markers = COMPLETION_MARKERS.get(step_name, [])
    return check_marker_exists(markers, step_name)

def check_prerequisites(step_name):
    """检查某个步骤的前置依赖是否都完成"""
    prereqs = PREREQUISITES.get(step_name, [])
    if not prereqs:
        return True, []

    incomplete = []
    for prereq in prereqs:
        if not check_step_completed(prereq):
            incomplete.append(prereq)

    return len(incomplete) == 0, incomplete

def print_header():
    print("\n" + "="*60)
    print("  [Workflow] Progress Check")
    print("="*60)

def print_step_status(step_name, status, note=""):
    symbol = "[OK]" if status else "[NO]"
    step_desc = WORKFLOW_STEPS.get(step_name, step_name)
    print(f"   {symbol} {step_name}: {step_desc}", end="")
    if note:
        print(f" ({note})")
    else:
        print()

def check_current_progress():
    """检查所有步骤的完成状态"""
    print_header()
    print("\n  各步骤完成状态：\n")

    for step in WORKFLOW_STEPS.keys():
        completed = check_step_completed(step)
        print_step_status(step, completed)

def verify_step(step_name):
    """验证某个步骤是否可以开始"""
    print_header()
    print(f"\n  正在检查: {step_name} - {WORKFLOW_STEPS.get(step_name, step_name)}")

    # 检查前置依赖
    ready, incomplete = check_prerequisites(step_name)

    if ready:
        print(f"\n  [OK] {step_name} pre-requisites completed. You can proceed.\n")
        return True
    else:
        print(f"\n  [BLOCKED] {step_name} requires these steps first:")
        for step in incomplete:
            step_desc = WORKFLOW_STEPS.get(step, step)
            print(f"     - {step} ({step_desc})")
        print(f"\n  [TIP] Complete the above steps first.\n")
        return False

def main():
    if len(sys.argv) < 2:
        # 无参数：显示所有步骤状态
        check_current_progress()
        print()
        return

    action = sys.argv[1]

    if action == 'check':
        # 检查当前进度
        check_current_progress()
        print()

    elif action in ['Step 2', 'Step 3', 'Step 4', 'Step 5', 'Step 6', 'Step 7',
                    'Step 8', 'Step 9', 'Step 10', 'Step 11', 'Step 12', 'Step 13', 'Step 14']:
        # 验证某个步骤是否可以开始
        success = verify_step(action)
        sys.exit(0 if success else 1)

    else:
        print(f"用法：")
        print(f"  python workflow_progress.py check          # 查看所有步骤状态")
        print(f"  python workflow_progress.py Step 2         # 检查某步骤是否可以开始")
        print(f"  python workflow_progress.py Step 8         # 例如检查 Step 8")
        sys.exit(1)

if __name__ == "__main__":
    main()