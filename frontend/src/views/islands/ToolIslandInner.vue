<template>
  <IslandInnerBase
    type="tool"
    title="工具岛 · 机关百变"
    subtitle="匠心独运，妙用无穷"
    @back="$emit('back')"
  >
    <div class="tool-content">
      <!-- 齿轮机关装饰 -->
      <div class="gears-decoration">
        <div class="gear" v-for="i in 6" :key="i" :class="`gear-${i}`"></div>
      </div>

      <!-- 零件悬浮 -->
      <div class="parts-floating">
        <div v-for="i in 10" :key="i" class="part" :style="getPartStyle(i)"></div>
      </div>

      <!-- 工具列表 -->
      <div class="tool-list-area">
        <div v-if="toolStore.loading" class="loading-state">
          <span class="loading-text">洞天正在解锁机关...</span>
        </div>
        <div v-else-if="!toolStore.items || toolStore.items.length === 0" class="empty-state">
          <span class="empty-icon">⚙️</span>
          <span class="empty-text">暂无机关启用，静待天机显现</span>
        </div>
        <div v-else class="tool-items">
          <div
            v-for="(item, index) in toolStore.items"
            :key="item.id"
            class="tool-item"
            :style="getItemStyle(index)"
          >
            <div class="tool-icon">
              <span>{{ getToolIcon(item.type) }}</span>
            </div>
            <div class="tool-info">
              <span class="tool-name">{{ item.name || '无名工具' }}</span>
              <span class="tool-desc">{{ item.description || '暂无描述' }}</span>
            </div>
            <div class="tool-status">
              <span class="status-dot" :class="{ active: item.enabled }"></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { onMounted } from 'vue'
import IslandInnerBase from './IslandInnerBase.vue'
import { useToolStore } from '@/stores/tool'

defineEmits(['back'])

const toolStore = useToolStore()

onMounted(async () => {
  await toolStore.fetchList()
})

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getPartStyle = (i) => {
  const seed = i * 5678.901
  const random = seededRandom(seed)

  return {
    left: `${random * 100}%`,
    top: `${10 + seededRandom(seed * 2) * 60}%`,
    width: `${8 + random * 16}px`,
    height: `${8 + random * 16}px`,
    animationDelay: `${random * 6}s`,
    opacity: 0.2 + random * 0.3,
    borderRadius: random > 0.5 ? '50%' : '2px',
    transform: `rotate(${random * 360}deg)`
  }
}

const getItemStyle = (index) => {
  const seed = index * 6789.012
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 0.3}s`
  }
}

const getToolIcon = (type) => {
  const icons = {
    generator: '⚡',
    converter: '🔄',
    analyzer: '📊',
    utility: '🔧',
    other: '🎛️'
  }
  return icons[type] || '🔧'
}
</script>

<style scoped>
.tool-content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.gears-decoration {
  position: absolute;
  top: 10%;
  left: 5%;
  width: 250px;
  height: 200px;
  pointer-events: none;
}

.gear {
  position: absolute;
  border: 3px solid var(--island-tool);
  border-radius: 50%;
  opacity: 0.2;
}

.gear-1 {
  width: 100px;
  height: 100px;
  top: 20%;
  left: 10%;
  animation: rotate-gear 12s linear infinite;
}

.gear-2 {
  width: 70px;
  height: 70px;
  top: 50%;
  left: 45%;
  animation: rotate-gear 9s linear infinite reverse;
}

.gear-3 {
  width: 55px;
  height: 55px;
  top: 10%;
  right: 20%;
  animation: rotate-gear 8s linear infinite;
}

.gear-4 {
  width: 45px;
  height: 45px;
  bottom: 20%;
  left: 30%;
  animation: rotate-gear 7s linear infinite reverse;
}

.gear-5 {
  width: 35px;
  height: 35px;
  bottom: 30%;
  right: 15%;
  animation: rotate-gear 6s linear infinite;
}

.gear-6 {
  width: 50px;
  height: 50px;
  top: 35%;
  left: 60%;
  animation: rotate-gear 10s linear infinite reverse;
}

@keyframes rotate-gear {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.parts-floating {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.part {
  position: absolute;
  background: var(--island-tool);
  animation: float-part 10s ease-in-out infinite;
  will-change: transform, opacity;
}

@keyframes float-part {
  0%, 100% {
    transform: translateY(0) rotate(var(--rotate, 0deg));
    opacity: 0.3;
  }
  50% {
    transform: translateY(-30px) rotate(calc(var(--rotate, 0deg) + 180deg));
    opacity: 0.6;
  }
}

.tool-list-area {
  background: var(--color-bg-elevated);
  border: 1px solid rgba(196, 154, 108, 0.2);
  border-radius: var(--radius);
  padding: 30px;
  min-height: 300px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
}

.loading-text,
.empty-text {
  color: var(--color-text-muted);
  font-size: 14px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.5;
}

.tool-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
  background: rgba(196, 154, 108, 0.05);
  border: 1px solid rgba(196, 154, 108, 0.15);
  border-radius: var(--radius-sm);
  transition: all var(--transition);
  animation: slide-in 0.5s ease-out backwards;
  cursor: pointer;
}

.tool-item:hover {
  background: rgba(196, 154, 108, 0.1);
  border-color: rgba(196, 154, 108, 0.3);
  transform: translateX(8px);
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.tool-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(
    135deg,
    var(--island-tool) 0%,
    rgba(196, 154, 108, 0.3) 100%
  );
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.tool-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.tool-name {
  font-family: var(--font-serif);
  color: var(--color-text);
  font-size: 16px;
}

.tool-desc {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.tool-status {
  display: flex;
  align-items: center;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-text-muted);
  transition: all var(--transition);
}

.status-dot.active {
  background: var(--color-success);
  box-shadow: 0 0 10px var(--color-success);
}
</style>