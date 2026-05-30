<template>
  <div class="cultivation-chronicle" v-if="isVisible">
    <div class="chronicle-container">
      <header class="chronicle-header">
        <h1>📜 修炼编年史</h1>
        <p class="chronicle-subtitle">叶兴辰的修仙之路</p>
        <button class="close-btn" @click="close">×</button>
      </header>

      <div class="timeline">
        <div
          v-for="(entry, index) in chronicleEntries"
          :key="index"
          class="timeline-entry"
        >
          <div class="entry-marker">
            <div class="marker-circle" :style="{ background: entry.color }"></div>
            <div class="marker-line" v-if="index < chronicleEntries.length - 1"></div>
          </div>

          <div class="entry-content">
            <div class="entry-year">{{ entry.year }}</div>
            <div class="entry-season">{{ entry.season }}</div>
            <h3 class="entry-title">{{ entry.title }}</h3>
            <p class="entry-description">{{ entry.description }}</p>
            <div class="entry-artifact">
              <span class="artifact-icon">{{ entry.icon }}</span>
              <span class="artifact-name">{{ entry.artifact }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="chronicle-footer">
        <p>道法自然 · 修行无止境</p>
        <button class="exit-btn" @click="close">归隐</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const isVisible = computed(() => props.visible)

// 修炼编年史内容
const chronicleEntries = [
  {
    year: '2025-03',
    season: '春分时节',
    title: '灵根初现',
    description: '首次创建个人网站，踏上修仙之路。选用Vue3+FastAPI，开启修行之旅。',
    icon: '🌱',
    artifact: '灵根种子',
    color: 'var(--color-jade)'
  },
  {
    year: '2025-05',
    season: '立夏时节',
    title: '筑基初成',
    description: '完成用户系统、文件上传、音视频管理基础功能，修行根基稳固。',
    icon: '🏔️',
    artifact: '筑基丹',
    color: 'var(--color-music)'
  },
  {
    year: '2025-08',
    season: '大暑时节',
    title: '金丹初结',
    description: '玄墨流金设计系统上线，视觉风格完成蜕变。金色与深墨交织，仙气初成。',
    icon: '✨',
    artifact: '金丹',
    color: 'var(--color-gold)'
  },
  {
    year: '2025-10',
    season: '秋分时节',
    title: '元婴化形',
    description: '动态背景系统完成，十二时辰光影变化。岛屿公转动画，仙府初现规模。',
    icon: '🌕',
    artifact: '元婴',
    color: 'var(--color-purple)'
  },
  {
    year: '2026-01',
    season: '小寒时节',
    title: '化神出窍',
    description: 'v1.8.0发布，天人合一境界升级。五层背景、粒子系统、入场动画完整实现。',
    icon: '🌀',
    artifact: '化神期',
    color: 'var(--color-novel)'
  },
  {
    year: '2026-05',
    season: '立夏时节',
    title: '大乘飞升',
    description: 'v2.0全面升级，14维度功能一个版本全部实现。修仙仙府，正式落成。',
    icon: '🚀',
    artifact: '飞升',
    color: 'var(--color-video)'
  }
]

const close = () => {
  emit('close')
}
</script>

<style scoped>
.cultivation-chronicle {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: var(--color-bg-dark);
  overflow-y: auto;
}

.chronicle-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
}

.chronicle-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 50px;
  position: relative;
}

.chronicle-header h1 {
  font-family: var(--font-serif);
  font-size: 36px;
  color: var(--color-gold);
  margin: 0;
}

.chronicle-subtitle {
  color: var(--color-text-secondary);
  font-size: 16px;
  margin: 10px 0 0;
}

.close-btn {
  position: absolute;
  right: 0;
  top: 0;
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: 32px;
  cursor: pointer;
  padding: 0 10px;
}

.close-btn:hover {
  color: var(--color-gold);
}

.timeline {
  position: relative;
}

.timeline-entry {
  display: flex;
  gap: 30px;
  margin-bottom: 40px;
}

.entry-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 30px;
}

.marker-circle {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 15px currentColor;
}

.marker-line {
  width: 2px;
  flex: 1;
  background: linear-gradient(
    to bottom,
    var(--color-gold) 0%,
    transparent 100%
  );
  margin-top: 10px;
}

.entry-content {
  flex: 1;
  padding-bottom: 30px;
}

.entry-year {
  font-size: 14px;
  color: var(--color-gold);
  font-weight: 600;
  margin-bottom: 5px;
}

.entry-season {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 10px;
}

.entry-title {
  font-family: var(--font-serif);
  font-size: 24px;
  color: var(--color-text);
  margin: 0 0 15px;
}

.entry-description {
  color: var(--color-text-secondary);
  font-size: 15px;
  line-height: 1.7;
  margin-bottom: 20px;
}

.entry-artifact {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: rgba(201, 169, 98, 0.1);
  border: 1px solid rgba(201, 169, 98, 0.3);
  border-radius: 20px;
}

.artifact-icon {
  font-size: 18px;
}

.artifact-name {
  font-size: 14px;
  color: var(--color-gold);
}

.chronicle-footer {
  text-align: center;
  padding: 50px 0;
}

.chronicle-footer p {
  font-family: var(--font-serif);
  font-size: 20px;
  color: var(--color-text-muted);
  margin-bottom: 30px;
}

.exit-btn {
  padding: 12px 40px;
  background: transparent;
  border: 1px solid var(--color-gold);
  border-radius: var(--radius);
  color: var(--color-gold);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.exit-btn:hover {
  background: rgba(201, 169, 98, 0.1);
}
</style>