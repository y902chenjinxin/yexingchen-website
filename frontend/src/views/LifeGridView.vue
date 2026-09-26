<template>
  <IslandInnerBase type="tool" title="人生 4000 周" subtitle="一生 ≈ 90 年 × 52 周 · 每周一格">
    <div class="lg-tool">
      <div v-if="!birth" class="lg-setup glass-card">
        <p class="lg-ask">你的出生日期？（只存在本机浏览器，不上传）</p>
        <input v-model="birthInput" type="date" class="lg-date">
        <button class="lg-btn primary" @click="saveBirth">生成我的人生格子</button>
      </div>

      <template v-else>
        <div class="lg-head glass-card">
          <div class="lg-stat">
            <div class="lg-stat-num">{{ livedWeeks.toLocaleString() }}</div>
            <div class="lg-stat-label">已生活的周数</div>
          </div>
          <div class="lg-stat">
            <div class="lg-stat-num">{{ percent }}%</div>
            <div class="lg-stat-label">人生进度（按 90 年）</div>
          </div>
          <div class="lg-stat">
            <div class="lg-stat-num">{{ remainingWeeks.toLocaleString() }}</div>
            <div class="lg-stat-label">剩余格子（乐观估计）</div>
          </div>
          <button class="lg-btn" @click="resetBirth">改生日</button>
        </div>

        <div class="lg-legend">
          <span><i class="dot lived"></i>已度过</span>
          <span><i class="dot current"></i>本周</span>
          <span><i class="dot future"></i>未来</span>
          <span class="lg-decade">每行 = 1 年 · 共 90 行</span>
        </div>

        <div class="lg-grid-wrap">
          <div class="lg-grid">
            <div
              v-for="w in TOTAL"
              :key="w"
              class="lg-cell"
              :class="{ lived: w < livedWeeks, current: w === livedWeeks }"
              :title="`第 ${w} 周 · ${weekLabel(w)}`"
            ></div>
          </div>
        </div>
      </template>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'

const TOTAL = 90 * 52
const birth = ref('')
const birthInput = ref('')
const today = new Date()

const livedWeeks = computed(() => {
  if (!birth.value) return 0
  const b = new Date(birth.value)
  const days = Math.max(0, Math.floor((today - b) / 86400000))
  return Math.min(TOTAL, Math.floor(days / 7))
})
const percent = computed(() => ((livedWeeks.value / TOTAL) * 100).toFixed(1))
const remainingWeeks = computed(() => Math.max(0, TOTAL - livedWeeks.value))

function weekLabel(w) {
  if (!birth.value) return ''
  const d = new Date(new Date(birth.value).getTime() + (w - 1) * 7 * 86400000)
  return d.toISOString().slice(0, 10)
}

function saveBirth() {
  if (!birthInput.value) return
  birth.value = birthInput.value
  localStorage.setItem('lg_birth', birth.value)
}
function resetBirth() {
  birth.value = ''
  localStorage.removeItem('lg_birth')
}
onMounted(() => { birth.value = localStorage.getItem('lg_birth') || '' })
</script>

<style scoped>
.lg-setup { padding: 26px; display: flex; flex-direction: column; gap: 14px; align-items: flex-start; }
.lg-ask { font-size: 14px; color: var(--dp-text2, #45505b); }
.lg-date { padding: 9px 12px; border-radius: 10px; border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text, #18202a); }
.lg-btn {
  padding: 9px 20px; border-radius: 10px; font-size: 13.5px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text, #18202a);
}
.lg-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.lg-head { display: flex; align-items: center; gap: 26px; padding: 16px 20px; flex-wrap: wrap; }
.lg-stat-num { font-size: 24px; font-weight: 800; color: var(--yq-gold, #c7a96b); font-variant-numeric: tabular-nums; }
.lg-stat-label { font-size: 11.5px; color: var(--dp-text3, #8a8f98); margin-top: 2px; }
.lg-head .lg-btn { margin-left: auto; }
.lg-legend { display: flex; gap: 16px; align-items: center; margin: 14px 0 10px; font-size: 12px; color: var(--dp-text3, #8a8f98); }
.lg-legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 4px; vertical-align: -1px; }
.dot.lived { background: #4a5a4a; }
.dot.current { background: var(--yq-gold, #c7a96b); }
.dot.future { background: rgba(0,0,0,.07); }
.lg-decade { margin-left: auto; }
.lg-grid-wrap { overflow-x: auto; padding-bottom: 8px; }
.lg-grid {
  display: grid; grid-template-rows: repeat(90, 13px); grid-auto-flow: column;
  grid-template-columns: repeat(52, 13px); gap: 3px; width: max-content;
}
.lg-cell { width: 13px; height: 13px; border-radius: 3px; background: rgba(0,0,0,.07); }
.lg-cell.lived { background: #4a5a4a; }
.lg-cell.current { background: var(--yq-gold, #c7a96b); box-shadow: 0 0 0 2px rgba(199,169,107,.35); }
</style>
