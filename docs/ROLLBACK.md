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

## v2.3.0 回滚方案

**部署时间**: 2026-05-31
**部署内容**: v2.3 融会贯通（键盘导航/手势控制/音效集成）
**功能**: Tab遍历岛屿、1-5数字键快捷、?帮助面板、手势缩放、hover音效
**回滚命令**:

```bash
# 1. 删除当前dist并重建
ssh root@203.195.208.25 "rm -rf /var/www/yexingchen/dist && mkdir -p /var/www/yexingchen/dist"

# 2. 上传旧版本文件（需要先构建旧版本）
# 假设 dist.v2.2.0 是之前的备份

# 3. 重启PM2
ssh root@203.195.208.25 "pm2 restart app"

# 4. 验证
curl -s https://yexingchen.cn -I | head -5
```

**关键文件**:
- HomeView.vue（键盘/手势集成）
- useKeyboardNavigation.js
- useGestureControl.js
- useIslandSound.js
- KeyboardHelp.vue

---

## v2.8.0 回滚方案

**部署时间**: 2026-05-31
**部署内容**: v2.8.0 玉简交互增强
**功能**: Tab遍历玉简、1-5数字键、Enter进入、左右滑动切换、双击进入、金色聚焦态
**回滚命令**:

```bash
# 1. 回滚dist目录
ssh root@203.195.208.25 "mv /var/www/yexingchen/dist /var/www/yexingchen/dist.v2.8.0 && mv /var/www/yexingchen/dist.bak.20260531 /var/www/yexingchen/dist"

# 2. 重启PM2
ssh root@203.195.208.25 "pm2 restart yexingchen-backend"

# 3. 验证
curl -s https://yexingchen.cn -I | head -5
```

**关键文件**:
- HomeView.vue（jade-focused 键盘聚焦态）
- useKeyboardNavigation.js（.jade-card 选择器）
- useGestureControl.js（左右滑动/双击）
- self_test.py（hover检查更新）

---

## v2.10.0 回滚方案

**部署时间**: 2026-05-31
**部署内容**: v2.10.0 功能收尾与体验优化
**功能**: 随机事件音效配合/修炼编年史持久化/首页云雾漂移效果
**回滚命令**:

```bash
# 1. 回滚dist目录
ssh root@203.195.208.25 "mv /var/www/yexingchen/dist /var/www/yexingchen/dist.v2.10.0 && mv /var/www/yexingchen/dist.bak.20260531_v29 /var/www/yexingchen/dist"

# 2. 重启PM2
ssh root@203.195.208.25 "pm2 restart yexingchen-backend"

# 3. 验证
curl -s https://yexingchen.cn -I | head -5
```

**关键文件**:
- useRandomEvents.js（音效配置）
- MistLayer.vue（云雾漂移）
- cultivation.js（修炼记录持久化）

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