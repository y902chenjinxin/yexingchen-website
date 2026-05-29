---
name: server-access
description: 服务器访问信息（凭证通过环境变量管理）
metadata:
  type: reference
---

## 服务器信息

| 项目 | 值 |
|------|-----|
| IP | 203.195.208.25 |
| 端口 | 22 |
| 用户 | root |
| 部署路径 | /var/www/yexingchen/ |
| 后端路径 | /var/www/yexingchen/backend/ |
| 前端路径 | /var/www/yexingchen/dist/ |
| 数据库 | /var/www/yexingchen/backend/yexingchen.db |
| Python路径 | /var/www/yexingchen/backend/venv/bin/python |

## 凭证管理

**原则**：凭证不得硬编码，必须从环境变量读取

凭证存储位置（3选1）：
1. **推荐** `.env` 文件（加入 `.gitignore`）
2. 环境变量 `export SERVER_PASSWORD=xxx`
3. `~/.netrc` 文件

## 连接测试

```bash
ssh root@203.195.208.25
```

## PM2管理

```bash
# 重启后端
ssh root@203.195.208.25 "cd /var/www/yexingchen/backend && pm2 restart yexingchen-backend"

# 查看日志
ssh root@203.195.208.25 "pm2 logs yexingchen-backend --lines 50"
```