<template>
  <div class="tt">
    <div v-if="!travels.length" class="tt-empty">
      <span class="tt-e-icon">🗺️</span>
      <span class="tt-e-text">还没有旅行足迹</span>
      <span v-if="canEdit" class="tt-e-hint">点击右上角「记下旅程」，标记走过的地方</span>
      <span v-else class="tt-e-hint">等主人记下第一段旅程</span>
    </div>
    <button
      v-for="t in travels"
      :key="t.id"
      class="tt-card"
      :class="{ on: activeId === t.id }"
      @click="emit('select', t.id)"
    >
      <span v-if="t.cover" class="tt-cover" :style="{ backgroundImage: `url(${t.cover})` }"></span>
      <div class="tt-body">
        <div class="tt-top">
          <span class="tt-title">{{ t.title }}</span>
          <span class="tt-star">{{ "★".repeat(t.star || 0) || '—' }}</span>
        </div>
        <div class="tt-cities">
          <span v-for="(c, i) in t.cities" :key="i" class="tt-city">{{ i > 0 ? ' · ' : '' }}{{ c.city }}</span>
        </div>
        <div class="tt-foot">
          <span class="tt-date">{{ dateRange(t) }}</span>
          <span v-if="t.video" class="tt-badge">🎬</span>
        </div>
      </div>
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  travels: { type: Array, default: () => [] },
  activeId: { type: Number, default: null },
  canEdit: { type: Boolean, default: false }
})
const emit = defineEmits(['select'])

function dateRange(t) {
  const d1 = t.start_date || t.created_at?.slice(0, 10) || ''
  const d2 = t.end_date
  return d2 && d2 !== d1 ? `${d1} ~ ${d2}` : d1
}
</script>

<style scoped>
.tt { display: flex; flex-direction: column; gap: 10px; max-height: 100%; overflow-y: auto; padding: 2px; }
.tt-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 48px 0; color: var(--lj-text-3); }
.tt-e-icon { font-size: 34px; opacity: .7; }
.tt-e-text { font-size: 14px; color: var(--lj-text-2); }
.tt-e-hint { font-size: 12px; }
.tt-card {
  display: block; width: 100%; text-align: left; cursor: pointer; padding: 12px; border-radius: 12px;
  background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); color: var(--lj-text); transition: all .28s; overflow: hidden;
}
.tt-card:hover { border-color: var(--lj-line-strong); transform: translateY(-2px); }
.tt-card.on { border-color: var(--lj-ochre, #C7A96B); box-shadow: 0 0 0 1px var(--lj-ochre, #C7A96B), 0 10px 22px rgba(0,0,0,.28); }
.tt-cover { display: block; height: 90px; border-radius: 8px; margin-bottom: 10px; background-size: cover; background-position: center; opacity: .92; }
.tt-body { display: flex; flex-direction: column; gap: 5px; }
.tt-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.tt-title { font-size: 14px; font-weight: 600; letter-spacing: .03em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tt-star { color: var(--lj-ochre, #C7A96B); font-size: 12px; letter-spacing: 1px; flex: none; }
.tt-cities { font-size: 12px; color: var(--lj-dai, #7FA8A3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tt-foot { display: flex; align-items: center; justify-content: space-between; }
.tt-date { font-size: 11px; color: var(--lj-text-3); }
.tt-badge { font-size: 12px; }
</style>