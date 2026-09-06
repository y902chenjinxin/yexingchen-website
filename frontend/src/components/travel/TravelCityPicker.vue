<template>
  <div class="tcp" v-click-outside="close">
    <input
      class="tcp-input"
      :value="text"
      :placeholder="placeholder"
      @input="onInput"
      @focus="open = true"
      @click="open = true"
    />
    <!-- 省份/城市两级下拉（内联面板，非弹窗） -->
    <div v-if="open" class="tcp-panel">
      <div class="tcp-tabs">
        <button v-for="p in provinceList" :key="p"
          class="tcp-tab" :class="{ on: selProvince === p }"
          @click="handleProvince(p)">{{ p }}</button>
      </div>
      <div class="tcp-cities">
        <button v-for="c in curCities" :key="c[0]"
          class="tcp-city" :class="{ on: isSel(c) }"
          @click="pick(c)">{{ c[0] }}</button>
        <div v-if="!curCities.length" class="tcp-none">该省份暂未收录城市</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  cities: { type: Array, default: () => [] }, // 本行程已选城市 {city, province, lon, lat}
  placeholder: { type: String, default: '选择城市…' }
})
const emit = defineEmits(['add'])
const vClickOutside = {
  mounted(el, binding) {
    el._clo = (ev) => { if (!el.contains(ev.target)) binding.value() }
    document.addEventListener('mousedown', el._clo)
  },
  unmounted(el) { document.removeEventListener('mousedown', el._clo) }
}

const lib = ref({})
const open = ref(false)
const text = ref('')
const selProvince = ref('')

const provinceList = computed(() => Object.keys(lib.value || {}))
const curCities = computed(() => (lib.value || {})[selProvince.value] || [])

fetch('/geo/cities.json').then((r) => r.json()).then((d) => { lib.value = d || {} }).catch(() => {})

function onInput(e) {
  text.value = e.target.value
  const kw = text.value.trim()
  if (!kw) { selProvince.value = ''; return }
  // 命中省份名直接展开该省
  if (lib.value[kw]) { selProvince.value = kw; return }
  // 跨省搜城市
  for (const [p, arr] of Object.entries(lib.value)) {
    if (arr.some((c) => c[0].includes(kw))) { selProvince.value = p; return }
  }
  selProvince.value = ''
}
function isSel(c) { return props.cities.some((x) => x.city === c[0] && x.province === selProvince.value) }
function pick(c) {
  const [name, lon, lat] = c
  emit('add', { city: name, province: selProvince.value, lon, lat })
  open.value = false
  text.value = ''
}
function handleProvince(p) { selProvince.value = p }
function close() { open.value = false }
</script>

<style scoped>
.tcp { position: relative; }
.tcp-input {
  width: 100%; box-sizing: border-box; padding: 8px 12px; border-radius: 10px;
  border: 1px solid var(--lj-line); background: var(--lj-glass-inset, rgba(255,255,255,.04));
  color: var(--lj-text); font-size: 14px; outline: none;
}
.tcp-input:focus { border-color: var(--lj-line-strong); }
.tcp-panel {
  position: absolute; top: 44px; left: 0; right: 0; z-index: 40;
  background: var(--lj-panel, rgba(16,22,28,.96));
  -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); border-radius: 12px; box-shadow: var(--glass-highlight), 0 16px 34px rgba(0,0,0,.35);
  padding: 8px; max-height: 260px; display: flex; flex-direction: column;
}
.tcp-tabs { display: flex; flex-wrap: wrap; gap: 4px; max-height: 96px; overflow-y: auto; padding-bottom: 6px; border-bottom: 1px dashed var(--lj-line); }
.tcp-tab { font-size: 12px; padding: 3px 9px; border-radius: 999px; border: 1px solid transparent; background: none; color: var(--lj-text-2); cursor: pointer; }
.tcp-tab.on { color: var(--lj-dai); border-color: var(--lj-dai); opacity: .9; }
.tcp-cities { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; overflow-y: auto; }
.tcp-city { font-size: 13px; padding: 4px 10px; border-radius: 8px; border: 1px solid var(--lj-line); background: none; color: var(--lj-text); cursor: pointer; }
.tcp-city:hover { border-color: var(--lj-dai); color: var(--lj-dai); }
.tcp-city.on { background: rgba(127,168,163,.16); border-color: var(--lj-dai); color: var(--lj-dai); }
.tcp-none { font-size: 12px; color: var(--lj-text-3); padding: 8px; }
</style>