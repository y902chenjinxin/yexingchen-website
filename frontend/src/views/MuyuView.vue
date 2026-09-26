<template>
  <IslandInnerBase type="tool" title="电子木鱼" subtitle="赛博功德 · 敲一下 +0.1">
    <div class="muyu-tool">
      <div class="my-counter">
        <span class="my-num">{{ countText }}</span>
        <span class="my-unit">功德</span>
      </div>

      <button class="my-drum" :class="{ hit: hitting }" aria-label="敲木鱼" @click="knock">
        <svg viewBox="0 0 200 160" class="my-svg">
          <!-- 木鱼主体 -->
          <ellipse cx="100" cy="105" rx="78" ry="46" fill="#8a5a34" />
          <ellipse cx="100" cy="98" rx="78" ry="46" fill="#a97142" />
          <ellipse cx="100" cy="94" rx="62" ry="34" fill="#b9854f" />
          <ellipse cx="100" cy="92" rx="20" ry="9" fill="#5a3a20" />
          <!-- 木鱼槌 -->
          <g :style="{ transform: hitting ? 'rotate(18deg)' : 'rotate(-8deg)', transformOrigin: '160px 30px', transition: 'transform .07s' }">
            <rect x="156" y="30" width="9" height="66" rx="4" fill="#6b4423" transform="rotate(24 160 30)" />
            <circle cx="128" cy="62" r="15" fill="#7a4e2a" />
            <circle cx="128" cy="62" r="10" fill="#8f5c33" />
          </g>
        </svg>
      </button>

      <div class="my-floating-layer">
        <span v-for="f in floats" :key="f.id" class="my-float" :style="{ left: f.x + '%', top: f.y + 'px' }">+{{ f.inc }} 功德</span>
      </div>

      <div class="my-foot">
        <button class="my-reset" @click="reset">清零重修</button>
        <span class="my-note">计数存在本机浏览器，换设备不同步——功德是自己的。</span>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'

const K = 'muyu_merit'
const count = ref(0)
const hitting = ref(false)
const floats = ref([])
let fid = 0
let audioCtx = null

const countText = computed(() => count.value.toFixed(1))

function knock() {
  count.value += 0.1
  localStorage.setItem(K, String(count.value))
  hitting.value = true
  setTimeout(() => { hitting.value = false }, 70)
  // 漂浮的 +0.1
  const id = ++fid
  floats.value.push({ id, x: 40 + Math.random() * 20, y: 0, inc: '0.1' })
  setTimeout(() => { floats.value = floats.value.filter(f => f.id !== id) }, 900)
  playDuk()
}

function playDuk() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)()
    const o = audioCtx.createOscillator()
    const g = audioCtx.createGain()
    o.type = 'sine'
    o.frequency.setValueAtTime(660, audioCtx.currentTime)
    o.frequency.exponentialRampToValueAtTime(180, audioCtx.currentTime + 0.08)
    g.gain.setValueAtTime(0.4, audioCtx.currentTime)
    g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.12)
    o.connect(g); g.connect(audioCtx.destination)
    o.start(); o.stop(audioCtx.currentTime + 0.13)
  } catch { /* 静音环境忽略 */ }
}

function reset() {
  count.value = 0
  localStorage.setItem(K, '0')
}

onMounted(() => { count.value = parseFloat(localStorage.getItem(K) || '0') || 0 })
</script>

<style scoped>
.muyu-tool { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 10px 0 20px; }
.my-counter { display: flex; align-items: baseline; gap: 8px; }
.my-num { font-size: 40px; font-weight: 800; color: var(--yq-gold, #c7a96b); font-variant-numeric: tabular-nums; }
.my-unit { font-size: 14px; color: var(--dp-text3, #8a8f98); }
.my-drum { width: 210px; background: transparent; border: none; cursor: pointer; padding: 0; user-select: none; -webkit-tap-highlight-color: transparent; }
.my-drum:active .my-svg { transform: scale(.97); }
.my-svg { width: 100%; display: block; filter: drop-shadow(0 6px 14px rgba(0,0,0,.18)); }
.my-floating-layer { position: relative; width: 210px; height: 0; }
.my-float {
  position: absolute; font-size: 13px; color: var(--yq-gold, #c7a96b); font-weight: 700;
  animation: floatUp .9s ease-out forwards; white-space: nowrap;
}
@keyframes floatUp { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(-46px); } }
@media (prefers-reduced-motion: reduce) { .my-float { animation: none; opacity: 0; } }
.my-foot { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; justify-content: center; }
.my-reset {
  padding: 6px 16px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text3, #8a8f98);
}
.my-note { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
</style>
