# 分支策略

## 分支模型

```
master (生产分支)
  └── feature/xxx (功能分支，从master切出)
  └── fix/xxx (修复分支，从master切出)
  └── hotfix/xxx (热修复分支，从master切出）
```

## 命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 功能分支 | `feature/功能描述` | `feature/login-limit` |
| 修复分支 | `fix/问题描述` | `fix/login-bug` |
| 热修复 | `hotfix/问题描述` | `hotfix/security-fix` |
| 发布分支 | `release/v版本号` | `release/v1.6.0` |

## 工作流程

### 1. 创建功能分支

```bash
# 从master切出新分支
git checkout master
git pull origin master
git checkout -b feature/xxx
```

### 2. 开发并提交

```bash
# 开发...
git add .
git commit -m "feat: 添加xxx功能"
git push -u origin feature/xxx
```

### 3. 创建PR

- 目标分支：`master`
- 必须包含：变更说明、测试结果、影响分析
- 指定至少1名评审人

### 4. 评审通过后合并

```bash
# 使用GitHub PR合并（推荐）
# 或命令行：
git checkout master
git merge --no-ff feature/xxx
git push origin master
git branch -d feature/xxx  # 删除本地分支
```

## 合并原则

1. **master受保护**：禁止直接push，必须通过PR合并
2. **至少1人review**：核心模块需2人review
3. **测试通过**：CI必须通过（构建+lint+测试）
4. **无敏感信息**：密码、密钥等不得提交
5. **保持线性历史**：使用`--no-ff`合并，保持提交历史清晰

## 回滚流程

```bash
# 回滚到上一个稳定版本
git revert <commit-hash>  # 创建新提交回滚
git push origin master

# 或硬回滚（紧急情况）
git checkout master
git reset --hard <commit-hash>
git push --force origin master  # 需谨慎使用
```