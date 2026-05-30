# 部署检查清单

> 每次部署前必须逐项确认

---

## 部署前（本地）

- [ ] Git已提交（`git status` 无未提交变更）
- [ ] 已打版本Tag（`git tag vX.Y.Z`）
- [ ] `npm run build` 构建成功

## 自测（关键）

- [ ] `python self_test.py` 本地浏览器验证通过
- [ ] `python self_test.py record Step 8` 记录构建证据
- [ ] 浏览器自动化：`node browser_verify.js --local --all`

## 部署中（服务器）

- [ ] 前端dist已上传（`python upload_server.py`）
- [ ] PM2进程已重启（`python restart_pm2.py`）

## 部署后（验证）

- [ ] `/api/health` 返回200
- [ ] `node browser_verify.js --production --all` 生产环境验证通过

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

# 4. 重启后端
python restart_pm2.py
```