/** 对局邀请（棋类 + 牌类）统一来源 —— v2.45
 *
 * 背景：此前棋类 / 牌类各自在 `App.vue` 里起一个 5s 轮询，收到邀请就用
 * `ElMessageBox.confirm` 弹一个**居中确认框**。两个问题：
 *   1. 弹窗是一次性的 —— `inviteSeen` 记过就不再提示，用户当时不在电脑前、
 *      正忙、或随手点了「拒绝」，之后**没有任何入口能补看**，观感就是「对方收不到邀请」；
 *   2. 居中模态弹窗打断当前操作，不符合全站「无弹窗」约定。
 *
 * 现在改成：轮询结果只落这一份单例状态，由三处共同消费 ——
 *   · 桌面顶栏「提醒中心 · 对局邀请」段（持久入口 + 未读角标 + 就地接受/拒绝）
 *   · 移动端悬浮邀请胶囊 `MobileInviteDock`
 *   · 新到时的非阻塞 `ElNotification`（角标提示，不打断操作）
 * 于是「页面开着能实时收到」与「错过之后还能补看」同时成立。
 *
 * 角标口径 = **待处理邀请条数**（`pendingCount`）。这是「有待办要你处理」的语义，
 * 只在接受 / 拒绝 / 对方撤回后才减少 —— 打开面板看过了不等于处理了，不该清零。
 */
import { ref, computed } from 'vue'
import { gameRoomsApi } from '@/api/gameRooms'
import { gameTablesApi } from '@/api/gameTables'
import { useAuthStore } from '@/stores/auth'

export const INVITE_POLL_MS = 5000

const invites = ref([])
const loading = ref(false)
/** 本会话「新到且尚未在面板里看过」的 key —— 只用于行内「新」标记，不影响角标 */
const newKeys = ref(new Set())

const seenKeys = new Set()   // 已触发过提示（防重复 toast / 重复「新」标记）
let timer = null
let arrivalsCb = null
let visBound = false

function parseTs(s) {
  if (!s) return 0
  const t = Date.parse(String(s).replace(' ', 'T'))
  return Number.isNaN(t) ? 0 : t
}

/** 相对时间标签（后端给的是 "YYYY-MM-DD HH:MM:SS.ffffff" 字符串） */
export function agoLabel(s) {
  const t = parseTs(s)
  if (!t) return '刚刚'
  const diff = Date.now() - t
  if (diff < 60 * 1000) return '刚刚'
  const min = Math.floor(diff / 60000)
  if (min < 60) return `${min} 分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前`
  return `${Math.floor(hr / 24)} 天前`
}

function normalizeChess(inv) {
  return {
    key: `c${inv.id}`,
    kind: 'chess',
    id: inv.id,
    gameKey: inv.game,
    gameName: inv.game_name || '对局',
    fromName: inv.owner_name || '家人',
    createdAt: inv.created_at || '',
    route: `/tool/games?room=${inv.id}&game=${inv.game}`,
  }
}

function normalizeTable(inv) {
  const hostSeat = (inv.seats || []).find((s) => s.user_id === inv.host_id)
  return {
    key: `t${inv.id}`,
    kind: 'table',
    id: inv.id,
    gameKey: inv.game_key,
    gameName: inv.game_name || '牌桌',
    fromName: hostSeat?.name || '家人',
    createdAt: inv.created_at || '',
    route: `/tool/games/table/${inv.id}`,
  }
}

async function refresh() {
  const auth = useAuthStore()
  if (!auth?.isLoggedIn) {
    invites.value = []
    return
  }
  loading.value = true
  const results = await Promise.allSettled([
    gameRoomsApi.invites(),
    gameTablesApi.invites(),
  ])
  const next = []
  if (results[0].status === 'fulfilled') {
    for (const inv of (results[0].value?.data?.list || [])) next.push(normalizeChess(inv))
  }
  if (results[1].status === 'fulfilled') {
    for (const inv of (results[1].value?.data?.list || [])) next.push(normalizeTable(inv))
  }
  invites.value = next
  loading.value = false

  const alive = new Set(next.map((it) => it.key))
  // 已消失（被撤回 / 已被别处处理）的 key 从记忆里清掉，避免下次同名 id 复用时误判为「旧」
  for (const k of [...seenKeys]) if (!alive.has(k)) seenKeys.delete(k)

  const arrivals = []
  for (const it of next) {
    if (seenKeys.has(it.key)) continue
    seenKeys.add(it.key)
    arrivals.push(it)
  }

  const nk = new Set()
  for (const k of newKeys.value) if (alive.has(k)) nk.add(k)
  for (const it of arrivals) nk.add(it.key)
  newKeys.value = nk

  if (arrivals.length && typeof arrivalsCb === 'function') arrivalsCb(arrivals)
}

function forget(key) {
  invites.value = invites.value.filter((i) => i.key !== key)
  seenKeys.delete(key)
  const nk = new Set(newKeys.value)
  nk.delete(key)
  newKeys.value = nk
}

/** 接受：棋类走 accept（waiting→playing），牌类走 join（入座） */
async function accept(item) {
  if (item.kind === 'chess') await gameRoomsApi.accept(item.id)
  else await gameTablesApi.join(item.id)
  forget(item.key)
}

/** 拒绝：两边语义一致，均把房间置为 declined */
async function decline(item) {
  if (item.kind === 'chess') await gameRoomsApi.decline(item.id)
  else await gameTablesApi.decline(item.id)
  forget(item.key)
}

/** 面板打开 = 看过，清掉「新」标记（角标仍按待处理条数走，不在这里清零） */
function markSeen() {
  if (!newKeys.value.size) return
  newKeys.value = new Set()
}

function start(onArrivals) {
  if (onArrivals) arrivalsCb = onArrivals
  if (!visBound && typeof document !== 'undefined') {
    // 从别的标签页 / 后台切回来时立刻补一次，不必干等一个轮询周期
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') refresh()
    })
    visBound = true
  }
  if (timer) return
  refresh()
  timer = setInterval(refresh, INVITE_POLL_MS)
}

function stop() {
  if (timer) { clearInterval(timer); timer = null }
}

export function useGameInvites() {
  const pendingCount = computed(() => invites.value.length)
  return { invites, loading, newKeys, pendingCount, refresh, accept, decline, markSeen, start, stop }
}
