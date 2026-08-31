<template>
  <div class="note-select" :class="{ 'is-open': open }">
    <input
      ref="inputEl"
      v-model="kwText"
      class="note-select-input"
      type="text"
      :placeholder="placeholder"
      autocomplete="off"
      @focus="onFocus"
      @blur="onBlur"
      @keydown.down.prevent="moveCursor(1)"
      @keydown.up.prevent="moveCursor(-1)"
      @keydown.enter.prevent="commitCursor"
      @keydown.esc="closePanel"
    />
    <ul v-if="open" ref="listEl" class="note-select-list" role="listbox">
      <li
        v-for="(n, i) in items"
        :key="n.id"
        class="note-select-item"
        :class="{ active: n.id === value, hover: hoverIndex === i }"
        role="option"
        :aria-selected="n.id === value"
        @mousedown.prevent="selectItem(n)"
        @mouseenter="hoverIndex = i"
      >
        {{ n.title || '（无标题）' }}
        <span class="note-select-meta">#{{ n.id }}</span>
      </li>
      <li
        v-if="!loading && items.length === 0"
        class="note-select-empty"
      >{{ emptyText }}</li>
      <!-- 触底哨兵：IntersectionObserver 命中即触发加载下一页 -->
      <li ref="sentinelEl" class="note-select-sentinel" aria-hidden="true"></li>
      <li v-if="loading" class="note-select-loading">加载中…</li>
      <li v-else-if="!hasMore && items.length > 0" class="note-select-end">已加载全部</li>
    </ul>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  hasMore: { type: Boolean, default: false },
  placeholder: { type: String, default: '输入关键词搜索…' },
  emptyText: { type: String, default: '暂无可选项' },
})

const emit = defineEmits(['update:modelValue', 'search', 'load-more'])

const kwText = ref('')
const open = ref(false)
const hoverIndex = ref(-1)

const inputEl = ref(null)
const listEl = ref(null)
const sentinelEl = ref(null)

let io = null
let searchTimer = null
const SEARCH_DEBOUNCE_MS = 250

/** 触发远程搜索（防抖） */
function emitSearch(immediate = false) {
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
  if (immediate) {
    emit('search', kwText.value || '')
    return
  }
  searchTimer = setTimeout(() => {
    emit('search', kwText.value || '')
    searchTimer = null
  }, SEARCH_DEBOUNCE_MS)
}

function onFocus() {
  open.value = true
  // 首次打开时立刻搜索一次，确保有内容可滚动
  if (props.items.length === 0 && !props.loading) {
    emitSearch(true)
  } else {
    emitSearch(true)
  }
  nextTick(() => attachObserver())
}

function onBlur() {
  // 延时关闭以保证 click 选择生效
  setTimeout(() => {
    open.value = false
    detachObserver()
  }, 120)
}

function closePanel() {
  open.value = false
  inputEl.value && inputEl.value.blur()
}

function attachObserver() {
  if (typeof IntersectionObserver === 'undefined') return
  detachObserver()
  if (!sentinelEl.value) return
  io = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        if (props.hasMore && !props.loading) {
          emit('load-more')
        }
      }
    }
  }, { root: listEl.value, rootMargin: '0px 0px 80px 0px' })
  io.observe(sentinelEl.value)
}

function detachObserver() {
  if (io) {
    io.disconnect()
    io = null
  }
}

/** 同步外部 value 到输入框显示 */
function syncInputFromValue() {
  const v = props.modelValue
  if (v == null) {
    // 清空时不强制覆盖用户输入（让用户继续搜索）
    return
  }
  const cur = props.items.find((n) => n.id === v)
  if (cur) kwText.value = cur.title || ''
}

watch(() => props.modelValue, () => syncInputFromValue(), { immediate: true })
watch(() => props.items, () => syncInputFromValue())

watch(open, async (v) => {
  if (v) {
    await nextTick()
    attachObserver()
  } else {
    detachObserver()
  }
})

/** 输入即触发搜索（带防抖） */
watch(kwText, () => {
  if (!open.value) return
  emitSearch(false)
})

function moveCursor(delta) {
  if (!open.value) {
    open.value = true
    return
  }
  if (props.items.length === 0) return
  let next = hoverIndex.value + delta
  if (next < 0) next = 0
  if (next >= props.items.length) next = props.items.length - 1
  hoverIndex.value = next
  scrollHoverIntoView()
}

function scrollHoverIntoView() {
  if (!listEl.value) return
  const li = listEl.value.querySelectorAll('.note-select-item')[hoverIndex.value]
  if (li && li.scrollIntoView) li.scrollIntoView({ block: 'nearest' })
}

function commitCursor() {
  if (hoverIndex.value >= 0 && hoverIndex.value < props.items.length) {
    selectItem(props.items[hoverIndex.value])
  }
}

function selectItem(n) {
  if (!n) return
  kwText.value = n.title || ''
  emit('update:modelValue', n.id)
  open.value = false
  detachObserver()
}

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
  detachObserver()
})
</script>

<style scoped>
.note-select { position: relative; width: 100%; }
.note-select-input {
  width: 100%;
  height: 32px;
  padding: 4px 10px;
  border: 1px solid #d4b85f;
  border-radius: 4px;
  background: #fff;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}
.note-select-input:focus { border-color: #b58a3f; box-shadow: 0 0 0 2px rgba(181, 138, 63, 0.2); }
.note-select-list {
  position: absolute;
  top: 36px;
  left: 0;
  right: 0;
  max-height: 240px;
  overflow-y: auto;
  margin: 0;
  padding: 0;
  list-style: none;
  background: #fff;
  border: 1px solid #d4b85f;
  border-radius: 4px;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.note-select-item {
  padding: 6px 10px;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.note-select-item.hover, .note-select-item:hover { background: #fff8e6; }
.note-select-item.active { background: #b58a3f; color: #fff; }
.note-select-item.active .note-select-meta { color: #f0eada; }
.note-select-meta { font-size: 11px; color: #999; }
.note-select-empty, .note-select-loading, .note-select-end {
  padding: 8px 10px;
  font-size: 12px;
  color: #999;
  text-align: center;
}
.note-select-sentinel { height: 1px; padding: 0; margin: 0; list-style: none; }
</style>