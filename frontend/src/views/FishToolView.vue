<template>
  <IslandInnerBase type="tool" title="摸鱼日历" subtitle="离下班/周末/假期还有多久 · 今日宜忌">
    <div class="fish-tool">
      <div v-if="!data && !error" class="ft-loading">加载中…</div>
      <div v-if="error" class="ft-err">{{ error }}</div>

      <template v-if="data">
        <!-- 今日头部 -->
        <div class="ft-hero glass-card" :class="'is-' + (data.today?.kind || 'workday')">
          <div class="ft-hero-left">
            <div class="ft-date">{{ data.date }} 周{{ data.weekday }}</div>
            <div class="ft-main">{{ heroMain }}</div>
            <div v-if="heroSub" class="ft-sub">{{ heroSub }}</div>
          </div>
          <div class="ft-hero-right">
            <div class="ft-week-label">本周进度</div>
            <div class="ft-week-bar"><i :style="{ width: data.week_progress + '%' }"></i></div>
            <div class="ft-week-pct">{{ data.week_progress }}%</div>
          </div>
        </div>

        <!-- 年度假期统计 -->
        <div class="ft-stats">
          <div class="ft-stat glass-card">
            <div class="ft-stat-num">{{ data.year_off_days ?? '—' }}</div>
            <div class="ft-stat-label">{{ data.year }} 年放假调休（天）</div>
          </div>
          <div class="ft-stat glass-card">
            <div class="ft-stat-num">{{ data.remaining_off_days ?? 0 }}</div>
            <div class="ft-stat-label">今年还剩（天）</div>
          </div>
          <div class="ft-stat glass-card">
            <div class="ft-stat-num">{{ data.days_to_saturday === 0 ? '就是今天' : data.days_to_saturday }}</div>
            <div class="ft-stat-label">{{ data.days_to_saturday === 0 ? '周六' : '距周六（天）' }}</div>
          </div>
        </div>

        <!-- 调休补班提醒 -->
        <div v-if="data.makeup && data.makeup.length" class="ft-makeup glass-card">
          <div class="ft-makeup-icon">⏰</div>
          <div class="ft-makeup-body">
            <div class="ft-makeup-title">
              下一补班：{{ data.makeup[0].date }}（周{{ data.makeup[0].weekday }}）
              <span v-if="data.makeup[0].days_left === 0" class="ft-makeup-hot">就是今天</span>
              <span v-else>· 还有 {{ data.makeup[0].days_left }} 天</span>
            </div>
            <div class="ft-makeup-desc">
              为 {{ data.makeup[0].for_holiday }} 放假调休<template v-if="data.makeup.length > 1">
                ，之后还有 {{ data.makeup.slice(1).map(m => m.date).join('、') }} 需上班</template>
            </div>
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
          <div v-for="h in data.holidays" :key="h.name + h.date" class="ft-holiday">
            <span class="ft-h-name">{{ h.name }}</span>
            <span class="ft-h-date">{{ formatRange(h) }}</span>
            <span v-if="h.kind === 'statutory'" class="ft-h-badge legal">法定 {{ h.days }} 天</span>
            <span v-if="h.makeup_days" class="ft-h-badge makeup">补班 {{ h.makeup_days }} 天</span>
            <span class="ft-h-days" :class="{ hot: h.days_left <= 7 }">
              {{ h.days_left === 0 ? (h.in_progress ? '假期中' : '就是今天') : `还有 ${h.days_left} 天` }}
            </span>
          </div>
        </div>

        <!-- 当年假期放完、次年安排未公布 -->
        <div v-if="data.next_pending && !data.next_holiday" class="ft-pending glass-card">
          {{ data.next_pending.plan_note }}，先看个元旦：{{ data.next_pending.date }}
          （还有 {{ data.next_pending.days_left }} 天）
        </div>

        <div class="ft-note">{{ (data.notes || []).join(' · ') }}</div>
      </template>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { fishCalendar } from '@/api/toolkit'

const data = ref(null)
const error = ref('')

const heroMain = computed(() => {
  const d = data.value
  if (!d) return ''
  const t = d.today || {}
  if (t.kind === 'holiday') return `${t.name} 假期中 · 第 ${t.day_index}/${t.days} 天`
  if (t.kind === 'makeup') return '今天调休补班 😮‍💨'
  const nh = d.next_holiday
  if (nh) return `${nh.name} 还有 ${nh.days_left} 天`
  if (d.next_pending) return `距 ${d.next_pending.name} 还有 ${d.next_pending.days_left} 天`
  return `距周六还有 ${d.days_to_saturday} 天`
})

const heroSub = computed(() => {
  const nh = data.value?.next_holiday
  if (!nh) return ''
  const parts = [`放假 ${nh.days} 天（${nh.start} ~ ${nh.end}）`]
  if (nh.makeup_days) {
    parts.push(`${nh.makeup.map((m) => m.slice(5)).join('、')} 补班`)
  } else {
    parts.push('不调休')
  }
  return parts.join(' · ')
})

function formatRange(h) {
  if (!h.end || h.end === h.date) return h.date
  return `${h.date} ~ ${h.end}`
}

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
.ft-hero.is-holiday { border-left: 3px solid var(--yq-gold, #c7a96b); }
.ft-hero.is-makeup { border-left: 3px solid #e5484d; }
.ft-date { font-size: 13px; color: var(--dp-text3, #8a8f98); }
.ft-main { margin-top: 6px; font-size: 22px; font-weight: 800; color: var(--dp-text, #18202a); }
.ft-sub { margin-top: 6px; font-size: 12.5px; color: var(--dp-text3, #8a8f98); }
.ft-hero-right { min-width: 180px; }
.ft-week-label { font-size: 12px; color: var(--dp-text3, #8a8f98); }
.ft-week-bar { margin-top: 6px; height: 8px; border-radius: 999px; background: var(--dp-bg2, rgba(0,0,0,.06)); overflow: hidden; }
.ft-week-bar i { display: block; height: 100%; background: linear-gradient(90deg, var(--yq-gold, #c7a96b), var(--yq-gold-bright, #f59e0b)); border-radius: 999px; }
.ft-week-pct { margin-top: 4px; font-size: 12px; color: var(--yq-gold, #c7a96b); font-weight: 700; text-align: right; }
.ft-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 14px; }
.ft-stat { padding: 14px 16px; text-align: center; }
.ft-stat-num { font-size: 22px; font-weight: 800; color: var(--yq-gold, #c7a96b); line-height: 1.2; }
.ft-stat-label { margin-top: 4px; font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.ft-makeup { display: flex; align-items: center; gap: 14px; margin-top: 14px; padding: 14px 16px; border-left: 3px solid #e5484d; }
.ft-makeup-icon { font-size: 20px; }
.ft-makeup-title { font-size: 14px; font-weight: 700; color: var(--dp-text, #18202a); }
.ft-makeup-hot { color: #e5484d; }
.ft-makeup-desc { margin-top: 3px; font-size: 12px; color: var(--dp-text3, #8a8f98); }
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
  display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-radius: 10px;
  border-bottom: 1px solid var(--dp-line, rgba(0,0,0,.06));
}
.ft-h-name { font-weight: 600; font-size: 14px; color: var(--dp-text, #18202a); width: 90px; flex: none; }
.ft-h-date { font-size: 13px; color: var(--dp-text3, #8a8f98); flex: 1; }
.ft-h-badge {
  flex: none; font-size: 11px; padding: 2px 7px; border-radius: 999px; line-height: 1.5;
}
.ft-h-badge.legal { color: var(--yq-gold, #c7a96b); background: color-mix(in srgb, var(--yq-gold, #c7a96b) 14%, transparent); }
.ft-h-badge.makeup { color: #e5484d; background: color-mix(in srgb, #e5484d 12%, transparent); }
.ft-h-days { flex: none; font-size: 13.5px; font-weight: 700; color: var(--dp-text2, #45505b); }
.ft-h-days.hot { color: #e5484d; }
.ft-pending { margin-top: 14px; padding: 12px 16px; font-size: 12.5px; color: var(--dp-text3, #8a8f98); }
.ft-note { margin-top: 12px; font-size: 11.5px; color: var(--dp-text3, #8a8f98); line-height: 1.7; }
</style>
