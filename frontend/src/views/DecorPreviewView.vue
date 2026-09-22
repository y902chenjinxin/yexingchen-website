<!--
  DecorPreviewView.vue
  玄黄装饰组件预览页 — 仅登录可见（meta.requiresAuth=true）
  - 三个 loader 来源（uiverse.io，MIT License）
  - 三个尺寸：小（按钮内）/ 中（卡片）/ 大（区块）
  - 主题切换：跟随全站 data-theme 同步
  - 用法：登录后访问 /decor-preview
-->
<template>
  <div class="decor-preview">
    <header class="dp-head">
      <div>
        <h1 class="dp-title">装饰组件预览</h1>
        <p class="dp-sub">来自 uiverse.io MIT 协议的 3 个 loader，已按玄黄色系 + 昼夜双套改造</p>
      </div>
      <div class="dp-meta">
        <span class="dp-tag">主题：<b>{{ theme }}</b></span>
        <span class="dp-tag">已选：<b>3</b> 个 loader</span>
      </div>
    </header>

    <section class="dp-grid">
      <!-- 卡片 1：鎏金骰子跳跃 -->
      <article class="dp-card">
        <header>
          <span class="dp-num">01</span>
          <h2>鎏金骰子跳跃（GoldRocker）</h2>
          <span class="dp-from">uiverse / Shoh2008 / cold-walrus-85</span>
        </header>
        <div class="dp-stage">
          <div class="dp-cell dp-cell--small">
            <span class="dp-label">小（按钮内）</span>
            <DecorLoaderGoldRocker :size="44" />
          </div>
          <div class="dp-cell dp-cell--mid">
            <span class="dp-label">中（卡片）</span>
            <DecorLoaderGoldRocker :size="88" />
          </div>
          <div class="dp-cell dp-cell--big">
            <span class="dp-label">大（区块）</span>
            <DecorLoaderGoldRocker :size="132" />
          </div>
        </div>
        <p class="dp-desc">
          主色鎏金 / bar 渐变三档色。适合<strong>节日级</strong>加载场景：工作台驾驶舱刷新、股票详情卡加载。
        </p>
      </article>

      <!-- 卡片 2：雨青矩阵 -->
      <article class="dp-card">
        <header>
          <span class="dp-num">02</span>
          <h2>雨青矩阵（RainMatrix）</h2>
          <span class="dp-from">uiverse / Nawsome / blue-dragon-70</span>
        </header>
        <div class="dp-stage">
          <div class="dp-cell dp-cell--small">
            <span class="dp-label">小</span>
            <DecorLoaderRainMatrix />
          </div>
          <div class="dp-cell dp-cell--mid dp-cell--rain">
            <span class="dp-label">中</span>
            <DecorLoaderRainMatrix />
          </div>
          <div class="dp-cell dp-cell--big dp-cell--rain">
            <span class="dp-label">大</span>
            <DecorLoaderRainMatrix />
          </div>
        </div>
        <p class="dp-desc">
          9 格雨青方块按 4s 周期移动。<strong>克制、克制、克制</strong>。适合 AI 长任务 / 历史页加载 / 数据驾驶舱刷新。
        </p>
      </article>

      <!-- 卡片 3：玉简弹跳 -->
      <article class="dp-card">
        <header>
          <span class="dp-num">03</span>
          <h2>玉简弹跳（JadeBounce）</h2>
          <span class="dp-from">uiverse / alexruix / white-cat-50</span>
        </header>
        <div class="dp-stage">
          <div class="dp-cell dp-cell--small">
            <span class="dp-label">小（按钮内）</span>
            <DecorLoaderJadeBounce />
          </div>
          <div class="dp-cell dp-cell--mid">
            <span class="dp-label">中</span>
            <DecorLoaderJadeBounce />
          </div>
          <div class="dp-cell dp-cell--big">
            <span class="dp-label">大</span>
            <DecorLoaderJadeBounce />
          </div>
        </div>
        <p class="dp-desc">
          鎏金→雨青双色渐变方块 + 投影。适合<strong>行内</strong>加载（按钮内 / 表格行内）。
        </p>
      </article>
    </section>

    <section class="dp-compare">
      <h2>在真实玄黄页面里的应用预览</h2>
      <div class="dp-grid">
        <!-- KPI 卡 -->
        <article class="dp-card dp-card--mock">
          <h3>KPI 卡 loading 状态</h3>
          <div class="dp-mock-kpi">
            <DecorLoaderGoldRocker :size="48" />
            <span>加载中…</span>
          </div>
        </article>
        <!-- 按钮 loading -->
        <article class="dp-card dp-card--mock">
          <h3>按钮 loading 状态</h3>
          <button class="dp-mock-btn">
            <DecorLoaderJadeBounce />
            正在保存…
          </button>
        </article>
        <!-- 区块 loading -->
        <article class="dp-card dp-card--mock">
          <h3>区块 loading 状态</h3>
          <div class="dp-mock-block">
            <DecorLoaderRainMatrix />
            <span>AI 分析中…</span>
          </div>
        </article>
      </div>
    </section>

    <footer class="dp-foot">
      <p>确认喜欢的 loader 后告诉我，我把它接进具体的页面（工作台/历史/股票等）。不喜欢也没关系——只改这 3 个组件就回滚。</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import DecorLoaderGoldRocker from '@/components/decor/DecorLoaderGoldRocker.vue'
import DecorLoaderRainMatrix from '@/components/decor/DecorLoaderRainMatrix.vue'
import DecorLoaderJadeBounce from '@/components/decor/DecorLoaderJadeBounce.vue'

const theme = ref('夜间（默认）')
onMounted(() => {
  // 同步主题文本
  const update = () => {
    const t = document.documentElement.getAttribute('data-theme')
    theme.value = t === 'day' ? '日间' : '夜间（默认）'
  }
  update()
  const obs = new MutationObserver(update)
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
})
</script>

<style scoped>
.decor-preview {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 24px 80px;
}
.dp-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  margin-bottom: 28px;
  flex-wrap: wrap;
}
.dp-title {
  font-family: var(--font-serif, serif);
  font-size: 24px;
  letter-spacing: 0.06em;
  color: var(--color-text, #e8eef2);
  margin: 0 0 6px;
}
.dp-sub {
  font-size: 13px;
  color: var(--color-text-muted, rgba(232, 238, 242, 0.6));
  margin: 0;
}
.dp-meta {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}
.dp-tag {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--color-bg-glass, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
}
.dp-tag b { color: var(--yq-gold, #c7a96b); font-weight: 600; margin-left: 4px; }

.dp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}
.dp-card {
  padding: 24px;
  border-radius: 18px;
  background: var(--color-bg-elevated, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--color-border, rgba(255, 255, 255, 0.08));
  box-shadow: var(--shadow-sm, 0 2px 6px rgba(0, 0, 0, 0.15));
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.dp-card:hover {
  border-color: var(--yq-gold, #c7a96b);
}
.dp-card header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.dp-num {
  font-family: var(--font-serif, serif);
  font-size: 13px;
  color: var(--yq-gold, #c7a96b);
  background: rgba(199, 169, 107, 0.12);
  padding: 2px 8px;
  border-radius: 4px;
}
.dp-card h2 {
  font-family: var(--font-serif, serif);
  font-size: 16px;
  letter-spacing: 0.04em;
  color: var(--color-text, #e8eef2);
  margin: 0;
  flex: 1;
}
.dp-from {
  font-size: 11px;
  color: var(--color-text-muted);
  font-family: var(--font-mono, monospace);
}
.dp-stage {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-around;
  padding: 18px 0;
  margin-bottom: 14px;
  min-height: 100px;
}
.dp-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.dp-label {
  font-size: 10px;
  color: var(--color-text-muted);
  letter-spacing: 0.08em;
}
.dp-desc {
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text-muted, rgba(232, 238, 242, 0.7));
  margin: 0;
  padding-top: 12px;
  border-top: 1px dashed var(--color-border, rgba(255, 255, 255, 0.08));
}
.dp-desc strong { color: var(--yq-gold, #c7a96b); font-weight: 600; }

/* 真实场景对比 */
.dp-compare h2 {
  font-family: var(--font-serif, serif);
  font-size: 16px;
  letter-spacing: 0.04em;
  color: var(--color-text);
  margin: 0 0 16px;
}
.dp-card--mock {
  padding: 18px;
}
.dp-card--mock h3 {
  font-size: 12px;
  color: var(--color-text-muted);
  letter-spacing: 0.08em;
  margin: 0 0 14px;
  text-transform: uppercase;
}
.dp-mock-kpi {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 24px;
  background: var(--color-bg-glass, rgba(255, 255, 255, 0.03));
  border-radius: 14px;
}
.dp-mock-kpi span { font-size: 12px; color: var(--color-text-muted); }
.dp-mock-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  border-radius: 10px;
  border: 1px solid var(--yq-rain, #7fa8a3);
  background: linear-gradient(135deg,
    rgba(127, 168, 163, 0.18),
    rgba(199, 169, 107, 0.12));
  color: var(--color-text, #e8eef2);
  font-size: 13px;
  cursor: not-allowed;
}
.dp-mock-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 30px;
  background: var(--color-bg-glass, rgba(255, 255, 255, 0.03));
  border-radius: 14px;
  min-height: 160px;
  justify-content: center;
}
.dp-mock-block span { font-size: 13px; color: var(--color-text-muted); }

.dp-foot {
  margin-top: 24px;
  padding: 16px 20px;
  border-radius: 12px;
  background: var(--color-bg-glass, rgba(255, 255, 255, 0.04));
  border-left: 3px solid var(--yq-gold, #c7a96b);
}
.dp-foot p {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.7;
}

@media (max-width: 760px) {
  .dp-stage { flex-wrap: wrap; }
  .dp-cell { flex: 0 0 calc(33% - 12px); }
}
</style>