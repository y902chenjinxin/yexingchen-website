# 部署检查清单

> 每次部署前必须逐项确认

---

## 部署前（本地）

- [x] Git已提交（`git status` 无未提交变更）
- [x] 已打版本Tag（`git tag v2.3.0`）
- [x] `npm run build` 构建成功

## 自测（关键）

- [x] `python self_test.py` 本地浏览器验证通过
- [x] `python self_test.py record Step 8` 记录构建证据
- [x] 浏览器自动化：`node browser_verify.js --local --all`

## 部署中（服务器）

- [x] 前端dist已上传（`python upload_server.py`）
- [x] PM2进程已重启（由 `upload_server.py` 自动执行 `pm2 restart yexingchen-backend`，无需单独脚本）

## 部署后（验证）

- [x] `/health` 返回200（Nginx `location = /health` 代理到后端；注意**不是** `/api/health`）
- [ ] `node browser_verify.js --production --all` 生产环境验证通过（部分测试因SPA加载时序问题 flaky）

## 回滚准备

- [ ] 回滚命令已记录到docs/ROLLBACK.md

---

## 部署命令

```bash
# 1. 构建
cd frontend && npm run build

# 2. 自测（本地preview）
python self_test.py && python self_test.py record Step 8

# 3. 上传（自动验证生产环境）
python upload_server.py

# 4. PM2 重启
# upload_server.py 上传完成后会自动执行 pm2 restart yexingchen-backend
# 如需手动重启：ssh root@203.195.208.25 "pm2 restart yexingchen-backend"
```