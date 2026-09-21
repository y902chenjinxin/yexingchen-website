<!--
  CommandPalette.vue
  玄黄·全局命令面板（Cmd/Ctrl+K）
  - 聚合路由跳转、工具、动作三类命令
  - 模糊匹配（name + alias + keyword），按优先级排序
  - ⌘K / Ctrl+K 唤起；Esc 关闭；↑↓ 选择；Enter 触发
  - 单例挂载到 App.vue，跨页面保持状态

  Props: 无（用 router / pinia 全局）
  Emits: 无
-->
<template>
  <transition name="cp-fade">
    <div v-if="open" class="cp-mask" @click.self="close" role="dialog" aria-modal="true" aria-label="命令面板">
      <div class="cp-panel" @keydown.stop @keydown.esc="close" ref="panelRef">
        <div class="cp-search">
          <span class="cp-search-icon" aria-hidden="true">⌘</span>
          <input
            ref="inputRef"
            v-model="query"
            class="cp-input"
            type="text"
            spellcheck="false"
            autocomplete="off"
            placeholder="搜索命令、页面、工具…（输入文字筛选）"
            :aria-label="`命令面板输入框，共 ${items.length} 条`"
          />
          <span class="cp-kbd">esc</span>
        </div>

        <div class="cp-list" ref="listRef" role="listbox" :aria-activedescendant="`cp-item-${activeIndex}`">
          <div v-if="!items.length" class="cp-empty">未匹配到命令</div>
          <template v-else>
            <button
              v-for="(it, i) in items"
              :id="`cp-item-${i}`"
              :key="it.key"
              type="button"
              role="option"
              :aria-selected="i === activeIndex"
              class="cp-item"
              :class="{ active: i === activeIndex, group: it.group === '分组' }"
              :style="{ paddingLeft: it.group === '分组' ? '14px' : '38px' }"
              @mouseenter="activeIndex = i"
              @click="run(it)"
            >
              <span v-if="it.group !== '分组'" class="cp-item-icon" aria-hidden="true">{{ it.icon || '·' }}</span>
              <span class="cp-item-name">{{ it.name }}</span>
              <span v-if="it.desc" class="cp-item-desc">{{ it.desc }}</span>
              <span v-if="it.kbd" class="cp-item-kbd">{{ it.kbd }}</span>
            </button>
          </template>
        </div>

        <footer class="cp-foot">
          <span class="cp-foot-hint"><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
          <span class="cp-foot-hint"><kbd>↵</kbd> 执行</span>
          <span class="cp-foot-hint"><kbd>esc</kbd> 关闭</span>
          <span class="cp-foot-brand">玄黄 · 命令面板</span>
        </footer>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 单例：所有组件实例共享 open / open()
const open = ref(false)
const query = ref('')
const activeIndex = ref(0)
const inputRef = ref(null)
const panelRef = ref(null)
const listRef = ref(null)

const COMMANDS = [
  // 分组标题
  { group: '分组', name: '工作台' },
  { key: 'g.workbench', name: '工作台', desc: '首页数据一览', icon: '◇', keywords: 'home dashboard', action: () => router.push('/workbench') },
  { key: 'g.profile', name: '个人中心', desc: '账号 / 主题 / 安装应用', icon: '◈', keywords: 'profile me', action: () => router.push('/profile') },

  { group: '分组', name: '记录' },
  { key: 'g.notes', name: '笔记', desc: '所有笔记', icon: '✎', keywords: 'note', action: () => router.push('/notes') },
  { key: 'g.notes.new', name: '新建笔记', desc: '打开编辑器', icon: '✎', keywords: 'create note', action: () => router.push('/notes/new') },
  { key: 'g.finance', name: '记账', desc: '收支流水 / 月度报表', icon: '¥', keywords: 'money bill', action: () => router.push('/finance') },
  { key: 'g.tasks', name: '任务', icon: '☐', keywords: 'todo', action: () => router.push('/tasks') },
  { key: 'g.contacts', name: '通讯录', icon: '☎', keywords: 'people phone', action: () => router.push('/contacts') },
  { key: 'g.subscriptions', name: '订阅', icon: '↻', keywords: 'subscription', action: () => router.push('/subscriptions') },
  { key: 'g.diary', name: '速记', icon: '✐', keywords: 'quick diary', action: () => router.push('/diary') },

  { group: '分组', name: '数据' },
  { key: 'g.travels', name: '足迹', desc: '旅行地图 / 城市', icon: '✈', keywords: 'travel map', action: () => router.push('/travels') },
  { key: 'g.stocks', name: '自选股', icon: '↑', keywords: 'stock', action: () => router.push('/stocks') },
  { key: 'g.feeds', name: '资讯流', icon: '☷', keywords: 'rss feed', action: () => router.push('/feeds') },
  { key: 'g.countdowns', name: '倒计时', icon: '◷', keywords: 'countdown', action: () => router.push('/tool/countdown') },
  { key: 'g.datahub', name: '数据中心', icon: '◉', keywords: 'data hub', action: () => router.push('/datahub') },

  { group: '分组', name: '工具 / 媒体' },
  { key: 'g.tool', name: '工具箱', icon: '⚒', keywords: 'tool', action: () => router.push('/tool') },
  { key: 'g.tool.watermark', name: '水印工具', icon: '⚒', action: () => router.push('/tool/watermark') },
  { key: 'g.tool.pdf', name: 'PDF 工具', icon: '⚒', action: () => router.push('/tool/pdf') },
  { key: 'g.tool.compress', name: '图片压缩', icon: '⚒', action: () => router.push('/tool/compress') },
  { key: 'g.tool.idphoto', name: '证件照', icon: '⚒', action: () => router.push('/tool/idphoto') },
  { key: 'g.tool.cover', name: 'AI 封面', icon: '⚒', action: () => router.push('/tool/cover') },
  { key: 'g.tool.voice', name: '音色克隆', icon: '⚒', action: () => router.push('/tool/voice') },

  { group: '分组', name: '内容 / 媒体库' },
  { key: 'g.music', name: '音乐库', icon: '♪', keywords: 'music audio bgm', action: () => router.push('/music') },
  { key: 'g.novel', name: '小说', icon: '✦', keywords: 'novel book', action: () => router.push('/novel') },
  { key: 'g.video', name: '视频', icon: '▶', keywords: 'video', action: () => router.push('/video') },

  { group: '分组', name: '动作' },
  { key: 'a.theme.day', name: '切换日间主题', desc: '明亮白天', icon: '☀', keywords: 'theme day light', action: () => setTheme('day') },
  { key: 'a.theme.night', name: '切换夜间主题', desc: '深邃夜幕', icon: '☾', keywords: 'theme night dark', action: () => setTheme('night') },
  { key: 'a.theme.toggle', name: '主题切换', desc: '日夜交替', icon: '◑', keywords: 'theme toggle', kbd: '⇧D', action: () => setTheme(document.documentElement.dataset.theme === 'day' ? 'night' : 'day') },

  { group: '分组', name: '键盘快捷键' },
  { key: 'a.shortcut.g', name: 'g + w · 工作台', desc: 'GitHub 风格快捷键', icon: '⌨', action: () => { close(); router.push('/workbench') }, kbd: 'g w' },
  { key: 'a.shortcut.n', name: 'g + n · 笔记', icon: '⌨', action: () => { close(); router.push('/notes') }, kbd: 'g n' },
  { key: 'a.shortcut.f', name: 'g + f · 记账', icon: '⌨', action: () => { close(); router.push('/finance') }, kbd: 'g f' },
  { key: 'a.shortcut.c', name: 'g + c · 倒计时', icon: '⌨', action: () => { close(); router.push('/tool/countdown') }, kbd: 'g c' },
  { key: 'a.ai', name: '打开 AI 助手', icon: '✺', keywords: 'assistant ai', action: () => router.push('/assistant') },
  { key: 'a.logout', name: '退出登录', desc: '清除当前会话', icon: '⏻', keywords: 'logout signout', action: () => logout() },
  { key: 'a.download', name: '下载手机 App', desc: 'Android / 鸿蒙 / iOS 引导页', icon: '↓', keywords: 'download app apk', action: () => window.open('/download/', '_blank') },
]

const items = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return COMMANDS
  return COMMANDS
    .map((it) => {
      if (it.group) {
        // 分组标题：若组内没有匹配项则隐藏，否则保留
        return { ...it, _hideGroup: true }
      }
      const hay = (it.name + ' ' + (it.desc || '') + ' ' + (it.keywords || '') + ' ' + it.key).toLowerCase()
      const score = q.split(/\s+/).reduce((s, term) => s + (hay.includes(term) ? 1 : 0), 0)
      return { ...it, _score: score }
    })
    .filter((it) => it.group || it._score > 0)
    .map((it) => {
      if (!it.group) return it
      // 分组：检查其后面紧邻命令是否有匹配（用 reduce）
      const idx = COMMANDS.findIndex((c) => c === it)
      const next = COMMANDS.slice(idx + 1).findIndex((c) => c.group)
      const sliceEnd = next === -1 ? COMMANDS.length : idx + 1 + next
      const hasMatch = COMMANDS.slice(idx + 1, sliceEnd).some((c) => !c.group)
      return hasMatch ? it : null
    })
    .filter(Boolean)
})

watch(query, () => { activeIndex.value = 0 })

watch(items, () => {
  // 让滚动跟随 activeIndex
  nextTick(() => {
    if (!listRef.value) return
    const el = listRef.value.querySelector(`#cp-item-${activeIndex.value}`)
    if (el) el.scrollIntoView({ block: 'nearest' })
  })
})

function openPanel() {
  open.value = true
  query.value = ''
  activeIndex.value = 0
  nextTick(() => inputRef.value?.focus())
}

function close() { open.value = false }

function run(it) {
  if (!it || it.group) return
  close()
  // 等待关闭动画完成再执行
  setTimeout(() => { try { it.action() } catch (e) { console.error('[CommandPalette] action failed:', e) } }, 80)
}

function onKey(e) {
  // ⌘K / Ctrl+K 唤起/关闭
  const mod = e.metaKey || e.ctrlKey
  if (mod && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    open.value ? close() : openPanel()
    return
  }
  if (!open.value) return
  if (e.key === 'Escape') { e.preventDefault(); close() }
  else if (e.key === 'ArrowDown' || (e.key === 'j' && !e.shiftKey)) {
    e.preventDefault(); move(1)
  }
  else if (e.key === 'ArrowUp' || (e.key === 'k' && !e.shiftKey)) {
    e.preventDefault(); move(-1)
  }
  else if (e.key === 'Enter') {
    e.preventDefault()
    run(items.value[activeIndex.value])
  }
}

function move(delta) {
  const list = items.value.filter((it) => !it.group)
  if (!list.length) return
  // 只在可执行项之间游走
  let cur = activeIndex.value
  for (let i = 0; i < items.value.length; i++) {
    if (items.value[i] === list[Math.max(0, list.indexOf(items.value[cur]))]) { cur = i; break }
  }
  let next = cur
  do {
    next = (next + delta + items.value.length) % items.value.length
    if (next === cur) break
  } while (items.value[next].group)
  activeIndex.value = next
}

function setTheme(t) {
  document.documentElement.dataset.theme = t
  try { localStorage.setItem('yx_theme', t) } catch {}
  // 触发后端记录偏好（如有则不阻塞）
  try { fetch('/api/settings/theme', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ theme: t }) }).catch(() => {}) } catch {}
}

function logout() {
  try {
    localStorage.removeItem('yx_token')
    localStorage.removeItem('yx_user')
    sessionStorage.clear()
  } catch {}
  window.location.href = '/login'
}

onMounted(() => { window.addEventListener('keydown', onKey) })
onBeforeUnmount(() => { window.removeEventListener('keydown', onKey) })

// 暴露给外部 trigger（如顶栏按钮点击）
defineExpose({ open: openPanel, close })
</script>

<style scoped>
.cp-mask {
  position: fixed; inset: 0;
  background: rgba(8, 12, 24, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  z-index: 9999;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 14vh 20px 20px;
}
.cp-panel {
  width: 100%;
  max-width: 620px;
  background: var(--dp-surface, #161b2c);
  border: 1px solid var(--dp-line, rgba(126, 136, 243, 0.25));
  border-radius: 14px;
  box-shadow: 0 24px 60px rgba(0,0,0,0.45), 0 0 0 1px rgba(126, 136, 243, 0.06);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 70vh;
}
.cp-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--dp-line, rgba(126, 136, 243, 0.2));
}
.cp-search-icon {
  font-size: 14px;
  color: var(--dp-text3, #94a3b8);
  width: 22px;
  text-align: center;
  border: 1px solid var(--dp-line, rgba(126,136,243,0.3));
  border-radius: 6px;
  padding: 1px 0;
}
.cp-input {
  flex: 1;
  background: transparent;
  border: 0;
  outline: 0;
  font-size: 15px;
  color: var(--dp-text, #f4f4f7);
  font-family: inherit;
}
.cp-input::placeholder { color: var(--dp-text3, #6b7793); }
.cp-kbd {
  font-size: 11px;
  color: var(--dp-text3, #94a3b8);
  padding: 2px 6px;
  border: 1px solid var(--dp-line, rgba(126,136,243,0.25));
  border-radius: 4px;
}
.cp-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 6px 12px;
  scrollbar-width: thin;
}
.cp-empty {
  padding: 36px 16px;
  text-align: center;
  color: var(--dp-text3, #6b7793);
  font-size: 13px;
}
.cp-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  text-align: left;
  padding: 8px 12px;
  border: 0;
  background: transparent;
  color: var(--dp-text, #f4f4f7);
  font-size: 14px;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
}
.cp-item.group {
  font-size: 11px;
  color: var(--dp-text3, #94a3b8);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 12px 14px 4px;
  cursor: default;
  font-weight: 600;
}
.cp-item.group:hover { background: transparent; }
.cp-item.active {
  background: linear-gradient(180deg, rgba(126, 136, 243, 0.22), rgba(126, 136, 243, 0.12));
  box-shadow: inset 0 0 0 1px rgba(126, 136, 243, 0.4);
}
.cp-item-icon {
  width: 22px;
  text-align: center;
  color: var(--dp-accent, #67e8f9);
  font-size: 14px;
  flex: 0 0 22px;
}
.cp-item-name { flex: 0 0 auto; }
.cp-item-desc {
  color: var(--dp-text3, #94a3b8);
  font-size: 12px;
  margin-left: auto;
  padding-left: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cp-item-kbd {
  font-size: 10.5px;
  color: var(--dp-text3, #94a3b8);
  padding: 2px 6px;
  border: 1px solid var(--dp-line, rgba(126,136,243,0.25));
  border-radius: 4px;
  margin-left: 8px;
  letter-spacing: 0.04em;
}
.cp-foot {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 8px 16px;
  border-top: 1px solid var(--dp-line, rgba(126,136,243,0.2));
  font-size: 11.5px;
  color: var(--dp-text3, #94a3b8);
}
.cp-foot-hint { display: inline-flex; gap: 4px; align-items: center; }
.cp-foot-brand { margin-left: auto; letter-spacing: 0.16em; opacity: 0.7; }
.cp-foot kbd {
  font-family: inherit;
  font-size: 10.5px;
  padding: 1px 5px;
  border: 1px solid var(--dp-line, rgba(126,136,243,0.3));
  border-radius: 4px;
  background: rgba(255,255,255,0.02);
}

.cp-fade-enter-active, .cp-fade-leave-active { transition: opacity .18s ease; }
.cp-fade-enter-from, .cp-fade-leave-to { opacity: 0; }
.cp-fade-enter-active .cp-panel, .cp-fade-leave-active .cp-panel {
  transition: transform .18s ease, opacity .18s ease;
}
.cp-fade-enter-from .cp-panel { transform: translateY(-12px) scale(0.98); opacity: 0; }
.cp-fade-leave-to .cp-panel { transform: translateY(-6px); opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .cp-fade-enter-active, .cp-fade-leave-active { transition: none; }
  .cp-fade-enter-from .cp-panel, .cp-fade-leave-to .cp-panel { transform: none; }
}

/* 浅色主题适配 */
:root[data-theme="day"] .cp-mask { background: rgba(240, 244, 250, 0.65); }
</style>