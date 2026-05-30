# TECH_DESIGN_v2.4.md

> 修仙仙府 v2.4 技术设计方案
> 版本: v2.4
> 日期: 2026-05-31

---

## 概述

v2.4 纯前端功能，集成已有组件到 HomeView.vue。

---

## 1. useRandomEvents.js

### 技术方案

```
位置: frontend/src/composables/useRandomEvents.js
依赖: Vue 3 Composition API, HomeView.vue, useCelestialSystem
```

**状态**:
```javascript
const lastEventTime = ref(null)     // 上次事件触发时间
const currentEvent = ref(null)     // 当前事件类型
const isEventActive = ref(false)    // 事件是否激活
```

**事件类型**:
```javascript
const EVENT_TYPES = {
  METEOR: 'meteor',       // 流星雨（夜间概率触发）
  QI_BURST: 'qi_burst',   // 灵气爆发（集齐5个岛屿后概率触发）
  CRANES: 'cranes'        // 仙鹤群飞（酉时概率触发）
}
```

**冷却逻辑**:
```javascript
const COOLDOWN_MS = 30 * 60 * 1000  // 30分钟

function canTriggerEvent() {
  if (!lastEventTime.value) return true
  return Date.now() - lastEventTime.value >= COOLDOWN_MS
}
```

**触发条件判断**:
- 流星雨：夜间（18:00-06:00）且概率随机
- 灵气爆发：用户已访问全部5个岛屿
- 仙鹤群飞：酉时（17:00-19:00）且概率随机

---

## 2. RandomEventsLayer.vue

### 技术方案

```
位置: frontend/src/components/effects/RandomEventsLayer.vue
依赖: useRandomEvents, HomeView.vue
```

**渲染逻辑**:
```vue
<template>
  <Teleport to="body">
    <div v-if="isEventActive" class="random-events-layer">
      <!-- 流星雨 -->
      <div v-if="currentEvent === 'meteor'" class="meteor-shower">
        <div v-for="i in 20" :key="i" class="meteor" :style="getMeteorStyle(i)"></div>
      </div>

      <!-- 灵气爆发 -->
      <div v-if="currentEvent === 'qi_burst'" class="qi-burst">
        <div v-for="i in 30" :key="i" class="qi-particle"></div>
      </div>

      <!-- 仙鹤群飞 -->
      <div v-if="currentEvent === 'cranes'" class="crane-flock">
        <div v-for="i in 8" :key="i" class="crane"></div>
      </div>
    </div>
  </Teleport>
</template>
```

**事件时长**: 5秒后自动消失

---

## 3. CultivationChronicle.vue

### 技术方案

```
位置: frontend/src/components/common/CultivationChronicle.vue
依赖: HomeView.vue (下拉菜单触发)
```

**集成方式**:
在 HomeView.vue 的用户下拉菜单中添加"编年史"选项：

```vue
<el-dropdown-item command="chronicle">
  <el-icon><Calendar /></el-icon>
  <span>修炼编年史</span>
</el-dropdown-item>
```

**时间线内容**:
```javascript
const timeline = [
  { date: '2024-01', event: '网站上线' },
  { date: '2024-06', event: 'v1.0 首发' },
  { date: '2025-05', event: 'v2.0 天人合一发布' },
  // ...
]
```

**显示逻辑**:
- 点击菜单项 → 显示弹窗
- 弹窗内时间线滚动展示
- 有关闭按钮

---

## 4. SpiritRootQuiz.vue

### 技术方案

```
位置: frontend/src/components/common/SpiritRootQuiz.vue
依赖: HomeView.vue
```

**触发方式**:
- 在导航下拉菜单中添加"灵根测试"选项
- 或在编年史弹窗中添加入口

**测试题目**（5道）:
1. 你最喜欢什么颜色？ A金 B木 C水 D火 E土
2. 你的性格更接近？ A温和 B坚韧 C灵动 D热情 E稳重
3. 你偏好什么环境？ A山林 B草原 C湖畔 D火山 E荒漠
4. 你的行事风格？ A谋定后动 B百折不挠 C随机应变 D雷厉风行 E沉稳持重
5. 你向往什么？ A隐居修行 B征服挑战 C自由探索 D轰轰烈烈 E平安是福

**灵根计算**:
- 统计算法：A(1) B(2) C(3) D(4) E(5)
- 最多选项对应灵根类型

**结果展示**:
```javascript
const spiritRoots = {
  METAL: { name: '金', traits: '果断刚毅', element: '金' },
  WOOD: { name: '木', traits: '仁慈正直', element: '木' },
  WATER: { name: '水', traits: '聪慧灵动', element: '水' },
  FIRE: { name: '火', traits: '热情奔放', element: '火' },
  EARTH: { name: '土', traits: '稳重厚实', element: '土' }
}
```

---

## 5. EntranceOverlay.vue

### 技术方案

```
位置: frontend/src/components/transition/EntranceOverlay.vue
依赖: router/index.js
```

**集成方式**:
在 `router/index.js` 中使用 `beforeEach` 导航守卫：

```javascript
router.beforeEach((to, from, next) => {
  // 如果是从首页到岛屿，触发墨染过渡
  if (from.path === '/home' && to.path.includes('/island')) {
    showEntranceOverlay(() => next())
  } else {
    next()
  }
})
```

**动画逻辑**:
- 墨水从中心扩散
- 持续 800ms
- 然后缩小消失

---

## 6. HomeView.vue 集成

### 下拉菜单修改

在用户下拉菜单中添加：

```vue
<el-dropdown-item command="chronicle">
  <el-icon><Calendar /></el-icon>
  <span>修炼编年史</span>
</el-dropdown-item>
<el-dropdown-item command="spirit-quiz">
  <el-icon><Star /></el-icon>
  <span>灵根测试</span>
</el-dropdown-item>
```

### handleDropdownCommand 修改

```javascript
case 'chronicle':
  showChronicle.value = true
  break
case 'spirit-quiz':
  showSpiritQuiz.value = true
  break
```

---

## 7. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 随机事件触发概率不可控 | 低 | 使用 seeded random 确保确定性 |
| 墨染动画性能 | 中 | 使用 CSS animation，不使用 JS 动画 |
| 组件过多影响加载 | 低 | 使用 Teleport 避免重复挂载 |

---

## 8. 文件清单

| 操作 | 文件路径 |
|------|----------|
| 修改 | `frontend/src/views/HomeView.vue` |
| 修改 | `frontend/src/router/index.js` |
| 已有 | `frontend/src/composables/useRandomEvents.js` |
| 已有 | `frontend/src/components/effects/RandomEventsLayer.vue` |
| 已有 | `frontend/src/components/common/CultivationChronicle.vue` |
| 已有 | `frontend/src/components/common/SpiritRootQuiz.vue` |
| 已有 | `frontend/src/components/transition/EntranceOverlay.vue` |

---

**文档状态**: 技术方案设计完成，待开发