<template>
  <article v-if="t" class="tdet">
    <div class="tdet-close" @click="emit('close')">✕</div>
    <div v-if="t.cover || t.photos" class="tdet-hero" :style="{ backgroundImage: `url(${t.cover || t.photos[0]})` }"></div>

    <div class="tdet-body">
      <h3 class="tdet-title">{{ t.title }}</h3>
      <div class="tdet-meta">
        <span class="tdet-star">{{ "★".repeat(t.star || 0) || '—' }}</span>
        <span class="tdet-date">{{ dateRange(t) }}</span>
        <span v-for="(g, i) in t.tags" :key="i" class="tdet-tag">{{ g }}</span>
      </div>
      <div class="tdet-cities">
        <span v-for="(c, i) in t.cities" :key="i" class="tdet-city">{{ i > 0 ? ' → ' : '' }}{{ c.city }}</span>
      </div>

      <div v-if="t.summary" class="tdet-summary">{{ t.summary }}</div>

      <video v-if="t.video" :src="t.video" controls :class="t.video.startsWith('http') ? 'tdet-video-out' : 'tdet-video'" class="tdet-video"></video>

      <div class="tdet-md" v-html="mdHtml"></div>

      <div v-if="t.photos && t.photos.length" class="tdet-gallery">
        <img v-for="(p, i) in t.photos" :key="i" :src="p" class="tdet-img" @click="zoom = zoom === p ? '' : p" />
      </div>

      <div v-if="canEdit" class="tdet-actions">
        <button class="tdet-btn ghost" @click="emit('edit', t.id)">编辑</button>
        <button class="tdet-btn danger" @click="emit('remove', t.id)">删除</button>
      </div>
    </div>

    <div v-if="zoom" class="tdet-zoom" @click="zoom = ''">
      <img :src="zoom" alt="" />
    </div>
  </article>
</template>

<script setup>
import { ref, computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps({
  t: { type: Object, required: true },
  canEdit: { type: Boolean, default: false }
})
const emit = defineEmits(['close', 'edit', 'remove'])
const zoom = ref('')
const mdHtml = computed(() => renderMarkdown(props.t?.markdown || ''))

function dateRange(t) {
  const d1 = t.start_date || ''
  const d2 = t.end_date
  return d2 && d2 !== d1 ? `${d1} ~ ${d2}` : d1
}
</script>

<style scoped>
.tdet { position: relative; border-radius: 16px; overflow: hidden; background: var(--lj-glass);
  -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); box-shadow: var(--glass-highlight), var(--glass-shadow); }
.tdet-close { position: absolute; top: 12px; right: 12px; z-index: 5; width: 26px; height: 26px; border-radius: 50%;
  background: rgba(0,0,0,.45); color: #fff; border: none; cursor: pointer; font-size: 13px; }
.tdet-hero { height: 220px; background-size: cover; background-position: center; }
.tdet-body { padding: 18px 20px 24px; }
.tdet-title { margin: 0 0 8px; font-size: 20px; letter-spacing: .06em; color: var(--lj-text); }
.tdet-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 6px; }
.tdet-star { color: var(--lj-ochre, #C7A96B); letter-spacing: 1px; font-size: 13px; }
.tdet-date { font-size: 12px; color: var(--lj-text-3); }
.tdet-tag { font-size: 11px; padding: 2px 9px; border-radius: 999px; border: 1px solid var(--lj-line); color: var(--lj-dai, #7FA8A3); }
.tdet-cities { font-size: 13px; color: var(--lj-dai, #7FA8A3); margin: 4px 0 10px; }
.tdet-summary { font-size: 13.5px; color: var(--lj-text-2); line-height: 1.7; margin-bottom: 10px; }
.tdet-video { width: 100%; max-height: 380px; border-radius: 12px; margin: 8px 0; background: #000; }
.tdet-md { font-size: 14px; line-height: 1.9; color: var(--lj-text); }
.tdet-md :deep(h1), .tdet-md :deep(h2), .tdet-md :deep(h3) { color: var(--lj-text); letter-spacing: .04em; margin: 14px 0 6px; }
.tdet-md :deep(h1) { font-size: 18px; } .tdet-md :deep(h2) { font-size: 16px; } .tdet-md :deep(h3) { font-size: 15px; }
.tdet-md :deep(p) { margin: 6px 0; }
.tdet-md :deep(code) { background: rgba(127,168,163,.12); padding: 1px 5px; border-radius: 4px; font-size: 12.5px; }
.tdet-md :deep(a) { color: var(--lj-dai, #7FA8A3); }
.tdet-md :deep(blockquote) { border-left: 2px solid var(--lj-ochre, #C7A96B); margin: 8px 0; padding-left: 12px; color: var(--lj-text-2); }
.tdet-gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; margin-top: 14px; }
.tdet-img { width: 100%; aspect-ratio: 4/3; object-fit: cover; border-radius: 8px; cursor: zoom-in; }
.tdet-zoom { position: fixed; inset: 0; z-index: 2000; background: rgba(0,0,0,.72); display: flex; align-items: center; justify-content: center; }
.tdet-zoom img { max-width: 88vw; max-height: 86vh; border-radius: 8px; }
.tdet-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.tdet-btn { padding: 8px 18px; border-radius: 999px; border: 1px solid var(--lj-line); background: none; color: var(--lj-text-2); cursor: pointer; font-size: 13px; }
.tdet-btn.danger { color: var(--lj-vermilion, #c23c3c); border-color: rgba(194,60,60,.4); }
</style>