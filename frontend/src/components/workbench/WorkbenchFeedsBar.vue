<template>
  <section class="wfb" @click="$router.push('/feeds')">
    <span class="wfb-badge">📡 资讯</span>
    <div class="wfb-viewport">
      <ul class="wfb-track" :style="{ transform: `translateY(${-idx * rowH}px)` }">
        <li v-for="(it, i) in list" :key="it.id || i" class="wfb-item" :style="{ height: rowH + 'px' }">
          <span class="wfb-dot"></span>
          <span class="wfb-title">{{ it.title }}</span>
        </li>
      </ul>
    </div>
    <span class="wfb-more">查看全部 →</span>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  feeds: { type: Array, default: () => [] }
})

const rowH = 30
const idx = ref(0)
let timer = null

const list = computed(() => {
  const arr = props.feeds || []
  // 至少一条占位，保证轨道不空；空态文案由样式兜底
  return arr.length ? arr : [{ id: 'empty', title: '暂无订阅源，点击前往添加' }]
})

const total = computed(() => list.value.length)

onMounted(() => {
  if (total.value <= 1) return
  timer = setInterval(() => {
    idx.value = (idx.value + 1) % total.value
  }, 3000)
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.wfb {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 18px;
  height: 52px;
  border-radius: 16px;
  cursor: pointer;
  background: var(--lj-glass);
  -webkit-backdrop-filter: var(--lj-glass-blur);
  backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line);
  box-shadow: var(--glass-highlight), var(--glass-shadow);
  color: var(--lj-text);
  overflow: hidden;
  transition: all .28s;
}
.wfb:hover { border-color: var(--lj-line-strong); box-shadow: var(--glass-highlight), 0 8px 22px rgba(0,0,0,.26); }

.wfb-badge {
  flex: none;
  font-size: 13px;
  letter-spacing: .06em;
  color: var(--lj-dai);
  white-space: nowrap;
}

.wfb-viewport {
  flex: 1;
  height: 30px;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(90deg, rgba(0,0,0,0) 0, #000 18px, #000 calc(100% - 18px), rgba(0,0,0,0));
  mask-image: linear-gradient(90deg, rgba(0,0,0,0) 0, #000 18px, #000 calc(100% - 18px), rgba(0,0,0,0));
}
.wfb-track { margin: 0; padding: 0; list-style: none; transition: transform .6s cubic-bezier(.4,0,.2,1); }
.wfb-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--lj-text-2); overflow: hidden; }
.wfb-dot { flex: none; width: 5px; height: 5px; border-radius: 50%; background: var(--lj-ochre); }
.wfb-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.wfb-more { flex: none; font-size: 12px; color: var(--lj-text-2); transition: all .25s; }
.wfb:hover .wfb-more { color: var(--lj-dai); }

@media (max-width: 600px) {
  .wfb { padding: 0 14px; gap: 10px; }
  .wfb-more { display: none; }
}
</style>