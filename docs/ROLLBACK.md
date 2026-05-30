# 回滚方案记录

> 每次部署后更新此文档

---

## v1.6.0 回滚方案

**部署时间**: 2026-05-29
**部署内容**: 流程优化落地（13步流程规范化）
**回滚命令**:

```bash
# 1. 回滚dist目录
ssh root@203.195.208.25 "mv /var/www/yexingchen/dist /var/www/yexingchen/dist.v1.6.0.new && mv /var/www/yexingchen/dist.bak.20260529 /var/www/yexingchen/dist"

# 2. 重启nginx
ssh root@203.195.208.25 "nginx -s reload"

# 3. 验证
curl -s https://yexingchen.cn -I | head -5
```

---

## v2.1.0 回滚方案

**部署时间**: 2026-05-30
**部署内容**: v2.1 初窥门径（鼠标轨迹/修为印章/hover特效/顶栏优化）
**回滚命令**:

```bash
# 1. 回滚dist目录
ssh root@203.195.208.25 "mv /var/www/yexingchen/dist /var/www/yexingchen/dist.v2.1.0.new && mv /var/www/yexingchen/dist.bak.20260529 /var/www/yexingchen/dist"

# 2. 重启nginx
ssh root@203.195.208.25 "nginx -s reload"

# 3. 验证
curl -s https://yexingchen.cn -I | head -5
```

---

## 回滚原则

1. **先备份再部署**：每次 `npm run build` 前先备份远程 dist
2. **版本Tag必须**：每次部署打 tag，回滚切到指定 tag
3. **小步快跑**：每次部署尽量少改，降低回滚影响面
4. **回滚后验证**：回滚完成后立即验证核心功能

---

## 回滚检查清单

- [ ] 确认备份目录存在且完整
- [ ] 执行 dist 切换
- [ ] nginx 重载
- [ ] 健康检查 `/api/health` 返回 200
- [ ] 登录功能验证
- [ ] 至少一个岛屿内容验证
- [ ] 通知用户回滚完成