<template>
  <IslandInnerBase type="tool" title="摸鱼日历" subtitle="离下班/周末/假期还有多久 · 今日宜忌">
    <div class="fish-tool">
      <div v-if="!data && !error" class="ft-loading">加载中…</div>
      <div v-if="error" class="ft-err">{{ error }}</div>

      <template v-if="data">
        <!-- 今日头部 -->
        <div class="ft-hero glass-card">
          <div class="ft-hero-left">
            <div class="ft-date">{{ data.date }} 周{{ data.weekday }}</div>
            <div class="ft-main">{{ data.days_to_saturday === 0 ? '今天就是周六！' : `距周六还有 ${data.days_to_saturday} 天` }}</div>
          </div>
          <div class="ft-hero-right">
            <div class="ft-week-label">本周进度</div>
            <div class="ft-week-bar"><i :style="{ width: data.week_progress + '%' }"></i></div>
            <div class="ft-week-pct">{{ data.week_progress }}%</div>
          </div>
        </div>

        <!-- 宜忌 -->
        <div class="ft-yiji">
          <div class="ft-yi glass-card">
            <div class="ft-yiji-label yi">宜</div>
            <div class="ft-yiji-text">{{ data.yi }}</div>
          </div>
          <div class="ft-yi glass-card">
            <div class="ft-yiji-label ji">忌</div>
            <div class="ft-yiji-text">{{ data.ji }}</div>
          </div>
        </div>

        <!-- 假期倒计时 -->
        <div class="ft-holidays">
          <div class="ft-sec-title">假期倒计时</div>
          <div v-for="h in data.holidays" :key="h.name" class="ft-holiday">
            <span class="ft-h-name">{{ h.name }}</span>
            <span class="ft-h-date">{{ h.date }}</span>
            <span class="ft-h-days" :class="{ hot: h.days_left <= 7 }">
              {{ h.days_left === 0 ? '就是今天' : `还有 ${h.days_left} 天` }}
            </span>
          </div>
        </div>
        <div class="ft-note">{{ data.note }}</div>
      </template>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { fishCalendar } from '@/api/toolkit'

const data = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    const body = await fishCalendar()
    data.value = body?.data || null
  } catch (e) {
    error.value = e?.response?.data?.detail || '加载失败'
  }
})
</script>

<style scoped>
.ft-loading, .ft-err { text-align: center; padding: 30px; color: var(--dp-text3, #8a8f98); font-size: 13px; }
.ft-err { color: #e5484d; }
.ft-hero { display: flex; justify-content: space-between; align-items: center; padding: 22px 24px; gap: 18px; flex-wrap: wrap; }
.ft-date { font-size: 13px; color: var(--dp-text3, #8a8f98); }
.ft-main { margin-top: 6px; font-size: 22px; font-weight: 800; color: var(--dp-text, #18202a); }
.ft-hero-right { min-width: 180px; }
.ft-week-label { font-size: 12px; color: var(--dp-text3, #8a8f98); }
.ft-week-bar { margin-top: 6px; height: 8px; border-radius: 999px; background: var(--dp-bg2, rgba(0,0,0,.06)); overflow: hidden; }
.ft-week-bar i { display: block; height: 100%; background: linear-gradient(90deg, var(--yq-gold, #c7a96b), var(--yq-gold-bright, #f59e0b)); border-radius: 999px; }
.ft-week-pct { margin-top: 4px; font-size: 12px; color: var(--yq-gold, #c7a96b); font-weight: 700; text-align: right; }
.ft-yiji { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 14px; }
.ft-yi { display: flex; align-items: center; gap: 14px; padding: 16px 18px; }
.ft-yiji-label {
  flex: none; width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 800; color: #fff;
}
.ft-yiji-label.yi { background: #1aa86a; }
.ft-yiji-label.ji { background: #e5484d; }
.ft-yiji-text { font-size: 14.5px; color: var(--dp-text, #18202a); line-height: 1.6; }
.ft-holidays { margin-top: 18px; }
.ft-sec-title { font-size: 13px; color: var(--dp-text3, #8a8f98); margin-bottom: 8px; letter-spacing: .05em; }
.ft-holiday {
  display: flex; align-items: center; gap: 14px; padding: 11px 14px; border-radius: 10px;
  border-bottom: 1px solid var(--dp-line, rgba(0,0,0,.06));
}
.ft-h-name { font-weight: 600; font-size: 14px; color: var(--dp-text, #18202a); width: 90px; }
.ft-h-date { font-size: 13px; color: var(--dp-text3, #8a8f98); flex: 1; }
.ft-h-days { font-size: 13.5px; font-weight: 700; color: var(--dp-text2, #45505b); }
.ft-h-days.hot { color: #e5484d; }
.ft-note { margin-top: 12px; font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
</style>
