<template>
  <header class="lj-topbar" :class="{ collapsed: collapsed }" ref="topbarRef">
    <!-- 品牌 + 回工作台 -->
    <div class="tb-brand" @click="go('/workbench')" title="返回工作台">
      <svg class="tb-logo" viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3" y="2" width="18" height="20" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/>
        <path d="M12 6 L15 10 L12 14 L9 10 Z" fill="currentColor" opacity="0.85"/>
      </svg>
      <span class="tb-brand-text">玄 黄</span>
    </div>

    <!-- 全站导航 -->
    <nav class="tb-nav" aria-label="全站导航">
      <a v-for="item in navItems" :key="item.to" class="tb-nav-item" :class="{ active: isActive(item) }" @click="go(item.to)">
        <el-icon class="tb-nav-icon"><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </a>
    </nav>

    <!-- 全局搜索（即时联想） -->
    <div class="tb-search" :class="{ 'is-mobile': isMobileInput }">
      <el-input
        v-model="searchWord"
        class="tb-search-input"
        placeholder="搜笔记 / 资产 / 任务 / 标签"
        clearable
        :size="isMobile ? 'default' : 'large'"
        @input="onSearchInput"
        @keyup.enter="runSearch"
        @focus="searchFocus = true"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>

      <!-- 联想面板 -->
      <transition name="fade-drop">
        <div v-if="searchFocus && suggestions && suggestions.count" class="tb-suggest">
          <template v-for="(group, gkey) in suggestGroups" :key="gkey">
            <div v-if="group.items.length" class="suggest-group">
              <div class="suggest-head">{{ group.title }}</div>
              <div
                v-for="it in group.items"
                :key="gkey + '-' + it.id"
                class="suggest-item"
                @mousedown.prevent="go(group.to(it))"
              >
                <el-icon class="suggest-icon"><component :is="group.icon" /></el-icon>
                <span class="suggest-label">{{ group.label(it) }}</span>
              </div>
            </div>
          </template>
          <div v-if="!suggestions.count" class="suggest-empty">无匹配结果</div>
        </div>
      </transition>
    </div>

    <!-- 右侧：移动搜索icon + 音频 + 用户区 -->
    <div class="tb-right">
      <button class="tb-icon-btn tb-search-toggle" @click="toggleMobileSearch" title="搜索">
        <el-icon><Search /></el-icon>
      </button>

      <!-- 音频控制（内联面板，不弹窗） -->
      <el-dropdown trigger="click" placement="bottom-end" :show-arrow="false">
        <button class="tb-icon-btn" :title="player.isPlaying ? '音频（播放中）' : '音频'">
          <el-icon><Headset /></el-icon>
          <span class="tb-audio-dot" :class="{ off: !player.isPlaying }"></span>
        </button>
        <template #dropdown>
          <div class="tb-audio-panel" @click.stop>
            <div class="tb-panel-title">音频面板</div>

            <!-- 背景音乐选择 -->
            <div class="tb-audio-seg">
              <div class="tb-seg-head" @click="bgmListOpen = !bgmListOpen">
                <span class="tb-audio-label">背景音乐</span>
                <span class="tb-bgm-cur">{{ curBgmName }}</span>
                <el-icon class="tb-seg-arrow" :class="{ open: bgmListOpen }"><CaretBottom /></el-icon>
              </div>
              <transition name="fade-drop">
                <div v-if="bgmListOpen" class="tb-bgm-list">
                  <div
                    v-for="it in player.musicLibrary"
                    :key="it.id"
                    class="tb-bgm-item"
                    :class="{ active: String(it.id) === String(player.bgmChoiceId) }"
                    @click="chooseBgm(it)"
                  >
                    <span class="tb-bgm-name">{{ it.title }}</span>
                    <el-icon v-if="String(it.id) === String(player.bgmChoiceId)" class="tb-bgm-check"><Check /></el-icon>
                  </div>
                  <div v-if="!player.musicLibrary.length" class="tb-bgm-empty">音乐库为空</div>
                </div>
              </transition>
            </div>

            <!-- 音量 -->
            <div class="tb-audio-row">
              <span class="tb-audio-label">音量</span>
              <div class="tb-knob" @mousedown.prevent="startVolDrag($event)">
                <div class="tb-knob-fill" :style="{ width: player.volume * 100 + '%' }"></div>
                <span class="tb-knob-thumb" :style="{ left: player.volume * 100 + '%' }"></span>
              </div>
            </div>
          </div>
        </template>
      </el-dropdown>

      <!-- 用户区 -->
      <el-dropdown trigger="click" @command="onCommand">
        <div class="tb-user">
          <span class="tb-avatar">{{ avatarText }}</span>
          <span class="tb-user-name">{{ userName }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="workbench"><el-icon><Grid /></el-icon>返回工作台</el-dropdown-item>
            <el-dropdown-item command="profile"><el-icon><User /></el-icon>个人中心</el-dropdown-item>
            <el-dropdown-item divided command="password"><el-icon><Lock /></el-icon>修改密码</el-dropdown-item>
            <el-dropdown-item command="avatar"><el-icon><Avatar /></el-icon>选择头像</el-dropdown-item>
            <el-dropdown-item v-if="auth.isSuperAdmin" divided command="admin"><el-icon><Tools /></el-icon>管理后台</el-dropdown-item>
            <el-dropdown-item command="logout" divided><el-icon><SwitchButton /></el-icon>退出账号</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- 收起态悬浮按钮 -->
    <button v-if="collapsed" class="tb-mini" @click="expand" title="展开顶栏">
      <el-icon><Expand /></el-icon>
    </button>
  </header>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  Grid, User, Lock, Avatar, Tools, SwitchButton, Search, Headset, Expand, CaretBottom,
  Document, FolderOpened, Check, PriceTag
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import { workbenchApi } from '@/api/workbench'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const player = usePlayerStore()

const topbarRef = ref(null)
const collapsed = ref(false)
const searchWord = ref('')
const searchFocus = ref(false)
let suggestTimer = null

/* ---- 导航 ---- */
const navItems = [
  { label: '笔记', to: '/notes', icon: Document },
  { label: '任务', to: '/tasks', icon: Check },
  { label: '内容资产', to: '/assets', icon: FolderOpened }
]
function isActive(item) {
  return route.path.startsWith(item.to)
}
function go(path) {
  router.push(path)
}

/* ---- 用户区 ---- */
const avatarOptions = [{ id: 1, emoji: '🌙' }, { id: 2, emoji: '☁️' }]
const avatarText = computed(() => {
  const id = Number(localStorage.getItem('avatar_id') || 1)
  return avatarOptions.find(a => a.id === id)?.emoji || '🌙'
})
const userName = computed(() => auth.user?.nickname || auth.user?.name || auth.user?.email || '道友')

/* ---- 音频控制（接 player store）---- */
const bgmListOpen = ref(false)

const curBgmName = computed(() => {
  const id = player.bgmChoiceId
  const it = player.musicLibrary.find(x => String(x.id) === String(id))
  return it ? it.title : '默认古筝'
})

function chooseBgm(item) {
  player.setBackground(item, true)
  bgmListOpen.value = false
}

function startVolDrag(e) {
  const track = e.currentTarget
  const apply = (ev) => {
    const r = track.getBoundingClientRect()
    player.setVolume(Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)))
  }
  apply(e)
  const move = (ev) => apply(ev)
  const up = () => {
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
  }
  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
}

/* ---- 下拉命令 ---- */
function onCommand(cmd) {
  switch (cmd) {
    case 'workbench': router.push('/workbench'); break
    case 'profile': router.push('/profile'); break
    case 'admin': router.push('/admin'); break
    case 'logout':
      auth.logoutAction()
      router.push('/login')
      break
    case 'password':
    case 'avatar':
      ElMessage.warning('请前往个人中心设置')
      break
  }
}

/* ---- 全局搜索联想 ---- */
const suggestions = ref({ results: null, count: 0 })
const suggestGroups = computed(() => {
  const r = suggestions.value.results || {}
  return [
    {
      key: 'notes', title: '笔记', icon: Document,
      items: r.notes || [],
      label: (it) => it?.title || '（无标题）',
      to: (it) => `/notes/${it?.id}`
    },
    {
      key: 'tasks', title: '任务', icon: Check,
      items: r.tasks || [],
      label: (it) => it?.title || '任务',
      to: () => '/tasks'
    },
    {
      key: 'assets', title: '内容资产', icon: FolderOpened,
      items: r.assets || [],
      label: (it) => it?.title || it?.original_filename || '资产',
      to: () => '/assets'
    },
    {
      key: 'tags', title: '标签', icon: PriceTag,
      items: r.tags || [],
      label: (it) => '#' + it?.name,
      to: (it) => `/notes?tag=${encodeURIComponent(it?.name || '')}`
    }
  ]
})

function onSearchInput() {
  clearTimeout(suggestTimer)
  const q = (searchWord.value || '').trim()
  if (!q) {
    suggestions.value = { results: null, count: 0 }
    return
  }
  suggestTimer = setTimeout(async () => {
    try {
      const res = await workbenchApi.search(q, { size: 6 })
      const results = res?.data?.results || {}
      const count = (results.notes?.length || 0) + (results.tasks?.length || 0) +
        (results.assets?.length || 0) + (results.tags?.length || 0)
      suggestions.value = { results, count }
    } catch {
      suggestions.value = { results: null, count: 0 }
    }
  }, 260)
}

function runSearch() {
  const q = (searchWord.value || '').trim()
  searchFocus.value = false
  if (!q) return
  router.push({ path: '/notes', query: { q } })
  suggestions.value = { results: null, count: 0 }
}

/* ---- 移动端 ---- */
const isMobile = ref(false)
const isMobileInput = ref(false)
function checkMobile() { isMobile.value = window.innerWidth < 768 }
function toggleMobileSearch() {
  isMobileInput.value = true
  // 聚焦输入框
  setTimeout(() => topbarRef.value?.querySelector('input')?.focus(), 50)
}

/* ---- 滚动收起 ---- */
let lastY = 0
function onScroll() {
  const y = window.scrollY
  if (y > 160 && y > lastY) collapsed.value = true
  else if (y < lastY || y < 200) collapsed.value = false
  lastY = y
}
function expand() { collapsed.value = false }

onMounted(async () => {
  await player.initBgm()
  checkMobile()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', checkMobile)
  document.addEventListener('mousedown', onDocDown)
})

function onDocDown(e) {
  if (!topbarRef.value?.contains(e.target)) searchFocus.value = false
}

onUnmounted(() => {
  clearTimeout(suggestTimer)
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', checkMobile)
  document.removeEventListener('mousedown', onDocDown)
})
</script>

<style scoped>
.lj-topbar {
  --tb-h: 60px;
  position: fixed;
  top: 0; left: 0; right: 0;
  height: var(--tb-h);
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 22px;
  background: var(--lj-glass);
  -webkit-backdrop-filter: var(--lj-glass-blur);
  backdrop-filter: var(--lj-glass-blur);
  border-bottom: 1px solid var(--lj-line);
  box-shadow: 0 1px 10px rgba(58, 67, 80, 0.05);
  box-sizing: border-box;
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.lj-topbar.collapsed { transform: translateY(-100%); }
.lj-topbar.expanding { transform: translateY(0); }

.tb-brand { display: flex; align-items: center; gap: 8px; cursor: pointer; flex: none; color: var(--lj-dai); }
.tb-logo { width: 26px; height: 26px; }
.tb-brand-text {
  font-family: var(--font-serif);
  font-size: 18px; font-weight: 600; letter-spacing: 0.3em;
  color: var(--lj-text);
}

.tb-nav { display: flex; gap: 4px; flex: none; }
.tb-nav-item {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 12px; border-radius: 8px;
  font-size: 13px; color: var(--lj-text-2); cursor: pointer;
  transition: all 0.25s;
}
.tb-nav-item:hover { color: var(--lj-dai); background: rgba(74, 95, 99, 0.06); }
.tb-nav-item.active { color: var(--lj-dai); background: rgba(74, 95, 99, 0.1); font-weight: 600; }
.tb-nav-icon { font-size: 15px; }

.tb-search { position: relative; flex: 1; max-width: 460px; }
.tb-search-input :deep(.el-input__wrapper) {
  background: rgba(251, 250, 246, 0.7);
  border-radius: 999px;
  box-shadow: 0 0 0 1px var(--lj-line) inset;
  padding-left: 14px;
}
.tb-search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--lj-dai) inset, 0 0 0 3px rgba(74, 95, 99, 0.1);
}

/* 联想面板 */
.tb-suggest {
  position: absolute; top: calc(100% + 8px); left: 0; right: 0;
  background: var(--lj-paper);
  border: 1px solid var(--lj-line);
  border-radius: 12px;
  box-shadow: var(--lj-shadow);
  overflow: hidden;
  z-index: 100;
}
.suggest-group { padding: 6px 0; }
.suggest-group + .suggest-group { border-top: 1px solid var(--lj-line); }
.suggest-head { padding: 4px 16px; font-size: 11px; color: var(--lj-text-3); letter-spacing: 0.15em; }
.suggest-item {
  display: flex; align-items: center; gap: 8px; padding: 8px 16px;
  font-size: 13px; color: var(--lj-text-2); cursor: pointer;
}
.suggest-item:hover { background: rgba(74, 95, 99, 0.06); color: var(--lj-dai); }
.suggest-icon { font-size: 14px; }
.suggest-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.suggest-empty { padding: 14px 16px; font-size: 13px; color: var(--lj-text-3); }

.fade-drop-enter-active, .fade-drop-leave-active { transition: all 0.18s ease; }
.fade-drop-enter-from, .fade-drop-leave-to { opacity: 0; transform: translateY(-4px); }

.tb-right { display: flex; align-items: center; gap: 8px; margin-left: auto; flex: none; }

.tb-icon-btn {
  position: relative;
  width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--lj-line); border-radius: 10px; background: rgba(251, 250, 246, 0.6);
  color: var(--lj-text-2); font-size: 16px; cursor: pointer; transition: all 0.25s;
}
.tb-icon-btn:hover { color: var(--lj-dai); border-color: var(--lj-line-strong); background: #fff; }
.tb-audio-dot {
  position: absolute; top: 5px; right: 5px; width: 6px; height: 6px; border-radius: 50%;
  background: var(--lj-ochre);
}
.tb-audio-dot.off { background: var(--lj-vermilion); }

/* 音频面板 */
.tb-audio-panel { width: 240px; padding: 14px 16px; }
.tb-panel-title { font-size: 13px; color: var(--lj-text); font-weight: 600; margin-bottom: 12px; letter-spacing: 0.05em; }
.tb-audio-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.tb-audio-label { font-size: 12px; color: var(--lj-text-2); width: 60px; flex: none; }
.tb-knob {
  flex: 1; height: 5px; border-radius: 999px; background: rgba(74, 95, 99, 0.15);
  position: relative; cursor: pointer;
}
.tb-knob-fill { position: absolute; inset: 0; right: auto; border-radius: 999px; background: var(--lj-dai); }
.tb-knob-thumb {
  position: absolute; top: 50%; width: 14px; height: 14px; border-radius: 50%;
  background: #fff; border: 2px solid var(--lj-dai);
  transform: translate(-50%, -50%);
}

/* 背景音乐选择折叠区 */
.tb-audio-seg { margin-bottom: 10px; }
.tb-seg-head {
  display: flex; align-items: center; gap: 6px; cursor: pointer;
  padding: 6px 4px; border-radius: 8px;
}
.tb-seg-head:hover { background: rgba(74, 95, 99, 0.06); }
.tb-bgm-cur {
  flex: 1; text-align: right; font-size: 12px; color: var(--lj-dai);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 100px;
}
.tb-seg-arrow { font-size: 12px; color: var(--lj-text-2); transition: transform 0.2s; }
.tb-seg-arrow.open { transform: rotate(180deg); }
.tb-bgm-list {
  max-height: 200px; overflow-y: auto; margin-top: 4px;
  border-top: 1px solid var(--lj-line); padding: 6px 0;
}
.tb-bgm-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 8px; border-radius: 8px; cursor: pointer;
}
.tb-bgm-item:hover { background: rgba(74, 95, 99, 0.06); }
.tb-bgm-item.active { background: rgba(112, 150, 170, 0.14); }
.tb-bgm-name {
  flex: 1; font-size: 13px; color: var(--lj-text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tb-bgm-item.active .tb-bgm-name { color: var(--lj-dai); font-weight: 600; }
.tb-bgm-check { font-size: 14px; color: var(--lj-dai); }
.tb-bgm-empty { padding: 10px 8px; color: var(--lj-text-2); font-size: 12px; text-align: center; }

.tb-user { display: flex; align-items: center; gap: 8px; cursor: pointer; padding: 4px 8px; border-radius: 10px; }
.tb-user:hover { background: rgba(74, 95, 99, 0.06); }
.tb-avatar {
  width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--lj-line-strong); border-radius: 10px; background: var(--lj-paper);
  font-size: 18px;
}
.tb-user-name { font-size: 13px; color: var(--lj-text); }

/* 收起态悬浮按钮 */
.tb-mini {
  position: fixed; top: 8px; right: 22px; z-index: 999;
  width: 40px; height: 40px; display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid var(--lj-line); border-radius: 12px; background: var(--lj-glass);
  -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  color: var(--lj-dai); font-size: 18px; cursor: pointer;
  box-shadow: var(--lj-shadow);
}

.tb-search-toggle { display: none; }

@media (max-width: 767px) {
  .tb-nav { display: none; }
  .tb-search { display: none; }
  .tb-search.is-mobile { display: block; max-width: none; flex: 1; }
  .tb-search-toggle { display: inline-flex; }
  .tb-user-name { display: none; }
}
</style>