<template>
  <div class="lp-root">
    <!-- 触发区：像普通输入框，点开弹日历 -->
    <button type="button" class="lp-field" :class="{ empty: !modelValue }" @click="toggle">
      <span class="lp-field-main">{{ modelValue || placeholder }}</span>
      <span v-if="lunarText" class="lp-field-lunar">{{ lunarText }}</span>
      <i class="lp-caret">▾</i>
    </button>
    <button v-if="modelValue" type="button" class="lp-clear" title="清除" @click.stop="pick('')">✕</button>

    <Teleport to="body">
      <div v-if="open" class="lp-mask" @click.self="open = false">
        <div class="lp-panel">
          <!-- 月历核心复用 LunarCalendar；头部点年份可快速跳年 -->
          <LunarCalendar
            ref="calRef"
            :model-value="modelValue"
            hint="点日期选择；带「休/班」的是法定假期与调休"
            @pick="pick"
          />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
/** 农历日历日期选择器（v2.40.36；v2.40.37 抽出 LunarCalendar 复用）。 */
import { ref, watch, onMounted } from 'vue'
import LunarCalendar from '@/components/common/LunarCalendar.vue'
import { getDayInfo } from '@/utils/lunarCache'

const props = defineProps({
  modelValue: { type: String, default: '' },     // 'YYYY-MM-DD'
  placeholder: { type: String, default: '选择日期' },
})
const emit = defineEmits(['update:modelValue', 'pick'])

const open = ref(false)
const lunarText = ref('')
const calRef = ref(null)

/** 收起时也把所选日期的农历写在输入框上（一眼能看到「农历八月十五」） */
async function refreshLunar() {
  if (!props.modelValue) { lunarText.value = ''; return }
  const info = await getDayInfo(props.modelValue)
  lunarText.value = info?.lunar_full || ''
}

function toggle() {
  open.value = !open.value
  if (open.value) calRef.value?.toDay?.()      // 每次打开都回到「日」视图
}

function pick(dateStr) {
  emit('update:modelValue', dateStr)
  emit('pick', dateStr)
  open.value = false
}

watch(() => props.modelValue, refreshLunar)
onMounted(refreshLunar)
</script>

<style scoped>
.lp-root { position: relative; display: inline-flex; align-items: center; gap: 6px; width: 100%; }
.lp-field {
  flex: 1; display: flex; align-items: center; gap: 8px; min-height: 38px; padding: 8px 12px;
  border: 1px solid var(--dp-line, rgba(0, 0, 0, .14)); border-radius: 10px; cursor: pointer;
  background: var(--dp-surface, #fff); color: var(--dp-text, #18202a); font-family: inherit;
  font-size: 13.5px; text-align: left;
}
.lp-field.empty .lp-field-main { color: var(--dp-text3, #8a8f98); }
.lp-field-main { flex: 1; }
.lp-field-lunar { font-size: 11.5px; color: var(--yq-gold, #c7a96b); white-space: nowrap; }
.lp-caret { color: var(--dp-text3, #8a8f98); font-size: 11px; }
.lp-clear {
  border: none; background: transparent; cursor: pointer; color: var(--dp-text3, #8a8f98);
  font-size: 13px; padding: 4px 6px;
}

.lp-mask {
  position: fixed; inset: 0; z-index: 2000; background: rgba(20, 26, 34, .38);
  display: flex; align-items: center; justify-content: center; padding: 16px;
}
.lp-panel {
  width: min(420px, 100%); max-height: 88vh; overflow-y: auto; border-radius: 18px; padding: 14px 16px 12px;
  background: var(--dp-bg, #f7f5f0); box-shadow: 0 20px 50px rgba(10, 16, 24, .28);
}
</style>
