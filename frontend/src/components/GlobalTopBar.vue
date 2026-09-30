<template>
  <!-- 桌面端顶栏已「去条化」：不再有整条背景/分隔线
       v2.41.2 进一步瘦身：只保留右侧两个悬浮按钮「提醒中心」+「账号」——
         背景音乐 → 进账号下拉
         下载 App  → 进账号下拉
         ⌘K / AI 高级 → 迁入「智能」分组（由侧栏与手机模块目录共用入口）

       这样顶栏视觉更干净，常驻操作只剩「看一眼提醒」+「点自己的名字」。
       —— 玄黄品牌 + 全局搜索仍位于左侧侧栏顶部，与「智能」分组共存；无重复入口 -->
  <div class="lj-topbar" ref="topbarRef">
    <div class="tb-right">
      <!-- 倒计时徽章：最近一条未过期倒计时，hover/点击展开面板
           语义属「提醒」类（与下方提醒中心同源），保留不占视觉权重 -->
      <el-dropdown v-if="nearest" trigger="click" placement="bottom-end" :show-arrow="false">
        <button class="tb-icon-btn tb-cd-btn" :title="`距 ${nearest.title} 还有 ${nearest.days_left} 天`">
          <el-icon><Calendar /></el-icon>
          <span class="tb-cd-text">距 {{ nearest.title }} {{ nearest.days_left }} 天</span>
        </button>
        <template #dropdown>
          <div class="tb-cd-panel" @click.stop>
            <div class="tb-panel-title">时光痕迹</div>
            <div
              v-for="it in upcoming"
              :key="it.id"
              class="tb-cd-item"
              @click="goCountdown(it.id)"
            >
              <span class="tb-cd-dot" :style="{ background: it.color || 'var(--lj-dai)' }"></span>
              <span class="tb-cd-name">{{ it.title }}</span>
              <span class="tb-cd-date">{{ shortDate(it.target_date) }}</span>
              <span class="tb-cd-days">{{ it.days_left }} 天</span>
            </div>
            <div v-if="!upcoming.length" class="tb-cd-empty">暂无进行中的倒计时</div>
          </div>
        </template>
      </el-dropdown>

      <!-- 提醒中心：目标价预警 + 待办提醒（v2.14.3 合并；v2.14.4 角标分色） -->
      <el-dropdown trigger="click" placement="bottom-end" :show-arrow="false" @visible-change="onAlertPanelToggle">
        <button class="tb-icon-btn tb-alert-btn" :title="alertTitle" aria-label="提醒中心">
          <el-icon><Bell /></el-icon>
          <span
            v-if="totalUnread > 0"
            class="tb-alert-dot"
            :class="alertDotTone"
          >{{ totalUnread > 99 ? '99+' : totalUnread }}</span>
        </button>
        <template #dropdown>
          <div class="tb-alert-panel" @click.stop>
            <!-- 段 1：待办提醒 -->
            <div class="tb-alert-section">
              <div class="tb-panel-title">
                <span>
                  <el-icon><List /></el-icon>
                  待办提醒
                  <span v-if="taskItems.length" class="tb-section-count">{{ taskItems.length }}</span>
                </span>
                <router-link to="/tasks" class="tb-alert-link" @click.stop>查看全部 →</router-link>
              </div>
              <div v-if="!taskItems.length" class="tb-alert-empty">
                暂无待办。
              </div>
              <div
                v-for="t in taskItems.slice(0, 5)"
                :key="'task-' + t.id"
                class="tb-alert-item kind-task"
                :class="['pri-' + (t.priority || 'medium'), { overdue: isOverdue(t.due_date) }]"
                @click="onTaskItemClick(t)"
              >
                <span class="tb-alert-kind" :class="'pri-' + (t.priority || 'medium')">
                  {{ priorityLabel(t.priority) }}
                </span>
                <span class="tb-alert-name">{{ t.title }}</span>
                <span class="tb-alert-meta">
                  <template v-if="isOverdue(t.due_date)">已逾期 {{ daysFromNow(t.due_date) }}</template>
                  <template v-else-if="t.due_date">还剩 {{ daysFromNow(t.due_date) }} 天到期</template>
                  <template v-else>无截止</template>
                </span>
              </div>
            </div>

            <div class="tb-alert-divider"></div>

            <!-- 段 2：即将到来（时光痕迹 / 倒计时） -->
            <div class="tb-alert-section">
              <div class="tb-panel-title">
                <span>
                  <el-icon><Calendar /></el-icon>
                  即将到来
                  <span v-if="upcoming.length" class="tb-section-count">{{ upcoming.length }}</span>
                </span>
                <router-link to="/tool/countdown" class="tb-alert-link" @click.stop>查看全部 →</router-link>
              </div>
              <div v-if="!upcoming.length" class="tb-alert-empty">
                暂无即将到来的事件。
              </div>
              <div
                v-for="cd in upcoming"
                :key="'cd-' + cd.id"
                class="tb-alert-item kind-cd"
                @click="goCountdown(cd.id)"
              >
                <span class="tb-cd-mark" :style="{ background: cd.color || 'var(--yq-gold)' }"></span>
                <span class="tb-alert-name">{{ cd.title }}</span>
                <span class="tb-alert-meta">
                  {{ shortDate(cd.target_date) }} ·
                  <em class="tb-alert-days">{{ cd.days_left === 0 ? '就是今天' : `还有 ${cd.days_left} 天` }}</em>
                </span>
              </div>
            </div>

            <div class="tb-alert-divider"></div>

            <!-- 段 3：目标价预警 -->
            <div class="tb-alert-section">
              <div class="tb-panel-title">
                <span>
                  <el-icon><TrendCharts /></el-icon>
                  目标价预警
                  <span v-if="alertUnread > 0" class="tb-section-count tb-section-count--alert">{{ alertUnread }}</span>
                </span>
                <button v-if="alertUnread > 0" class="tb-alert-clear" @click="markAllRead">全部已读</button>
              </div>
              <div v-if="!alertItems.length" class="tb-alert-empty">
                暂无预警。在「行情」→ 点自选股的「✎」即可设置目标价。
              </div>
              <div
                v-for="a in alertItems"
                :key="'alert-' + a.id"
                class="tb-alert-item"
                :class="['kind-' + a.kind, { unread: !a.read }]"
                @click="onAlertItemClick(a)"
              >
                <span class="tb-alert-kind" :class="'kind-' + a.kind">
                  {{ a.kind === 'up' ? '涨破' : '跌破' }}
                </span>
                <span class="tb-alert-name">{{ a.name }} <i>{{ a.code }}</i></span>
                <span class="tb-alert-meta">
                  目标 ¥{{ fmtPrice(a.target_price) }} · 现价 ¥{{ fmtPrice(a.hit_price) }}
                </span>
                <span class="tb-alert-date">{{ shortDate(a.date) }}</span>
                <span v-if="!a.read" class="tb-alert-newdot" aria-label="未读"></span>
              </div>
            </div>
          </div>
        </template>
      </el-dropdown>

      <!-- 账号区：v2.41.2 把「背景音乐」「下载 App」也收纳进来
           ——「顶栏只留提醒和账号」是用户拍板，账号下拉作为「个人场景集合」是合理的入口。
           不用 el-dropdown-item 因为命令需要自带参数（profile/ openAudio/ download/ logout），
           自己用 ul+li+onCommand 更直白，免去 dropdown-item 的点击语义不一致 -->
      <el-dropdown trigger="click" placement="bottom-end" :show-arrow="false" @visible-change="onUserPanelToggle">
        <div class="tb-user" :title="userName">
          <span class="tb-user-name">{{ userName }}</span>
          <el-icon class="tb-caret"><CaretBottom /></el-icon>
        </div>
        <template #dropdown>
          <div class="tb-user-panel" @click.stop>
            <header class="tb-user-card">
              <div class="tb-user-card__name">{{ userName }}</div>
              <div v-if="auth.user?.email" class="tb-user-card__email">{{ auth.user.email }}</div>
            </header>

            <ul class="tb-user-list">
              <li class="tb-user-item" @click="onCommand('profile')">
                <el-icon><User /></el-icon><span>个人中心</span>
              </li>
              <li class="tb-user-item" @click="onCommand('openAudio')">
                <el-icon><Headset /></el-icon><span>背景音乐</span>
                <span class="tb-user-side">
                  <span class="tb-user-mini-switch" :class="{ on: player.bgmEnabled }" aria-hidden="true"></span>
                  <span class="tb-user-mini-status" :class="{ off: !player.bgmEnabled }">{{ player.bgmEnabled ? '开' : '关' }}</span>
                </span>
              </li>
              <li class="tb-user-item" @click="onCommand('download')">
                <el-icon><Cellphone /></el-icon><span>下载手机软件</span>
                <span class="tb-user-side"><el-icon class="tb-user-ext"><Promotion /></el-icon></span>
              </li>
              <li class="tb-user-item tb-user-item--divided" @click="onCommand('logout')">
                <el-icon><SwitchButton /></el-icon><span>退出账号</span>
              </li>
            </ul>
          </div>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import {
  User, SwitchButton, Headset, CaretBottom, Cellphone, Promotion, Calendar, Bell, List, TrendCharts,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { usePlayerStore } from '@/stores/player'
import { useBgmLibraryStore } from '@/stores/bgmLibrary'
import { listHomeCountdowns } from '@/api/countdown'
import { stocksApi } from '@/api/stocks'
import { workbenchApi } from '@/api/workbench'

/* ---- 倒计时徽章（#3）：最近一条未过期的 count_down 倒计时 + 展开面板 ---- */
const cdList = ref([])
const nearest = computed(() => {
  const cds = cdList.value.filter(c => c.direction === 'count_down' && c.days_left >= 0)
  if (!cds.length) return null
  return cds.sort((a, b) => a.days_left - b.days_left)[0]
})
// 顶栏「倒计时徽章」与「提醒中心 · 即将到来」共用同一份最近 5 条。
// 必须限定 count_down：纪念日（count_up）的 days_left 在后端是 abs(日期差)，
// 即「已过天数」且恒 ≥ 0，与倒计时的「剩余天数」不是同一量纲 —— 混进来既排不出
// 正确的序，也会让「即将到来」里冒出「已经 13 天」这种自相矛盾的条目。
const upcoming = computed(() => {
  const cds = cdList.value.filter(c => c.direction === 'count_down' && c.days_left >= 0)
  cds.sort((a, b) => a.days_left - b.days_left)
  return cds.slice(0, 5)
})
function goCountdown(id) { router.push(`/tool/countdown/${id}`) }
function shortDate(dateStr) { return dateStr ? String(dateStr).slice(5) : '' }
async function loadCountdowns() {
  try {
    const res = await listHomeCountdowns()
    cdList.value = res?.data?.list || []
  } catch { /* 未登录/网络失败则不显示徽章 */ }
}

/* ---- 目标价预警 ---- */
const alertItems = ref([])
const alertUnread = ref(0)
const ALERT_POLL_MS = 60 * 1000
let alertTimer = null
let lastSeenIds = new Set()

/* ---- 待办提醒 ---- */
const taskItems = ref([])
function isOverdue(due) {
  if (!due) return false
  return new Date(due).getTime() < Date.now() - 24 * 3600 * 1000
}
function daysFromNow(due) {
  if (!due) return 0
  const d = Math.ceil((new Date(due).getTime() - Date.now()) / (24 * 3600 * 1000))
  return d
}
function priorityLabel(p) {
  if (p === 'high') return '高优'
  if (p === 'low') return '低优'
  return '中优'
}

const totalUnread = computed(() => alertUnread.value + taskItems.value.length)
const alertDotTone = computed(() => {
  if (alertUnread.value > 0) return 'is-alert'
  return 'is-task'
})
const alertTitle = computed(() => {
  const parts = []
  if (taskItems.value.length) parts.push(`待办 ${taskItems.value.length}`)
  if (alertUnread.value) parts.push(`目标价预警 ${alertUnread.value}`)
  if (parts.length) return `提醒：${parts.join(' · ')} 条`
  return '提醒中心'
})
function fmtPrice(v) {
  return v == null ? '--' : Number(v).toFixed(2)
}
async function loadAlerts(showNotifications = false) {
  try {
    const res = await stocksApi.alerts({ limit: 30 })
    const data = res?.data || { unread: 0, items: [] }
    const newItems = data.items || []
    alertItems.value = newItems
    alertUnread.value = data.unread || 0

    if (showNotifications) {
      for (const it of newItems) {
        if (it.read) continue
        if (lastSeenIds.has(it.id)) continue
        lastSeenIds.add(it.id)
        const isUp = it.kind === 'up'
        ElNotification({
          title: isUp ? '🎯 涨破目标价' : '🔻 跌破目标价',
          message: `${it.name || it.code} 触达目标价：现价 ¥${fmtPrice(it.hit_price)}（目标 ¥${fmtPrice(it.target_price)}）`,
          type: isUp ? 'success' : 'warning',
          duration: 6000,
          position: 'top-right',
        })
      }
    }
  } catch { /* 静默 */ }
}
function startAlertPolling() {
  if (alertTimer) return
  alertTimer = setInterval(() => {
    loadAlerts(true)
    loadTasks(true)
  }, ALERT_POLL_MS)
}
function stopAlertPolling() {
  if (alertTimer) { clearInterval(alertTimer); alertTimer = null }
}

async function loadTasks(showNotifications = false) {
  try {
    const res = await workbenchApi.tasks.list({ size: 200 })
    const all = res?.data?.list || []
    const now = Date.now()
    const SEVEN_DAYS = 7 * 24 * 3600 * 1000
    const filtered = all
      .filter((t) => t.status !== 'done')
      .filter((t) => {
        if (t.priority === 'high') return true
        if (!t.due_date) return false
        const dueTs = new Date(t.due_date).getTime()
        return dueTs < now + SEVEN_DAYS
      })
      .sort((a, b) => {
        const aDue = a.due_date ? new Date(a.due_date).getTime() : Infinity
        const bDue = b.due_date ? new Date(b.due_date).getTime() : Infinity
        const aOver = aDue < now
        const bOver = bDue < now
        if (aOver !== bOver) return aOver ? -1 : 1
        if (a.priority === 'high' && b.priority !== 'high') return -1
        if (b.priority === 'high' && a.priority !== 'high') return 1
        return aDue - bDue
      })
      .slice(0, 8)
    taskItems.value = filtered
    for (const it of filtered) {
      if (!isOverdue(it.due_date)) continue
      if (lastSeenTaskIds.has(it.id)) continue
      lastSeenTaskIds.add(it.id)
      ElNotification({
        title: '⏰ 待办已逾期',
        message: `${it.title}（截止 ${shortDate(it.due_date)}）`,
        type: 'warning',
        duration: 5000,
        position: 'top-right',
      })
    }
  } catch { /* 静默 */ }
}
let lastSeenTaskIds = new Set()

function onTaskItemClick(t) {
  router.push({ path: '/tasks', query: { focus: String(t.id) } })
}

function onAlertPanelToggle(open) {
  if (open) {
    loadAlerts(false)
    loadTasks(false)
  }
}
/* 账号下拉开关不做事（命令由 li 自带 click 处理），保留占位避免后续忘记 */
function onUserPanelToggle(_open) { /* 暂无需刷新的数据 */ }
async function markAllRead() {
  try {
    await stocksApi.markAllAlertsRead()
    await loadAlerts(false)
  } catch { /* 静默 */ }
}
async function onAlertItemClick(a) {
  try {
    if (!a.read) await stocksApi.markAlertRead(a.id)
  } catch { /* 静默 */ }
  router.push({ path: `/stocks/${a.code}`, query: { market: a.market } })
}

const router = useRouter()
const auth = useAuthStore()
const player = usePlayerStore()
const bgm = useBgmLibraryStore()

const topbarRef = ref(null)

const userName = computed(() => auth.user?.nickname || auth.user?.name || auth.user?.email || '道友')

/* ---- 账号下拉命令 ----
   个人中心 → /profile
   背景音乐 → 切换 BGM 总开关（不开抽屉，开关一次就能用，更轻）
   下载手机软件 → 新窗口打开 /download/
   退出账号 → 清 token 跳 /login
*/
function onCommand(cmd) {
  switch (cmd) {
    case 'profile': router.push('/profile'); break
    case 'openAudio': player.toggleBgm(); break
    case 'download':
      if (typeof window !== 'undefined') window.open('/download/', '_blank', 'noopener')
      break
    case 'logout':
      auth.logoutAction()
      router.push('/login')
      break
  }
}

onMounted(async () => {
  await bgm.initBgm()
  loadCountdowns()
  await loadAlerts(false)
  for (const it of alertItems.value) {
    if (!it.read) lastSeenIds.add(it.id)
  }
  startAlertPolling()
  await loadTasks(false)
  for (const it of taskItems.value) {
    if (isOverdue(it.due_date)) lastSeenTaskIds.add(it.id)
  }
})

onUnmounted(() => {
  stopAlertPolling()
})
</script>

<style scoped>
/* 顶栏已「去条化」：不再是一条通栏，只有右上角悬浮按钮组
   v2.41.2 进一步收紧：右侧只剩「提醒中心」+「账号」两个区域（倒计时徽章算提醒语义） */
.lj-topbar {
  position: fixed;
  top: 12px;
  right: 16px;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  background: transparent;
  border: none;
  box-shadow: none;
  box-sizing: border-box;
}
@media (max-width: 767px) {
  .lj-topbar { top: calc(10px + var(--safe-top)); right: 10px; }
}

.tb-right { display: flex; align-items: center; gap: 8px; margin-left: auto; flex: none; }

.tb-icon-btn {
  position: relative;
  width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: 10px;
  background: transparent;
  color: var(--dp-text2, var(--lj-text-2)); font-size: 17px; cursor: pointer; transition: all 0.18s;
}
.tb-icon-btn:hover {
  color: var(--dp-accent, var(--lj-dai));
  background: var(--dp-accent-faint, rgba(127, 168, 163, 0.12));
}

/* 倒计时徽章按钮（胶囊，贴合金辉玻璃按钮组） */
.tb-cd-btn {
  width: auto;
  gap: 6px;
  padding: 0 12px;
  border: 1px solid var(--dp-line, rgba(126, 136, 243, 0.22));
}
.tb-cd-btn:hover { border-color: var(--dp-accent, var(--lj-dai)); }
.tb-cd-text {
  font-size: 11.5px;
  color: var(--dp-text2, var(--lj-text-2));
  white-space: nowrap;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-variant-numeric: tabular-nums;
}
.tb-cd-btn:hover .tb-cd-text { color: var(--dp-accent, var(--lj-dai)); }

/* 倒计时展开面板 */
.tb-cd-panel { width: 260px; padding: 10px 12px; }
.tb-cd-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px; border-radius: 8px; cursor: pointer;
}
.tb-cd-item:hover { background: rgba(127, 168, 163, 0.1); }
.tb-cd-dot { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.tb-cd-name { flex: 1; min-width: 0; font-size: 13px; color: var(--lj-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tb-cd-date { font-size: 11px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }
.tb-cd-days { font-size: 12px; color: var(--lj-dai); font-variant-numeric: tabular-nums; flex: none; }
.tb-cd-empty { padding: 12px 8px; text-align: center; font-size: 12px; color: var(--lj-text-3); }

/* ---- 目标价预警 ---- */
.tb-alert-btn { position: relative; }
.tb-alert-dot {
  position: absolute;
  top: 4px; right: 4px;
  min-width: 16px; height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  color: #fff;
  font-size: 10px; font-weight: 600; line-height: 16px;
  text-align: center;
  box-shadow: 0 0 0 2px var(--dp-bg, #0B0F14);
  transition: background var(--motion-fast) var(--ease-standard);
}
.tb-alert-dot.is-task { background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-gold-bright, #d97706)); }
.tb-alert-dot.is-alert { background: #D8504F; }
.tb-alert-panel {
  width: 360px; max-height: 520px; overflow-y: auto; padding: 10px 14px 12px;
}
.tb-alert-panel .tb-panel-title {
  display: flex; justify-content: space-between; align-items: center;
}
.tb-alert-clear {
  background: transparent; border: 1px solid var(--lj-line);
  color: var(--lj-text-2); font-size: 11px;
  padding: 3px 10px; border-radius: 999px; cursor: pointer;
  transition: all 0.18s;
}
.tb-alert-clear:hover { color: var(--lj-seal); border-color: var(--lj-seal); }
.tb-alert-empty {
  padding: 18px 4px;
  text-align: center; font-size: 12px;
  color: var(--lj-text-3); line-height: 1.7;
}
.tb-alert-item {
  position: relative;
  display: grid;
  grid-template-columns: 44px 1fr auto;
  align-items: center;
  gap: 6px 10px;
  padding: 10px 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px dashed var(--lj-line);
}
.tb-alert-item:last-child { border-bottom: none; }
.tb-alert-item:hover { background: rgba(127, 168, 163, 0.08); }
.tb-alert-item.unread { background: rgba(216, 80, 79, 0.04); }
.tb-alert-kind {
  display: inline-flex; align-items: center; justify-content: center;
  height: 22px; padding: 0 8px; border-radius: 999px;
  font-size: 11px; font-weight: 600;
}
.tb-alert-kind.kind-up { background: rgba(216, 80, 79, 0.12); color: #D8504F; }
.tb-alert-kind.kind-down { background: rgba(63, 150, 142, 0.12); color: #3F968E; }
.tb-alert-name {
  font-size: 13px; color: var(--lj-text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.tb-alert-name i {
  font-style: normal; font-size: 11px; color: var(--lj-text-3); margin-left: 4px;
}
.tb-alert-meta {
  grid-column: 1 / -1;
  font-size: 11px; color: var(--lj-text-2);
  font-variant-numeric: tabular-nums;
}
.tb-alert-date {
  font-size: 11px; color: var(--lj-text-3);
  font-variant-numeric: tabular-nums;
  align-self: center;
}
.tb-alert-newdot {
  position: absolute; top: 10px; right: 4px;
  width: 6px; height: 6px; border-radius: 50%;
  background: #D8504F;
}

.tb-alert-panel .tb-panel-title > span {
  display: inline-flex; align-items: center; gap: 6px;
  font-weight: 600; font-size: 12.5px; color: var(--lj-text);
}
.tb-section-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 18px; height: 18px; padding: 0 6px;
  border-radius: 999px;
  background: var(--lj-seal-soft, var(--yq-gold-faint));
  color: var(--lj-seal, var(--yq-gold));
  font-size: 10.5px; font-weight: 600;
}
.tb-section-count--alert { background: rgba(216, 80, 79, .12); color: #D8504F; }
.tb-alert-link {
  font-size: 11.5px; color: var(--lj-seal); text-decoration: none;
  cursor: pointer;
}
.tb-alert-link:hover { text-decoration: underline; }
.tb-alert-divider {
  height: 1px; background: var(--lj-line); margin: 4px 0;
}
.tb-alert-item.kind-task { grid-template-columns: 44px 1fr; }
.tb-alert-item.kind-task .tb-alert-name {
  font-size: 12.5px;
}
.tb-alert-item.overdue {
  background: rgba(216, 80, 79, .05);
}
.tb-alert-kind.pri-high { background: rgba(216, 80, 79, .14); color: #D8504F; }
.tb-alert-kind.pri-medium { background: var(--yq-gold-faint, rgba(199, 169, 107, .18)); color: var(--yq-gold, #c7a96b); }
.tb-alert-kind.pri-low { background: rgba(127, 168, 163, .14); color: var(--yq-rain, #7fa8a3); }

.tb-alert-item.kind-cd { grid-template-columns: 10px 1fr; }
.tb-alert-item.kind-cd .tb-alert-name { font-size: 12.5px; }
.tb-cd-mark {
  width: 7px; height: 7px; border-radius: 50%;
  justify-self: center; flex: none;
}
.tb-alert-days {
  font-style: normal; font-weight: 600;
  color: var(--lj-seal, var(--yq-gold));
}

@media (max-width: 767px) {
  .tb-icon-btn { width: 40px; height: 44px; }
}

/* ---- 账号下拉面板（v2.41.2：用户信息卡 + 多入口） ---- */
.tb-user {
  display: flex; align-items: center; gap: 4px;
  cursor: pointer;
  padding: 6px 10px; border-radius: 10px;
  background: transparent;
  transition: all 0.18s;
}
.tb-user:hover { background: var(--dp-accent-faint, rgba(127, 168, 163, 0.12)); }
.tb-user:hover .tb-user-name { color: var(--dp-accent, var(--lj-dai)); }
.tb-user-name { font-size: 13px; color: var(--dp-text, var(--lj-text)); }
.tb-caret { font-size: 12px; color: var(--dp-text3, var(--lj-text-2)); }

/* 自渲染的下拉面板：保持与 el-dropdown 弹出层一致的视觉规格 */
.tb-user-panel {
  width: 280px;
  padding: 4px 6px 6px;
  background: var(--lj-paper, #fff);
  border: 1px solid var(--lj-line, rgba(0,0,0,0.08));
  border-radius: 12px;
  box-shadow: var(--lj-shadow, 0 8px 24px rgba(0,0,0,0.12));
  color: var(--lj-text, #222);
}
:root[data-theme="night"] .tb-user-panel {
  background: rgba(22, 19, 38, .92);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  backdrop-filter: blur(16px) saturate(160%);
}
.tb-user-card {
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--lj-line, rgba(0,0,0,0.06));
  margin-bottom: 4px;
}
.tb-user-card__name {
  font-size: 14px; font-weight: 600; color: var(--lj-text, #222);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tb-user-card__email {
  font-size: 11.5px; color: var(--lj-text-3, #888);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-top: 2px;
}

/* 账号下拉列表（自渲染） */
.tb-user-list {
  list-style: none; padding: 0; margin: 4px 0 0;
}
.tb-user-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.2;
  color: var(--lj-text-2, #555);
  cursor: pointer;
  user-select: none;
  transition: background 0.15s, color 0.15s;
}
.tb-user-item > .el-icon { font-size: 15px; color: var(--lj-text-3, #888); transition: color 0.15s; }
.tb-user-item:hover { background: var(--lj-seal-soft, rgba(217, 138, 118, 0.08)); color: var(--lj-seal, #d98a76); }
.tb-user-item:hover > .el-icon { color: var(--lj-seal, #d98a76); }
.tb-user-item--divided {
  margin-top: 6px;
  border-top: 1px solid var(--lj-line, rgba(0,0,0,0.06));
  padding-top: 10px;
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}
.tb-user-item > span:not(.tb-user-side) { flex: none; }

/* 右侧状态/外链图标：mini 开关、外链标识 */
.tb-user-side {
  margin-left: auto;
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11.5px;
  color: var(--lj-text-3, #888);
}
.tb-user-mini-switch {
  position: relative;
  width: 28px; height: 16px;
  border-radius: 999px;
  background: rgba(74, 95, 99, 0.2);
  border: 1px solid var(--lj-line-strong, rgba(0,0,0,0.08));
  transition: background 0.18s, border-color 0.18s;
}
.tb-user-mini-switch::after {
  content: '';
  position: absolute;
  top: 50%; left: 2px;
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--lj-text-3, #888);
  transform: translateY(-50%);
  transition: left 0.18s, background 0.18s;
}
.tb-user-mini-switch.on {
  background: var(--lj-seal-soft, rgba(217, 138, 118, 0.16));
  border-color: var(--lj-seal, #d98a76);
}
.tb-user-mini-switch.on::after {
  left: 14px;
  background: var(--yq-rain-bright, #62e6d1);
}
.tb-user-mini-status.off { color: var(--lj-text-3, #888); }
.tb-user-ext { font-size: 12px; }
</style>