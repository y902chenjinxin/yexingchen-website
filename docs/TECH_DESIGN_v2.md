# TECH_DESIGN_v2.0.md - 技术设计方案

> 修仙仙府 v2.0 - "天人合一"完整技术实现方案
> 版本: v2.0
> 日期: 2026-05-29

---

## 1. 整体架构

### 1.1 前端架构调整

```
frontend/src/
├── components/
│   ├── layers/                    # 【景】五层背景
│   │   ├── SkyLayer.vue         # 天穹层
│   │   ├── MountainLayer.vue     # 远山层
│   │   ├── QiLayer.vue          # 灵气层
│   │   ├── CloudLayer.vue        # 云海层
│   │   └── MistLayer.vue         # 薄雾层
│   ├── particles/                 # 粒子系统
│   │   ├── ParticleCanvas.vue    # 粒子画布
│   │   ├── CursorTrail.vue       # 鼠标轨迹
│   │   ├── GodRay.vue            # 丁达尔光柱
│   │   └── Meteor.vue            # 流星
│   ├── islands/                   # 岛屿系统
│   │   ├── IslandOrbit.vue        # 公转容器
│   │   ├── IslandCard.vue        # 岛屿卡片（含灵物）
│   │   └── IslandSpirit.vue      # 岛屿精灵（音效/动效）
│   ├── transition/                # 转场系统
│   │   └── InkTransition.vue      # 砚台转场
│   └── common/
│       ├── DaoName.vue           # 道号显示
│       ├── CultivationProgress.vue # 修为进度
│       └── RealmSelector.vue     # 今文/古文切换
├── composables/                   # 组合式函数
│   ├── useParticleSystem.js      # 粒子系统
│   ├── useAudioReactive.js        # 音频驱动
│   ├── useBreathCycle.js          # 呼吸节奏
│   ├── useGracefulDegrade.js      # 性能降级
│   ├── useCelestialSystem.js      # 天象系统
│   └── useKeyboardNavigation.js   # 键盘导航
├── shaders/                       # WebGL shaders
│   ├── bloom.glsl
│   ├── chromatic.glsl
│   └── godray.glsl
└── views/
    ├── HomeView.vue              # 重构为调度中心
    ├── MusicIslandInner.vue      # 音乐岛内景
    ├── NovelIslandInner.vue      # 小说岛内景
    ├── VideoIslandInner.vue      # 视频岛内景
    ├── LogIslandInner.vue        # 日志岛内景
    ├── ToolIslandInner.vue       # 工具岛内景
    └── CultivationChronicle.vue  # 修炼编年史
```

---

## 2. CSS变量体系（14维度）

### 2.1 核心色系

```css
:root {
  /* ========== 玄墨底色 ========== */
  --color-bg-dark: #0D0F14;
  --color-bg: #12141A;
  --color-bg-elevated: #1A1D24;
  --color-bg-glass: rgba(18, 20, 26, 0.85);
  --color-ink-deep: #0A0C12;

  /* ========== 古铜金系 ========== */
  --color-gold: #C9A86C;
  --color-gold-light: rgba(201, 168, 108, 0.4);
  --color-gold-dark: #8B7355;
  --color-gold-glow: 0 0 30px rgba(201, 169, 98, 0.3);

  /* ========== 灵气色 ========== */
  --color-qi-primary: #4A7C59;
  --color-qi-glow: rgba(74, 124, 89, 0.4);

  /* ========== 岛屿专属色 ========== */
  --island-music: #9B8DC9;
  --island-music-glow: rgba(155, 141, 201, 0.5);
  --island-novel: #D4C4A8;
  --island-novel-glow: rgba(212, 196, 168, 0.5);
  --island-video: #A87C9C;
  --island-video-glow: rgba(168, 124, 156, 0.5);
  --island-log: #7A9B7C;
  --island-log-glow: rgba(122, 155, 124, 0.5);
  --island-tool: #C49A6C;
  --island-tool-glow: rgba(196, 154, 108, 0.5);

  /* ========== 文字色 ========== */
  --color-text: #E8E4DC;
  --color-text-secondary: #9A968E;
  --color-text-muted: #6A665E;
}
```

### 2.2 【景】五层背景变量

```css
:root {
  /* 层透明度 */
  --layer-1-opacity: 0.3;    /* 天穹 */
  --layer-2-opacity: 0.5;     /* 远山 */
  --layer-3-opacity: 0.7;     /* 灵气 */
  --layer-4-opacity: 0.9;     /* 云海 */
  --layer-5-opacity: 0.4;     /* 薄雾 */

  /* 层移动速度 */
  --layer-1-speed: 0;
  --layer-2-speed: 0.5s;
  --layer-3-speed: 1s;
  --layer-4-speed: 2s;
  --layer-5-speed: 3s;

  /* 呼吸节奏（4-7-8调息）*/
  --breath-in: 4s;
  --breath-hold: 7s;
  --breath-out: 8s;
  --breath-total: 19s;

  /* 丁达尔光柱 */
  --god-ray-color: rgba(201, 169, 98, 0.4);
  --god-ray-count: 4;
  --god-ray-particle-opacity: 0.5;
  --god-ray-animation-duration: 8s;

  /* 云海 */
  --cloud-color-base: var(--color-gold);
  --cloud-animation-duration: 25s;
}
```

### 2.3 【光】shader效果变量

```css
:root {
  /* Bloom辉光 */
  --bloom-intensity: 0.6;
  --bloom-threshold: 0.8;
  --bloom-radius: 20px;

  /* 色差 */
  --chromatic-offset: 2px;
  --chromatic-red: rgba(255, 0, 0, 0.5);
  --chromatic-blue: rgba(0, 255, 255, 0.5);

  /* 玉石光感 */
  --jade-glow-intensity: 0.3;
  --jade-breathe-duration: 6s;

  /* 景深 */
  --dof-near-blur: 0px;
  --dof-far-blur: 8px;
  --dof-focus-distance: 50%;
}
```

### 2.4 【转场】砚台变量

```css
:root {
  /* 墨韵转场 */
  --ink-transition-easing: cubic-bezier(0.65, 0, 0.35, 1);
  --ink-duration: 0.8s;
  --ink-color: var(--color-ink-deep);
  --ink-corner-size: 100px;

  /* 入场动画时序 */
  --entrance-phase-1: 0s;      /* 墨色渐显 */
  --entrance-phase-2: 1s;      /* 灵气涌动 */
  --entrance-phase-3: 2s;       /* 阵法浮现 */
  --entrance-phase-4: 3s;       /* 岛屿凝聚 */
  --entrance-phase-5: 5s;       /* 顶栏淡入 */
}
```

### 2.5 【时】天象变量

```css
:root {
  /* 十二时辰背景 */
  --color-bg-theme-0: #0A0C12;   /* 子时 */
  --color-bg-theme-1: #0C0E16;   /* 丑时 */
  --color-bg-theme-2: #100E10;   /* 寅时 */
  --color-bg-theme-3: #12100A;   /* 卯时 */
  --color-bg-theme-4: #0D0F14;   /* 辰时 */
  --color-bg-theme-5: #12141A;   /* 巳时 */
  --color-bg-theme-6: #0E1018;   /* 午时 */
  --color-bg-theme-7: #100C14;   /* 未时 */
  --color-bg-theme-8: #0C1018;   /* 申时 */
  --color-bg-theme-9: #0A0E14;   /* 酉时 */
  --color-bg-theme-10: #0C0E18;  /* 戌时 */
  --color-bg-theme-11: #080A10;   /* 亥时 */

  /* 岛屿光晕 */
  --color-glow-theme-0: rgba(201,169,98,0.35);
  --color-glow-theme-1: rgba(74,124,89,0.3);
  /* ... 省略其他时辰 */

  /* 节气特效 */
  --solar-term-intensity: 1;
  --solar-term-spring: 0.8;      /* 春分 */
  --solar-term-summer: 1.2;      /* 夏至 */
  --solar-term-autumn: 1.0;      /* 秋分 */
  --solar-term-winter: 0.9;      /* 冬至 */
}
```

### 2.6 【感】交互变量

```css
:root {
  /* 鼠标灵气轨迹 */
  --cursor-trail-color: rgba(201, 169, 98, 0.6);
  --cursor-trail-lifetime: 1200ms;
  --cursor-trail-max-particles: 30;

  /* 岛屿hover效果 */
  --island-hover-scale: 1.05;
  --island-hover-translate: -20px;
  --island-hover-glow: 30px;
  --island-hover-duration: 0.4s;

  /* 灵气共鸣波纹 */
  --ripple-color: var(--color-gold);
  --ripple-duration: 0.6s;
  --ripple-max-scale: 3;

  /* 手势反馈 */
  --gesture-feedback-duration: 0.3s;
}
```

### 2.7 【包】包容性变量

```css
:root {
  /* 性能降级阈值 */
  --perf-high-tier: 8;           /* 8核以上全开 */
  --perf-mid-tier: 4;           /* 4核减少粒子 */
  --perf-low-tier: 2;            /* 2核仅静态 */

  /* 无障碍 */
  --focus-outline: 2px solid var(--color-gold);
  --focus-outline-offset: 2px;

  /* 高对比模式 */
  --high-contrast-bg: #FFFFFF;
  --high-contrast-text: #000000;
  --high-contrast-accent: var(--color-gold);
}
```

---

## 3. 核心组件设计

### 3.1 粒子系统 (ParticleCanvas.vue)

```javascript
// useParticleSystem.js
export function useParticleSystem(canvasRef, options = {}) {
  const {
    particleCount = 50,
    colors = ['--color-gold', '--color-qi-primary'],
    lifetime = 2000,
    speed = 1,
    size = 3,
    blendMode = 'screen'
  } = options;

  // 种子随机（保证连贯性）
  const seededRandom = (seed) => {
    return Math.abs(Math.sin(seed * 12.9898) * 43758.5453) % 1;
  };

  // 性能降级：粒子数量自动调整
  const adjustParticleCount = () => {
    const cores = navigator.hardwareConcurrency || 4;
    if (cores >= 8) return particleCount;
    if (cores >= 4) return Math.floor(particleCount * 0.5);
    return Math.floor(particleCount * 0.25);
  };

  // 渲染循环（requestAnimationFrame）
  const render = (timestamp) => {
    // 清除画布
    ctx.clearRect(0, 0, width, height);

    // 更新粒子位置
    particles.forEach((p, i) => {
      p.x += p.vx * speed;
      p.y += p.vy * speed;
      p.life -= deltaTime;

      // 绘制
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * (p.life / p.maxLife), 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.fill();
    });

    // 离屏预渲染优化
    if (worker) {
      offscreenCanvas.transferToImageBitmap();
    }
  };

  return { init, pause, resume, setIntensity };
}
```

### 3.2 入场动画系统

```javascript
// useEntranceAnimation.js
export function useEntranceAnimation() {
  const phases = [
    { name: 'ink-appear', duration: 1000, start: 0 },
    { name: 'qi-flow', duration: 1500, start: 1000 },
    { name: 'symbols-appear', duration: 1000, start: 2500 },
    { name: 'islands-materialize', duration: 2000, start: 3500 },
    { name: 'topbar-fadein', duration: 1000, start: 5000 }
  ];

  const runEntrance = async () => {
    for (const phase of phases) {
      await delay(phase.start);
      document.body.classList.add(`entrance-${phase.name}`);

      // CSS变量控制
      document.documentElement.style.setProperty(
        `--entrance-progress`,
        phases.indexOf(phase) / phases.length
      );
    }
  };

  return { runEntrance, phases };
}
```

### 3.3 音频驱动视觉

```javascript
// useAudioReactive.js
export function useAudioReactive(audioElement) {
  let analyser;
  let dataArray;

  const init = () => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;

    const source = audioContext.createMediaElementSource(audioElement);
    source.connect(analyser);
    analyser.connect(audioContext.destination);

    dataArray = new Uint8Array(analyser.frequencyBinCount);
  };

  const getFrequencyData = () => {
    analyser.getByteFrequencyData(dataArray);

    // 低频 → 岛屿呼吸
    const lowFreq = dataArray.slice(0, 8).reduce((a, b) => a + b) / 8;
    // 高频 → 粒子密度
    const highFreq = dataArray.slice(8, 32).reduce((a, b) => a + b) / 24;

    return {
      low: lowFreq / 255,
      high: highFreq / 255
    };
  };

  // 应用到CSS变量
  const applyToCSS = () => {
    const { low, high } = getFrequencyData();
    document.documentElement.style.setProperty('--island-breathe', 0.8 + low * 0.4);
    document.documentElement.style.setProperty('--particle-density', 0.5 + high * 0.5);
    requestAnimationFrame(applyToCSS);
  };

  return { init, getFrequencyData };
}
```

---

## 4. 性能降级策略

### 4.1 分级降级

```javascript
// useGracefulDegrade.js
export function useGracefulDegrade() {
  const getDeviceTier = () => {
    const cores = navigator.hardwareConcurrency || 4;
    const memory = navigator.deviceMemory || 4;
    const saveData = navigator.connection?.saveData || false;

    // 检测帧率（前三帧平均）
    const fps = getInitialFPS();

    if (saveData || memory < 4 || cores < 2) return 'low';
    if (fps < 30 || cores < 4) return 'mid';
    return 'high';
  };

  const featureFlags = {
    high: {
      particleSystem: true,
      godRays: true,
      audioReactive: true,
      cursorTrail: true,
      shaders: true,
      complexAnimations: true
    },
    mid: {
      particleSystem: true,
      godRays: false,
      audioReactive: true,
      cursorTrail: true,
      shaders: false,
      complexAnimations: true
    },
    low: {
      particleSystem: false,
      godRays: false,
      audioReactive: false,
      cursorTrail: false,
      shaders: false,
      complexAnimations: false
    }
  };

  return { getDeviceTier, getFeatureFlags: (tier) => featureFlags[tier] };
}
```

### 4.2 Shader降级链

```javascript
const shaderFallback = () => {
  if (typeof WebGL2RenderingContext !== 'undefined') {
    // 使用WebGL2 shader
    return new ShaderRenderer();
  } else if (typeof CanvasRenderingContext2D !== 'undefined') {
    // 降级到Canvas 2D多层叠加
    return new Canvas2DRenderer();
  } else {
    // 最终降级：CSS渐变
    return new CSSGradientFallback();
  }
};
```

---

## 5. 后端变更（如有）

### 5.1 新增API（仅用于存储用户数据）

| 端点 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/v1/settings/cultivation` | GET/PUT | 用户修为数据 | 需要 |
| `/api/v1/settings/dao_name` | GET | 获取/生成道号 | 需要 |

### 5.2 数据模型变更

```python
# backend/app/models/user.py (扩展)
class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    dao_name = Column(String(50))              # 道号
    cultivation_points = Column(Integer, default=0)  # 修为点
    spirit_stones = Column(Integer, default=0)  # 灵石
    last_visit = Column(DateTime)
    total_visits = Column(Integer, default=0)

    # 五岛探索状态
    music_explored = Column(Boolean, default=False)
    novel_explored = Column(Boolean, default=False)
    video_explored = Column(Boolean, default=False)
    log_explored = Column(Boolean, default=False)
    tool_explored = Column(Boolean, default=False)
```

**注意**: 所有用户数据存储在本地localStorage，后端无需存储。如需持久化，可扩展此模型。

---

## 6. 动画时序表

### 6.1 入场动画（命轮渐显）

| 阶段 | 时间 | 效果 | CSS类 |
|------|------|------|-------|
| Phase 1 | 0-1s | 墨色从无到有凝聚 | `.entrance-ink-appear` |
| Phase 2 | 1-2.5s | 灵气从中心涌动成形 | `.entrance-qi-flow` |
| Phase 3 | 2.5-3.5s | 阵法符文浮现 | `.entrance-symbols-appear` |
| Phase 4 | 3.5-5.5s | 岛屿依次从灵气中凝聚 | `.entrance-islands-materialize` |
| Phase 5 | 5-6s | 顶栏+装饰粒子淡入 | `.entrance-topbar-fadein` |

### 6.2 岛屿公转

```css
@keyframes orbit-around {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 各岛屿相位差 - 呼吸不同步 */
.island-pos:nth-child(1) .island {
  animation: island-breathe 8s ease-in-out infinite;
}
.island-pos:nth-child(2) .island {
  animation: island-breathe 9s ease-in-out infinite 1s;
}
.island-pos:nth-child(3) .island {
  animation: island-breathe 7s ease-in-out infinite 2s;
}
/* ... 以此类推，相位差2-3秒 */
```

### 6.3 鼠标灵气轨迹

```javascript
// 轨迹粒子生命周期
const particleLifecycle = {
  birth: { opacity: 0.8, scale: 1 },
  peak: { opacity: 0.6, scale: 1.2, time: 0.3 },  // 30%生命周期
  death: { opacity: 0, scale: 0.5, time: 1.2 }    // 1200ms后消失
};
```

---

## 7. 文件清单

### Phase 1 必做文件

```
frontend/src/
├── assets/styles/variables.css          # 扩展CSS变量
├── composables/
│   ├── useParticleSystem.js
│   ├── useEntranceAnimation.js
│   ├── useBreathCycle.js
│   └── useGracefulDegrade.js
├── components/
│   ├── layers/
│   │   ├── SkyLayer.vue
│   │   ├── MountainLayer.vue
│   │   ├── QiLayer.vue
│   │   ├── CloudLayer.vue
│   │   └── MistLayer.vue
│   ├── particles/
│   │   ├── ParticleCanvas.vue
│   │   └── CursorTrail.vue
│   └── transition/
│       └── InkTransition.vue
└── views/
    └── HomeView.vue                    # 重构
```

### Phase 2-3 扩展文件

```
frontend/src/
├── components/
│   ├── particles/
│   │   ├── GodRay.vue
│   │   └── Meteor.vue
│   └── common/
│       ├── DaoName.vue
│       └── CultivationProgress.vue
├── composables/
│   ├── useAudioReactive.js
│   ├── useCelestialSystem.js
│   └── useKeyboardNavigation.js
└── views/
    ├── MusicIslandInner.vue
    ├── NovelIslandInner.vue
    └── ... (其他内景)
```

---

## 8. 测试计划

### 8.1 功能验证清单

| 功能 | 验证操作 | 预期结果 | 优先级 |
|------|---------|---------|--------|
| 五层背景 | 滚动页面观察层次 | 远近分明，呼吸节奏不同 | P0 |
| 粒子系统 | 鼠标移动 | 淡金色粒子跟随，1.2s消失 | P0 |
| 入场动画 | 刷新页面 | 墨色渐显→灵气涌动→岛屿凝聚 | P0 |
| 岛屿hover | 悬停岛屿 | 上浮+光晕+粒子汇聚 | P0 |
| 砚台转场 | 进入内景再返回 | 墨韵转场效果 | P0 |
| 性能降级 | 低配设备访问 | 自动降级，流畅运行 | P1 |
| 键盘导航 | Tab遍历岛屿 | 按方位顺序，焦点金色边框 | P2 |
| 天象系统 | 不同时间访问 | 背景色调随时间变化 | P2 |

### 8.2 性能基准

| 指标 | 高端机 | 中端机 | 低端机 |
|------|--------|--------|--------|
| 首屏加载 | <2s | <3s | <4s |
| FPS | 60 | 30-60 | 20-30 |
| 粒子数量 | 50 | 25 | 0 |
| 内存占用 | <200MB | <150MB | <100MB |

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 粒子系统性能 | 低端机卡顿 | 自动降级，粒子数量可配置 |
| 音频驱动复杂 | 开发周期长 | Phase 1先不做，Phase 2再引入 |
| 多个内景页面 | 工作量大 | 复用模板，仅变更内容 |
| shader兼容性 | 老浏览器崩溃 | 完整降级链：WebGL2→Canvas2D→CSS |

---

**文档状态**: 技术方案完成
**下一步**: 进入 Step 5 开发实施