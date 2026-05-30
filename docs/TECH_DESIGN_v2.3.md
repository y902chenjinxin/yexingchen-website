# TECH_DESIGN_v2.3.md

> 修仙仙府 v2.3 技术设计方案
> 版本: v2.3
> 日期: 2026-05-31

---

## 概述

v2.3 纯前端功能，使用 Vue 3 Composition API 实现，无需后端 API 变更。

---

## 1. useKeyboardNavigation.js

### 技术方案

```
位置: frontend/src/composables/useKeyboardNavigation.js
依赖: Vue 3 Composition API, HomeView.vue
```

**状态**:
```javascript
const islands = ref([])           // 岛屿元素列表
const currentIndex = ref(0)       // 当前聚焦索引
const isHelpVisible = ref(false)  // 帮助层显示状态
```

**核心逻辑**:
1. `onMounted` 时获取所有 `.island-pos` 元素存入 `islands`
2. 监听 `keydown` 事件，根据 `e.key` 分发处理
3. Tab → `currentIndex = (currentIndex + 1) % length`
4. Shift+Tab → `currentIndex = (currentIndex - 1 + length) % length`
5. Enter → 调用 `router.push(getIslandRoute(currentIndex))`
6. Escape → 返回首页 `/home`
7. ? → 切换 `isHelpVisible`

**岛屿路由映射**:
```javascript
const routes = ['/island/music', '/island/novel', '/island/video', '/island/log', '/island/tool']
```

**视觉反馈**:
- 选中岛屿添加 `.island-focused` class（翡翠绿 glow）
- 取消选中时移除

---

## 2. useGestureControl.js

### 技术方案

```
位置: frontend/src/composables/useGestureControl.js
依赖: Vue 3 Touch Events, HomeView.vue
```

**状态**:
```javascript
const touchState = ref({
  startX: 0,
  startY: 0,
  startDistance: 0,  // 用于捏合
  isLongPress: false,
  timeoutId: null
})
```

**手势识别**:

| 手势 | 条件 | 动作 |
|------|------|------|
| 捏合 | touchmove 两指距离变化 > 20px | scale 岛屿 |
| 长按 | touchend 未触发 swipe 且时长 > 500ms | 显示详情卡片 |
| 上滑 | touchend dy < -50px 且 dx < 20px | 返回首页 |
| 双击 | 两次 tap 间隔 < 300ms | 进入岛屿 |

**移动端检测**:
```javascript
const isTouchDevice = matchMedia('(hover: none)').matches
```

**性能优化**:
- 只在移动端启用监听
- `will-change: transform` 用于缩放岛屿
- 使用 `passive: true` 提升滚动性能

---

## 3. useIslandSound.js

### 技术方案

```
位置: frontend/src/composables/useIslandSound.js
依赖: Web Audio API, HomeView.vue
```

**状态**:
```javascript
const audioContext = ref(null)
const audioBuffers = ref({})     // 缓存音效
const isMuted = ref(false)        // 静音状态
const currentSound = ref(null)    // 当前播放音效
```

**音效文件**:
```
public/sounds/
├── music-island.mp3    # 轻柔琴音
├── novel-island.mp3    # 翻书声
├── video-island.mp3    # 播放音效
├── log-island.mp3      # 墨滴声
└── tool-island.mp3     # 机械声
```

**核心逻辑**:

1. **初始化** (`initAudioContext`):
   ```javascript
   audioContext.value = new (window.AudioContext || window.webkitAudioContext)()
   ```

2. **预加载** (`preloadSounds`):
   ```javascript
   for (const [key, url] of Object.entries(soundUrls)) {
     const response = await fetch(url)
     const arrayBuffer = await response.arrayBuffer()
     const audioBuffer = await audioContext.value.decodeAudioData(arrayBuffer)
     audioBuffers.value[key] = audioBuffer
   }
   ```

3. **播放** (`playSound`):
   ```javascript
   const source = audioContext.value.createBufferSource()
   source.buffer = audioBuffers.value[key]
   source.connect(audioContext.value.destination)
   source.start()
   ```

4. **hover 触发** (`setupHoverSounds`):
   - 每个岛屿添加 `@mouseenter` 监听
   - 调用 `playSound(islandType)`
   - 使用防抖避免频繁触发

**静音持久化**:
- 使用 `localStorage.getItem('sound-muted')`
- 静音按钮 UI: 顶栏音控按钮旁边

---

## 4. HomeView.vue 集成

### 模板修改

```vue
<!-- 键盘导航 -->
<template>
  <div class="home-page" @keydown="handleKeydown" tabindex="0">
    <!-- 现有内容 -->
  </div>
</template>

<!-- 音效 -->
<template>
  <!-- 添加音效控制按钮 -->
  <button class="sound-toggle" @click="toggleSound">
    {{ isMuted ? '🔇' : '🔊' }}
  </button>
</template>
```

### 脚本导入

```javascript
import { useKeyboardNavigation } from '@/composables/useKeyboardNavigation'
import { useGestureControl } from '@/composables/useGestureControl'
import { useIslandSound } from '@/composables/useIslandSound'

const { setupKeyboardNav, cleanup: cleanupKeyboard } = useKeyboardNavigation()
const { setupGestures, cleanup: cleanupGestures } = useGestureControl()
const { setupHoverSounds, toggleSound, isMuted, cleanup: cleanupSound } = useIslandSound()

onMounted(() => {
  setupKeyboardNav()
  setupGestures()
  setupHoverSounds()
})

onUnmounted(() => {
  cleanupKeyboard()
  cleanupGestures()
  cleanupSound()
})
```

---

## 5. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Web Audio API 在移动端兼容性 | 低 | 检测不支持时静默跳过 |
| 手势误触发 | 中 | 设置合理阈值（捏合>20px，上滑<-50px） |
| 音效文件加载慢 | 中 | 预加载 + loading 状态 |
| 键盘导航与浏览器快捷键冲突 | 低 | 使用自定义逻辑，不拦截系统快捷键 |

---

## 6. 文件清单

| 操作 | 文件路径 |
|------|----------|
| 新增 | `frontend/src/composables/useKeyboardNavigation.js` |
| 新增 | `frontend/src/composables/useGestureControl.js` |
| 新增 | `frontend/src/composables/useIslandSound.js` |
| 新增 | `public/sounds/` (音效文件) |
| 修改 | `frontend/src/views/HomeView.vue` |
| 修改 | `frontend/src/assets/styles/variables.css` (如需新增音效图标色板) |

---

**文档状态**: 技术方案设计完成，待开发