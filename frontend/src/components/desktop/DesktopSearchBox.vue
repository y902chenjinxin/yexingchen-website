<template>
  <div class="ds-search" :class="{ 'is-open': open }">
    <el-input
      v-model="word"
      class="ds-search-input"
      placeholder="搜索全站"
      clearable
      size="small"
      @focus="focus = true"
      @input="onInput"
      @keyup.enter="runSearch"
    >
      <template #prefix><el-icon><Search /></el-icon></template>
      <template #suffix>
        <VoiceInputButton @result="onVoice" />
      </template>
    </el-input>

    <!-- 联想面板：宽于侧栏，向右浮出 -->
    <transition name="ds-fade">
      <div v-if="focus && word.trim()" class="ds-suggest">
        <template v-for="(group, gkey) in groups" :key="gkey">
          <div v-if="group.items.length" class="ds-group">
            <div class="ds-head">{{ group.title }}</div>
            <div
              v-for="it in group.items"
              :key="gkey + '-' + it.id"
              class="ds-item"
              @mousedown.prevent="go(group.to(it))"
            >
              <el-icon class="ds-ic"><component :is="group.icon" /></el-icon>
              <span class="ds-label">{{ group.label(it) }}</span>
            </div>
          </div>
        </template>

        <div v-if="!count" class="ds-empty">未找到相关结果，可直达下方模块</div>

        <!-- 模块快捷入口（DB 菜单驱动，已按角色过滤） -->
        <div class="ds-modules">
          <div class="ds-head">快速前往</div>
          <div class="ds-mod-row">
            <a
              v-for="mod in menus.loose"
              :key="'m' + mod.id"
              class="ds-mod"
              @mousedown.prevent="go(mod.path)"
            >
              <el-icon class="ds-ic"><component :is="menuIcon(mod.icon)" /></el-icon>
              <span>{{ mod.title }}</span>
            </a>
          </div>
          <template v-for="grp in menus.groups" :key="'g' + grp.id">
            <div class="ds-subhead">
              <el-icon class="ds-ic"><component :is="menuIcon(grp.icon)" /></el-icon>
              <span>{{ grp.title }}</span>
            </div>
            <div class="ds-mod-row">
              <a
                v-for="sub in grp.children"
                :key="'s' + sub.id"
                class="ds-mod"
                :class="{ active: isActivePath(sub.path) }"
                @mousedown.prevent="go(sub.path)"
              >
                <el-icon class="ds-ic"><component :is="menuIcon(sub.icon)" /></el-icon>
                <span>{{ sub.title }}</span>
              </a>
            </div>
          </template>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  Search, Collection, TrendCharts, MapLocation, Tools, Headset, Reading,
  VideoCamera, Document, ChatDotRound, Setting, User, Tickets, Wallet,
  Money, DataAnalysis, DataBoard, MagicStick, VideoPlay, Notebook, Grid,
} from '@element-plus/icons-vue'
import { searchAll } from '@/api/search'
import { useMenusStore } from '@/stores/menus'
import VoiceInputButton from '@/components/VoiceInputButton.vue'

const router = useRouter()
const route = useRoute()
const menus = useMenusStore()

const word = ref('')
const focus = ref(false)
const open = computed(() => focus.value && !!word.value.trim())
let timer = null

const suggestions = ref({ results: null, count: 0 })
const count = computed(() => suggestions.value.count)

const ICON_MAP = {
  Collection, TrendCharts, MapLocation, Tools, Headset, Reading, VideoCamera,
  Document, ChatDotRound, Setting, User, Tickets, Wallet, Money, DataAnalysis,
  DataBoard, MagicStick, VideoPlay, Notebook,
}
function menuIcon(name) { return ICON_MAP[name] || Grid }

function isActivePath(path) {
  if (!path) return false
  const cur = route.path
  return cur === path || cur.startsWith(path + '/')
}

const groups = computed(() => {
  const r = suggestions.value.results || {}
  return [
    { key: 'notes', title: '笔记', icon: Document, items: r.notes || [], label: (it) => it?.title || '（无标题）', to: (it) => `/notes/${it?.id}` },
    { key: 'music', title: '音乐', icon: Headset, items: r.music || [], label: (it) => it?.title || '（无标题）', to: () => '/music' },
    { key: 'novels', title: '小说', icon: Reading, items: r.novels || [], label: (it) => it?.title + (it?.author ? `　${it.author}` : ''), to: () => '/novel' },
    { key: 'videos', title: '视频', icon: VideoPlay, items: r.videos || [], label: (it) => it?.title || '（无标题）', to: () => '/video' },
    { key: 'tools', title: '工具', icon: Tools, items: r.tools || [], label: (it) => it?.title || it?.description || '（无标题）', to: () => '/tool' },
  ]
})

function onInput() {
  clearTimeout(timer)
  const q = (word.value || '').trim()
  if (!q) { suggestions.value = { results: null, count: 0 }; return }
  timer = setTimeout(async () => {
    try {
      const res = await searchAll({ q, page: 1, size: 6 })
      const data = res?.data || {}
      const c = (data.notes?.length || 0) + (data.music?.length || 0) +
        (data.novels?.length || 0) + (data.videos?.length || 0) + (data.tools?.length || 0)
      suggestions.value = { results: data, count: c }
    } catch {
      suggestions.value = { results: null, count: 0 }
    }
  }, 260)
}

function runSearch() {
  const q = (word.value || '').trim()
  focus.value = false
  if (!q) return
  router.push({ path: '/notes', query: { q } })
  suggestions.value = { results: null, count: 0 }
}

function onVoice(text) {
  const merged = word.value.trim() ? `${word.value.trim()} ${text}` : text
  word.value = merged
  focus.value = true
  onInput()
}

function go(path) {
  focus.value = false
  router.push(path)
}

function onDocDown(e) {
  if (!e.target?.closest?.('.ds-search')) focus.value = false
}

onMounted(() => {
  menus.load()
  document.addEventListener('mousedown', onDocDown)
})
onUnmounted(() => {
  clearTimeout(timer)
  document.removeEventListener('mousedown', onDocDown)
})
</script>

<style scoped>
.ds-search {
  position: relative;
  width: 100%;
}
.ds-search :deep(.el-input__wrapper) {
  background: var(--dp-surface2) !important;
  box-shadow: inset 0 0 0 1px var(--dp-line) !important;
  border-radius: 8px;
}
.ds-search :deep(.el-input__wrapper:hover) {
  box-shadow: inset 0 0 0 1px var(--dp-line-strong) !important;
}
.ds-search :deep(.el-input__inner) { font-size: 13px; }
.ds-search :deep(.el-input__inner::placeholder) { color: var(--dp-text3); }

/* 联想面板：向右浮出，宽于侧栏 */
.ds-suggest {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 320px;
  max-height: 60vh;
  overflow-y: auto;
  z-index: 1200;
  padding: 8px;
  border-radius: 12px;
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  box-shadow: var(--dp-raised, var(--dp-shadow));
}
:root[data-theme="night"] .ds-suggest {
  background: rgba(28, 24, 46, .96);
  -webkit-backdrop-filter: blur(16px);
  backdrop-filter: blur(16px);
}

.ds-head {
  font-size: 10px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--dp-text3);
  padding: 8px 8px 4px;
}
.ds-subhead {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--dp-text2);
  padding: 8px 8px 4px;
}
.ds-group + .ds-group { margin-top: 2px; }

.ds-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 13px;
  color: var(--dp-text);
}
.ds-item:hover { background: var(--dp-surface2); color: var(--dp-accent); }
.ds-ic { flex: none; opacity: .85; }
.ds-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.ds-empty {
  font-size: 12px;
  color: var(--dp-text3);
  padding: 12px 8px;
  text-align: center;
}

.ds-modules { border-top: 1px solid var(--dp-line); margin-top: 6px; }
.ds-mod-row { display: flex; flex-wrap: wrap; gap: 4px; padding: 0 4px 4px; }
.ds-mod {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  border-radius: 7px;
  font-size: 12px;
  color: var(--dp-text2);
  cursor: pointer;
  text-decoration: none;
}
.ds-mod:hover { background: var(--dp-surface2); color: var(--dp-text); }
.ds-mod.active { background: var(--dp-accent-faint); color: var(--dp-accent); }

.ds-fade-enter-active, .ds-fade-leave-active { transition: opacity .15s, transform .15s; }
.ds-fade-enter-from, .ds-fade-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
