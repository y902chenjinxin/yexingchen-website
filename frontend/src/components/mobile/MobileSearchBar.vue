<template>
  <div class="msearch" ref="rootEl">
    <div class="msearch-bar">
      <svg class="msearch-mag" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
      <input
        v-model="word"
        class="msearch-input"
        placeholder="搜索笔记 · 音乐 · 小说 · 视频 · 工具"
        @focus="focus=true"
        @input="debounceSearch"
        @keyup.enter="run"
        aria-label="全局搜索"
      />
      <VoiceInputButton class="msearch-voice" @result="onVoice" />
      <span v-if="word" class="msearch-clear" role="button" tabindex="0" aria-label="清空" @click="clear" @keydown.enter="clear">✕</span>
    </div>

    <!-- 联想面板 -->
    <transition name="msearch-pop">
      <div v-if="focus && (word.trim() || showModules)" class="msearch-panel" @mousedown.stop>
        <template v-if="results.count">
          <div v-for="(g, k) in groups" :key="k" class="msearch-group">
            <div class="msearch-group__head">{{ g.title }}</div>
            <button v-for="it in g.items" :key="k + it.id" class="msearch-item" @click="pick(g.to(it))">
              <span>{{ g.label(it) }}</span>
            </button>
          </div>
        </template>
        <div v-else-if="word.trim()" class="msearch-empty">未找到相关结果</div>

        <!-- 快捷前往模块 -->
        <div class="msearch-mods">
          <div class="msearch-mods__head">快速前往</div>
          <div class="msearch-mods__row">
            <button v-for="m in quickModules" :key="m.path" class="msearch-mod" @click="pick(m.path)">
              <span class="msearch-mod-rune">{{ m.rune }}</span>
              <span>{{ m.title }}</span>
            </button>
          </div>
        </div>

        <button class="msearch-ai" @click="pick('/assistant')">
          用 AI 对话问点什么
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useMenusStore } from '@/stores/menus'
import { searchAll } from '@/api/search'
import VoiceInputButton from '@/components/VoiceInputButton.vue'

const emit = defineEmits(['go'])
const router = useRouter()
const menus = useMenusStore()

const word = ref('')
const focus = ref(false)
const showModules = ref(true)
const results = ref({ results: null, count: 0 })
let timer = null

const groups = computed(() => {
  const r = results.value.results || {}
  return [
    { key:'notes', title:'笔记', items: r.notes || [], label: it => it?.title || '（无标题）', to: it => `/notes/${it?.id}` },
    { key:'music', title:'音乐', items: r.music || [], label: it => it?.title || '', to: () => '/music' },
    { key:'novels', title:'小说', items: r.novels || [], label: it => (it?.title||'') + (it?.author ? `　${it.author}` : ''), to: () => '/novel' },
    { key:'videos', title:'视频', items: r.videos || [], label: it => it?.title || '', to: () => '/video' },
    { key:'tools', title:'工具', items: r.tools || [], label: it => it?.title || it?.description || '', to: () => '/tool' },
  ].filter(g => g.items.length)
})

const QUICK = [
  { path:'/music', rune:'音', title:'音乐' }, { path:'/novel', rune:'書', title:'小说' },
  { path:'/video', rune:'影', title:'视频' }, { path:'/notes', rune:'記', title:'笔记' },
  { path:'/finance', rune:'账', title:'记账' }, { path:'/stocks', rune:'股', title:'股票' },
  { path:'/tool', rune:'器', title:'工具' }, { path:'/travels', rune:'迹', title:'足迹' },
]
const quickModules = computed(() => QUICK.filter(m => menus.isPathAllowed(m.path)))

function debounceSearch() {
  clearTimeout(timer)
  const q = word.value.trim()
  if (!q) { results.value = { results:null, count:0 }; showModules.value = true; return }
  showModules.value = true
  timer = setTimeout(async () => {
    try {
      const d = (await searchAll({ q, page:1, size:5 }))?.data || {}
      const count = (d.notes?.length||0)+(d.music?.length||0)+(d.novels?.length||0)+(d.videos?.length||0)+(d.tools?.length||0)
      results.value = { results: d, count }
    } catch { results.value = { results:null, count:0 } }
  }, 260)
}

function onVoice(text) {
  word.value = text
  focus.value = true
  debounceSearch()
}

function run() {
  const q = word.value.trim()
  if (!q) return
  router.push({ path:'/notes', query:{ q } })
  close()
}

function pick(path) {
  close()
  emit('go', path)
  router.push(path)
}

function clear() { word.value = ''; results.value = { results:null, count:0 } }
function close() { focus.value = false }

const rootEl = ref(null)
function onDocDown(e) {
  if (!rootEl.value?.contains(e.target)) focus.value = false
}
onMounted(() => { menus.load(); document.addEventListener('mousedown', onDocDown) })
onBeforeUnmount(() => { clearTimeout(timer); document.removeEventListener('mousedown', onDocDown) })
</script>

<style scoped>
.msearch { position: relative; }
.msearch-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 0 8px 0 14px; height: 46px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.02)), rgba(14,22,29,.5);
  -webkit-backdrop-filter: var(--lj-glass-blur, blur(16px));
  backdrop-filter: var(--lj-glass-blur, blur(16px));
  border: 1px solid var(--lj-line-strong, rgba(127,168,163,.3));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.07), 0 6px 18px rgba(0,0,0,.2);
}
.msearch:focus-within .msearch-bar {
  border-color: var(--lj-amber, #caa466);
  box-shadow: 0 0 0 3px rgba(201,163,95,.16), inset 0 1px 0 rgba(255,255,255,.07);
}
.msearch-mag { width: 17px; height: 17px; flex: none; color: var(--lj-text-3, rgba(200,215,220,.55)); }
.msearch-input {
  flex: 1; min-width: 0; height: 100%; border: none; outline: none; background: transparent;
  font-size: 14.5px; color: var(--lj-text, #dfebe5);
  caret-color: var(--lj-amber, #caa466);
}
.msearch-input::placeholder { color: var(--lj-text-3, rgba(200,215,220,.5)); }
.msearch-voice { flex: none; }
.msearch-clear {
  flex: none; width: 22px; height: 22px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px; color: var(--lj-text-3); cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

/* 面板 */
.msearch-panel {
  position: absolute; top: calc(100% + 10px); left: 0; right: 0;
  border-radius: 18px; overflow: hidden;
  background: var(--lj-paper, #101b15);
  -webkit-backdrop-filter: var(--lj-glass-blur, blur(18px));
  backdrop-filter: var(--lj-glass-blur, blur(18px));
  border: 1px solid var(--lj-line, rgba(127,168,163,.24));
  box-shadow: 0 18px 40px rgba(0,0,0,.36);
  z-index: 120;
  padding: 8px 10px;
}
.msearch-group + .msearch-group { margin-top: 4px; }
.msearch-group__head { padding: 4px 8px; font-size: 11px; letter-spacing: .14em; color: var(--lj-text-3, rgba(200,215,220,.5)); }
.msearch-item {
  display: flex; width: 100%; text-align: left; gap: 6px;
  padding: 9px 10px; border-radius: 12px; font-size: 14px; color: var(--lj-text-2, rgba(210,222,225,.8));
}
.msearch-item:active, .msearch-item:hover { background: rgba(127,168,163,.1); color: var(--lj-amber, #caa466); }
.msearch-empty { padding: 14px 10px; text-align: center; font-size: 13px; color: var(--lj-text-3); }

.msearch-mods { margin-top: 6px; padding-top: 8px; border-top: 1px solid var(--lj-line, rgba(127,168,163,.16)); }
.msearch-mods__head { padding: 4px 8px; font-size: 11px; letter-spacing: .14em; color: var(--lj-text-3, rgba(200,215,220,.5)); }
.msearch-mods__row { display: flex; flex-wrap: wrap; gap: 6px; padding: 2px 4px; }
.msearch-mod {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 10px; border-radius: 10px; font-size: 12.5px; color: var(--lj-text-2);
  background: rgba(127,168,163,.07); border: 1px solid var(--lj-line, rgba(127,168,163,.2));
}
.msearch-mod:active { border-color: var(--lj-amber, #caa466); color: var(--lj-amber, #caa466); }
.msearch-mod-rune { font-family: var(--font-serif, serif); color: var(--lj-amber, #b8894a); }
.msearch-ai {
  display: block; width: 100%; text-align: center;
  margin-top: 8px; padding: 10px; border-radius: 12px;
  background: linear-gradient(135deg, var(--lj-seal,#c96b58), var(--lj-seal-hover,#e0a26b));
  color: #fff; font-size: 13.5px; font-weight: 600;
}

.msearch-pop-enter-active, .msearch-pop-leave-active { transition: opacity .18s ease, transform .18s ease; }
.msearch-pop-enter-from, .msearch-pop-leave-to { opacity: 0; transform: translateY(-6px); }
</style>