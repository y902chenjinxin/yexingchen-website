<template>
  <!-- 管理模块统一摘要头（v2.46.372）
       三层信息模型里的 L1：一个主数字 + 2~3 个迷你指标，一屏内看完不滚。
       L2 概览（构成条 / 迷你趋势）走默认插槽，由各模块自己画。 -->
  <section class="ms" :aria-label="label">
    <div class="ms-head">
      <span class="ms-label">{{ label }}</span>
      <span v-if="badge" class="ms-badge">{{ badge }}</span>
    </div>

    <div class="ms-value-row">
      <span v-if="unit" class="ms-unit">{{ unit }}</span>
      <span class="ms-value" :class="{ neg: isNeg }">{{ display }}</span>
    </div>

    <div v-if="deltaText" class="ms-delta" :class="deltaTone">
      <span class="ms-delta-arrow" aria-hidden="true">{{ deltaArrow }}</span>
      <span>{{ deltaText }}</span>
    </div>

    <div v-if="stats && stats.length" class="ms-stats">
      <div v-for="s in stats" :key="s.label" class="ms-stat">
        <span class="ms-stat-label">{{ s.label }}</span>
        <span class="ms-stat-value" :class="s.tone">{{ s.value }}</span>
      </div>
    </div>

    <slot />
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** 主数字的标题，如「本月支出」 */
  label: { type: String, required: true },
  /** 主数字（数字或已格式化字符串） */
  value: { type: [Number, String], default: 0 },
  /** 货币/单位前缀，如「¥」；不传则不显示 */
  unit: { type: String, default: '' },
  /** 环比/差值百分比，正数升、负数降；null 不显示 */
  delta: { type: Number, default: null },
  /** 差值说明，如「较上月」 */
  deltaLabel: { type: String, default: '' },
  /** 差值方向语义：up=涨是好事（绿），down=跌是好事（如支出） */
  deltaGoodWhen: { type: String, default: 'down' },
  /** 右上角小徽标，如「11月」 */
  badge: { type: String, default: '' },
  /** 迷你指标：[{ label, value, tone }]，tone 可选 income/expense */
  stats: { type: Array, default: () => [] },
})

const isNeg = computed(() => {
  const n = typeof props.value === 'number' ? props.value : Number(String(props.value).replace(/[^\d.-]/g, ''))
  return Number.isFinite(n) && n < 0
})

const display = computed(() => {
  if (typeof props.value === 'string') return props.value
  if (!Number.isFinite(props.value)) return '0'
  return props.value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const deltaText = computed(() => {
  if (props.delta === null || props.delta === undefined) return ''
  const v = props.delta
  const pct = `${Math.abs(v).toFixed(1)}%`
  const dir = v === 0 ? '持平' : (v > 0 ? `增加 ${pct}` : `减少 ${pct}`)
  return props.deltaLabel ? `${props.deltaLabel}${dir}` : dir
})

const deltaArrow = computed(() => {
  if (props.delta === null || props.delta === undefined) return ''
  return props.delta > 0 ? '↑' : (props.delta < 0 ? '↓' : '—')
})

const deltaTone = computed(() => {
  if (props.delta === null || props.delta === undefined) return ''
  if (props.delta === 0) return 'flat'
  const rising = props.delta > 0
  const good = props.deltaGoodWhen === 'up' ? rising : !rising
  return good ? 'good' : 'bad'
})
</script>

<style scoped>
.ms {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 20px 20px 18px;
  border-radius: 22px;
  background:
    linear-gradient(165deg, rgba(255, 255, 255, .12), rgba(255, 255, 255, 0) 44%),
    var(--lg-tint, rgba(255, 255, 255, .88));
  -webkit-backdrop-filter: var(--lg-blur, blur(20px) saturate(170%));
  backdrop-filter: var(--lg-blur, blur(20px) saturate(170%));
  border: 1px solid var(--lg-line, rgba(60, 60, 67, .10));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .55),
    0 1px 2px rgba(31, 41, 55, .05),
    0 6px 18px rgba(31, 41, 55, .06);
}

.ms-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ms-label {
  font-size: 12px;
  letter-spacing: .04em;
  color: var(--color-text-tertiary, #8e8e93);
}

.ms-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  color: var(--color-text-tertiary, #8e8e93);
  background: rgba(127, 127, 127, .10);
}

.ms-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-top: 6px;
}

.ms-unit {
  font-size: 17px;
  font-weight: 500;
  color: var(--color-text-secondary, #515154);
}

.ms-value {
  font-size: 34px;
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -.02em;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-primary, #1d1d1f);
}

.ms-value.neg { color: #c0392b; }

.ms-delta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-tertiary, #8e8e93);
}

.ms-delta.good { color: #2e7d5b; }
.ms-delta.bad { color: #c0392b; }
.ms-delta-arrow { font-size: 12px; }

.ms-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
  gap: 8px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--lg-ctl-line, rgba(60, 60, 67, .10));
}

.ms-stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.ms-stat-label {
  font-size: 11px;
  color: var(--color-text-tertiary, #8e8e93);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ms-stat-value {
  font-size: 15px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-primary, #1d1d1f);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ms-stat-value.income { color: #2e7d5b; }
.ms-stat-value.expense { color: #c0392b; }

@media (max-width: 420px) {
  .ms { padding: 16px 16px 14px; border-radius: 20px; }
  .ms-value { font-size: 30px; }
}
</style>
