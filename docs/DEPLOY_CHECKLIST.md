# 部署检查清单

> 每次部署前必须逐项确认

---

## 部署前（本地）

- [ ] Git已提交（`git status` 无未提交变更）
- [ ] 已打版本Tag（`git tag vX.Y.Z`）
- [ ] `npm run build` 构建成功
- [ ] `npm run lint` 通过（如已配置）
- [ ] 单元测试通过（`npm run test` 如有）
- [ ] E2E测试通过（`node test_site.cjs`）
- [ ] 安全扫描通过（`npm audit --audit-level=high`）

## 数据库（如有变更）

- [ ] 已编写migration脚本
- [ ] migration脚本在测试环境验证
- [ ] 已备份线上数据库（`python scripts/backup_db.py`）

## 部署中（服务器）

- [ ] 已备份远程dist（`/var/www/yexingchen/dist.bak.{date}`）
- [ ] 前端dist已上传（`python upload_server.py`）
- [ ] 后端依赖已同步（`python sync_backend.py`）
- [ ] nginx已重载
- [ ] PM2进程已重启

## 部署后（验证）

- [ ] `/api/health` 返回200
- [ ] 登录流程正常
- [ ] 至少一个岛屿功能验证
- [ ] 更新docs/ROLLBACK.md
- [ ] 更新docs/CHANGELOG.md

## 回滚准备

- [ ] 备份目录存在且完整
- [ ] 回滚命令已记录到docs/ROLLBACK.md

---

## 部署命令

```bash
# 1. 本地构建
cd frontend && npm run build

# 2. Git提交+Tag
git add -A
git commit -m "feat: v1.6.0 description"
git tag -a v1.6.0 -m "v1.6.0 release"
git push && git push --tags

# 3. 上传到服务器
python upload_server.py

# 4. 重启后端
python restart_pm2.py

# 5. 验证
node test_site.cjs
```