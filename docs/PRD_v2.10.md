# PRD v2.10.0 - 功能收尾与体验优化

## 1. 产品定位

**版本定位**：功能收尾与体验优化
**版本目标**：
1. 随机事件触发时有古琴/钟磬音效配合
2. 修炼编年史数据持久化（localStorage）
3. 首页云雾漂移背景增强

---

## 2. 功能详情

### 2.1 随机事件音效配合

**背景**：v2.4.0 已实现 RandomEventsLayer 随机事件（灯笼/丹炉/仙鹤/符文飘浮），但无音效配合

**功能**：
- 随机事件触发时播放对应音效
- 古琴音效（guqin.mp3）：灯笼、丹炉
- 钟磬音效（camera.mp3）：仙鹤、符文

**技术实现**：
- 在 RandomEventsLayer.vue 中添加音效触发逻辑
- 复用现有的 useIslandSound.js 的 Web Audio API
- 音效触发间隔限制：同一音效冷却时间 ≥3秒

---

### 2.2 修炼编年史数据持久化

**背景**：v2.4.0 已实现 CultivationChronicle.vue 时间线弹窗，但数据存储在内存，刷新后丢失

**功能**：
- 修炼记录存入 localStorage
- 记录字段：事件类型、时间戳、描述
- 事件类型：登录、首次访问岛屿、随机事件触发、修炼完成
- 支持查看历史记录

**技术实现**：
- 创建 useCultivationStore.js（Pinia + localStorage）
- CultivationChronicle.vue 改为从 store 读取数据
- 数据结构：`{ events: [{ type, timestamp, description }] }`

---

### 2.3 首页云雾漂移效果增强

**背景**：v2.8.0 待落地功能"首页空白区域填充"

**功能**：
- 增加云雾漂移动画填充首页底部区域
- 阵法符文方案（已有阵法模式）
- 灵气粒子从底部缓缓上升

**技术实现**：
- 复用现有的 ParticleLayer.vue灵气粒子
- 新增 MistLayer.vue 薄雾漂移动画层
- CSS animation: mist-drift 慢速横向漂移
- z-index层级：云雾在岛屿下方，不遮挡玉简

---

## 3. 验收标准

### 3.1 随机事件音效
- [ ] 灯笼出现时播放古琴音效
- [ ] 丹炉出现时播放古琴音效
- [ ] 仙鹤出现时播放钟磬音效
- [ ] 符文飘浮时播放钟磬音效
- [ ] 音效冷却时间 ≥3秒
- [ ] prefers-reduced-motion 时禁用音效

### 3.2 修炼编年史持久化
- [ ] 刷新页面后历史记录保留
- [ ] 登录后记录登录事件
- [ ] 首次进入岛屿记录事件
- [ ] 面板可查看完整历史

### 3.3 云雾漂移效果
- [ ] 首页底部有云雾漂移动画
- [ ] 动画速度缓慢（60s+周期）
- [ ] 不遮挡玉简卡片
- [ ] 移动端有降级处理

---

## 4. 技术方案

### 4.1 文件变更

| 文件 | 变更 |
|------|------|
| frontend/src/components/effects/RandomEventsLayer.vue | 添加音效触发 |
| frontend/src/composables/useIslandSound.js | 复用，添加playEventSound方法 |
| frontend/src/stores/cultivation.js（新建） | localStorage持久化store |
| frontend/src/components/effects/MistLayer.vue（新建） | 薄雾漂移组件 |
| frontend/src/views/HomeView.vue | 集成MistLayer |

### 4.2 依赖

- 复用现有音效文件：frontend/public/sounds/guqin.mp3, camera.mp3
- 无新增npm依赖

---

## 5. 排期

| 阶段 | 内容 | 时长 |
|------|------|------|
| 开发 | 3个功能实现 | 2h |
| 自测 | 本地验证 | 30min |
| 部署 | 按流程发布 | 30min |

---

## 6. 备注

**踩坑预警**：
- 随机事件音效不能过于频繁，需要冷却机制
- 云雾漂移不能影响玉简卡片的可操作性
- localStorage 有5MB限制，注意数据量