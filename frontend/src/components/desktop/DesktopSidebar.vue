<template>
  <!-- 桌面端侧栏：登录后所有桌面页面统一左导航 + 顶栏保持不变 -->
  <aside class="dsb" :class="{ collapsed: !expanded }" :aria-label="'主导航'">
    <!-- 顶部：品牌 + 折叠按钮 + 全局搜索 -->
    <div class="dsb-head">
      <div class="dsb-head-row">
        <div class="dsb-brand" @click="go('/workbench')" title="返回工作台">
          <span class="dsb-brand-rune">玄</span>
          <span class="dsb-brand-text">玄 黄</span>
        </div>
        <button
          class="dsb-toggle"
          :title="expanded ? '收起侧栏' : '展开侧栏'"
          :aria-label="expanded ? '收起侧栏' : '展开侧栏'"
          @click="toggle"
        >
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            <path
              :d="expanded ? 'M15 6 L9 12 L15 18' : 'M9 6 L15 12 L9 18'"
              fill="none"
              stroke="currentColor"
              stroke-width="1.9"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>
      <!-- 全局搜索（原顶栏搜索迁移到此） -->
      <DesktopSearchBox class="dsb-search" />
    </div>

    <!-- 滚动菜单区 -->
    <nav class="dsb-nav">
      <template v-for="(group, gi) in groups" :key="group.label">
        <div v-if="group.label" class="dsb-group-label">{{ group.label }}</div>

        <RouterLink
          v-for="item in group.items"
          :key="item.path"
          :to="item.path"
          class="dsb-item"
          :class="{ active: isActive(item.path), 'super-only': item.superOnly }"
        >
          <span class="dsb-ic" aria-hidden="true">
            <component :is="item.icon" />
          </span>
          <span class="dsb-label">{{ item.title }}</span>
        </RouterLink>

        <div v-if="gi < groups.length - 1" class="dsb-divider" aria-hidden="true"></div>
      </template>
    </nav>

    <!-- 底部信息 -->
    <div class="dsb-foot">
      <span>v2.36.0</span>
    </div>
  </aside>

  <!-- 折叠态的浮动展开按钮（侧栏完全隐藏后仍可唤出） -->
  <button
    v-if="!expanded"
    class="dsb-open-fab"
    title="展开侧栏"
    aria-label="展开侧栏"
    @click="toggle"
  >
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path d="M4 6h16M4 12h16M4 18h16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" />
    </svg>
  </button>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import {
  House,
  Headset,
  Reading,
  VideoPlay,
  EditPen,
  Bell,
  MapLocation,
  Money,
  TrendCharts,
  Notebook,
  List,
  Calendar,
  ChatLineRound,
  Connection,
  Compass,
  Coin,
  UserFilled,
  Lock,
  Menu,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import DesktopSearchBox from './DesktopSearchBox.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

/* ---------- 折叠状态（按用户持久化；折叠 = 侧栏完全隐藏，仅留浮动唤出按钮） ---------- */
const STORAGE_KEY = 'xh_desktop_sidebar_collapsed'
/* 窄屏（≤900）侧栏是浮层抽屉：默认折叠，避免一进页面就压住内容 */
const NARROW_W = 900
const expanded = ref(true)
function isNarrow() {
  return typeof window !== 'undefined' && window.innerWidth <= NARROW_W
}
function loadCollapsed() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === '1') { expanded.value = false; return }
    if (saved === '0') { expanded.value = true; return }
  } catch { /* ignore */ }
  // 无用户偏好时：窄屏默认收起
  expanded.value = !isNarrow()
}
function toggle() {
  expanded.value = !expanded.value
  try { localStorage.setItem(STORAGE_KEY, expanded.value ? '0' : '1') } catch { /* ignore */ }
}

onMounted(loadCollapsed)

/* 窄屏抽屉：跳转后自动收起，避免浮层一直压着内容 */
watch(() => route.path, () => { if (isNarrow()) expanded.value = false })

/* ---------- 菜单分组 ---------- */
const isSuper = computed(() => auth.user?.role === 'super_admin' || auth.user?.is_super_admin === 1)

const groups = computed(() => {
  const base = [
    {
      label: '',
      items: [
        { path: '/workbench', title: '工作台', icon: House },
      ],
    },
    {
      label: '内容',
      items: [
        { path: '/music', title: '音乐', icon: Headset },
        { path: '/novel', title: '小说', icon: Reading },
        { path: '/video', title: '视频', icon: VideoPlay },
        { path: '/log', title: '日志', icon: EditPen },
        { path: '/tool', title: '工具', icon: Bell },
        { path: '/notes', title: '笔记云台', icon: Notebook },
      ],
    },
    {
      label: '生活',
      items: [
        { path: '/tool/countdown', title: '时光痕迹', icon: Calendar },
        { path: '/travels', title: '足迹地图', icon: MapLocation },
        { path: '/finance', title: '记账', icon: Money },
        { path: '/stocks', title: '股票', icon: TrendCharts },
        { path: '/feeds', title: '资讯', icon: Connection },
      ],
    },
    {
      label: '家',
      items: [
        { path: '/contacts', title: '通讯录', icon: Compass },
        { path: '/subscriptions', title: '订阅', icon: Coin },
        { path: '/tasks', title: '待办', icon: List },
      ],
    },
    {
      label: '智能',
      items: [
        { path: '/assistant', title: 'AI 对话', icon: ChatLineRound },
      ],
    },
  ]

  if (isSuper.value) {
    base.push({
      label: '管理',
      items: [
        { path: '/admin/users', title: '用户管理', icon: UserFilled, superOnly: true },
        { path: '/admin/roles', title: '角色管理', icon: Lock, superOnly: true },
        { path: '/admin/menus', title: '菜单管理', icon: Menu, superOnly: true },
      ],
    })
  }
  return base
})

/* ---------- 路由匹配高亮 ---------- */
function isActive(path) {
  if (path === '/workbench') return route.path === '/workbench'
  if (path === '/notes') return route.path === '/notes' || route.path.startsWith('/notes/')
  if (path === '/tool/countdown') return route.path.startsWith('/tool/countdown')
  if (path === '/tool') return route.path === '/tool' || (route.path.startsWith('/tool/') && !route.path.startsWith('/tool/countdown'))
  if (path === '/admin/users') return route.path === '/admin' || route.path === '/admin/users'
  return route.path === path || route.path.startsWith(path + '/')
}

function go(path) { router.push(path) }
</script>

<style scoped>
.dsb {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 90;
  width: 220px;
  display: flex;
  flex-direction: column;
  background: var(--dp-surface);
  border-right: 1px solid var(--dp-line);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  overflow: hidden;
  transition: transform .24s cubic-bezier(.4, 0, .2, 1), opacity .18s ease;
}
:root[data-theme="night"] .dsb {
  background: rgba(22, 19, 38, .72);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  backdrop-filter: blur(16px) saturate(160%);
}
/* 折叠 = 完全隐藏（整条移出视口） */
.dsb.collapsed {
  transform: translateX(-100%);
  opacity: 0;
  pointer-events: none;
}

/* ---------- 顶部：品牌 + 折叠按钮同行，下方全局搜索 ---------- */
.dsb-head {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 12px 12px;
  border-bottom: 1px solid var(--dp-line);
  flex-shrink: 0;
}
.dsb-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.dsb-search { width: 100%; }
.dsb-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  cursor: pointer;
  min-width: 0;
  flex: 1;
}
.dsb-brand-rune {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--dp-accent), var(--dp-accent-strong));
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px var(--dp-accent-faint);
}
.dsb-brand-text {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: .02em;
  white-space: nowrap;
  color: var(--dp-text);
  overflow: hidden;
  text-overflow: ellipsis;
}

.dsb-toggle {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 6px;
  background: transparent;
  border: 1px solid var(--dp-line);
  color: var(--dp-text3);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  transition: all .15s;
}
.dsb-toggle:hover {
  color: var(--dp-accent);
  border-color: var(--dp-accent);
  background: var(--dp-accent-faint);
}

/* ---------- 折叠态的浮动展开按钮 ---------- */
.dsb-open-fab {
  position: fixed;
  top: 72px;
  left: 14px;
  z-index: 95;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  color: var(--dp-text2);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  box-shadow: var(--dp-shadow);
  transition: all .15s;
}
.dsb-open-fab:hover {
  color: var(--dp-accent);
  border-color: var(--dp-accent);
  background: var(--dp-accent-faint);
  transform: translateY(-1px);
}
:root[data-theme="night"] .dsb-open-fab {
  background: rgba(22, 19, 38, .85);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}

/* ---------- 菜单 ---------- */
.dsb-nav {
  flex: 1;
  overflow-y: auto;
  padding: 10px 10px 16px;
  scrollbar-width: thin;
}
.dsb-nav::-webkit-scrollbar { width: 4px; }
.dsb-nav::-webkit-scrollbar-thumb { background: var(--dp-line); border-radius: 999px; }

.dsb-group-label {
  font-size: 10px;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--dp-text3);
  padding: 12px 12px 6px;
  font-weight: 500;
}

.dsb-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px;
  border-radius: 8px;
  color: var(--dp-text2);
  text-decoration: none;
  font-size: 13px;
  margin: 1px 0;
  transition: background .15s, color .15s;
  cursor: pointer;
  position: relative;
}
.dsb-item:hover {
  background: var(--dp-surface2);
  color: var(--dp-text);
}
.dsb-item.active {
  background: var(--dp-accent-faint);
  color: var(--dp-accent);
  font-weight: 600;
}
.dsb-item.active::before {
  content: '';
  position: absolute;
  left: -10px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 14px;
  border-radius: 0 3px 3px 0;
  background: var(--dp-accent);
}
.dsb-ic {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.dsb-ic :deep(svg) { width: 16px; height: 16px; }
.dsb-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dsb-divider {
  height: 1px;
  background: var(--dp-line);
  margin: 8px 10px;
}

.dsb-foot {
  flex-shrink: 0;
  padding: 8px 18px 10px;
  border-top: 1px solid var(--dp-line);
  font-size: 10px;
  color: var(--dp-text3);
  letter-spacing: .04em;
}
</style>
