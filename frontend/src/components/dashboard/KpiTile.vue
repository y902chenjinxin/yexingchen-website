<template>
  <div class="kpi" :class="{ 'kpi-click': clickable }" @click="$emit('click')">
    <div class="kpi-label">{{ label }}</div>
    <div class="kpi-val" :style="valColor ? { color: valColor } : {}">
      {{ val }}<span v-if="unit" class="kpi-unit">{{ unit }}</span>
    </div>
    <div v-if="sub || delta" class="kpi-meta">
      <span v-if="delta" class="kpi-delta" :class="deltaClass">{{ delta }}</span>
      <span v-if="sub" class="kpi-sub">{{ sub }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  val: { type: [String, Number], required: true },
  unit: { type: String, default: '' },
  sub: { type: String, default: '' },
  delta: { type: String, default: '' },
  deltaTone: { type: String, default: 'up' }, // up / dn / neu
  valColor: { type: String, default: '' },
  clickable: { type: Boolean, default: false },
})

defineEmits(['click'])

const deltaClass = computed(() => {
  if (!props.delta) return ''
  return props.deltaTone === 'dn' ? 'kpi-delta-dn' : (props.deltaTone === 'neu' ? 'kpi-delta-neu' : 'kpi-delta-up')
})
</script>

<style scoped>
.kpi {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  padding: 14px 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 92px;
  transition: border-color .15s, box-shadow .15s, transform .15s;
  box-shadow: var(--dp-shadow);
}
.kpi-click { cursor: pointer; }
.kpi-click:hover {
  border-color: var(--dp-accent);
  box-shadow: var(--dp-glow);
  transform: translateY(-1px);
}
.kpi-label {
  font-size: 11px;
  color: var(--dp-text3);
  letter-spacing: .04em;
  text-transform: uppercase;
}
.kpi-val {
  font-size: 24px;
  font-weight: 700;
  font-family: var(--dp-serif);
  font-variant-numeric: tabular-nums;
  color: var(--dp-text);
  line-height: 1.1;
}
.kpi-unit {
  font-size: 13px;
  font-weight: 400;
  margin-left: 4px;
  color: var(--dp-text3);
}
.kpi-meta {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 2px;
  font-size: 11px;
}
.kpi-delta-up { color: #16a34a; }
.kpi-delta-dn { color: #dc2626; }
.kpi-delta-neu { color: var(--dp-text3); }
:root[data-theme="night"] .kpi-delta-up { color: #34d399; }
:root[data-theme="night"] .kpi-delta-dn { color: #fb7185; }
.kpi-sub { color: var(--dp-text3); }
</style>