<template>
  <teleport to="body">
    <transition name="mr-fade">
      <div v-if="open" class="mr-mask" @click="close">
        <div class="mr-panel" role="dialog" aria-label="我的对局" @click.stop>
          <header class="mr-head">
            <b class="mr-title">我的对局</b>
            <span class="mr-n">{{ items.length }}</span>
            <span class="mr-spacer"></span>
            <button
              v-if="finishedCount"
              class="mr-clear"
              :disabled="!!busyKey"
              @click="clearFinished"
            >清空已结束（{{ finishedCount }}）</button>
            <button class="mr-x" aria-label="关闭" @click="close">✕</button>
          </header>

          <p class="mr-tip">
            <template v-if="items.length">点一下进入对局 · <b>长按可删除这个房间</b></template>
            <template v-else>这里会列出你和家人还没清掉的对局房间</template>
          </p>

          <div class="mr-list">
            <p v-if="loading" class="mr-empty">读取中…</p>
            <p v-else-if="!items.length" class="mr-empty">暂无对局房间</p>

            <template v-else>
              <div
                v-for="it in items"
                :key="it.key"
                class="mr-row"
                :class="{ done: it.done, pressing: pressing === it.key }"
                @pointerdown="onDown(it)"
                @pointerup="onUp"
                @pointercancel="onUp"
                @pointerleave="onUp"
                @click="onTap(it)"
              >
                <span class="mr-ic">{{ iconOf(it.gameKey) }}</span>
                <div class="mr-tx">
                  <div class="mr-line1">
                    <b>{{ it.gameName }}</b>
                    <span class="mr-st" :class="'st-' + it.status">{{ statusText(it.status) }}</span>
                  </div>
                  <i>{{ it.opp }} · {{ ago(it.at) }}</i>
                </div>

                <!-- 长按后原地出确认，不用居中弹窗（全站约定） -->
                <div v-if="confirmKey === it.key" class="mr-confirm" @click.stop>
                  <button class="mr-btn del" :disabled="busyKey === it.key" @click="doDelete(it)">删除</button>
                  <button class="mr-btn" @click="confirmKey = ''">取消</button>
                </div>
                <span v-else class="mr-dot" aria-hidden="true"></span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
/** 「我的对局」抽屉（v2.46.2）
 *
 * 背景：退出对局后，房间记录还留在服务端的 waiting / playing / finished 里，
 * `mine()` 会一直把它们返回，但前端**没有任何列表**能把它们清掉（只有 6 个棋盘
 * 组件在挂载时静默接回第一条）。夜星要的是「在外部看到、长按能删除」，于是有这里。
 *
 * 数据源 = 棋类 `gameRoomsApi.mine()` + 牌类 `gameTablesApi.mine()` 合并。
 * 删除 = 真删语义：棋类走新增的 `dissolve`、牌类走 `dissolve`，置为 `dissolved`
 * 终态后 `mine()` 不再返回 —— 服务端也查不到了，不只是前端藏起来。
 */
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { gameRoomsApi } from '@/api/gameRooms'
import { gameTablesApi } from '@/api/gameTables'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open', 'update:count', 'open-room'])

const auth = useAuthStore()
const items = ref([])
const loading = ref(false)

const pressing = ref('')
const confirmKey = ref('')
const busyKey = ref('')

const finishedCount = computed(() => items.value.filter((x) => x.done).length)

const GAME_ICON = {
  gomoku: '⚫', go: '⚪', xiangqi: '♟', junqi: '🎖', ludo: '✈',
  guandan: '🃏', mahjong: '🀄', monopoly: '🎲',
}
function iconOf(gameKey) {
  const k = String(gameKey || '').replace(/[0-9_].*$/, '')
  return GAME_ICON[k] || '🎮'
}
const STATUS_TEXT = { waiting: '等待中', playing: '进行中', finished: '已结束' }
function statusText(s) { return STATUS_TEXT[s] || s || '—' }

function parseTs(s) {
  if (!s) return 0
  const t = Date.parse(String(s).replace(' ', 'T'))
  return Number.isNaN(t) ? 0 : t
}
function ago(s) {
  const t = parseTs(s)
  if (!t) return '刚刚'
  const diff = Date.now() - t
  if (diff < 60e3) return '刚刚'
  const min = Math.floor(diff / 60e3)
  if (min < 60) return `${min} 分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前`
  return `${Math.floor(hr / 24)} 天前`
}

function normChess(r, myId) {
  const opp = r.owner_id === myId ? (r.invitee_name || '待入座') : r.owner_name
  return {
    key: `c${r.id}`,
    kind: 'chess',
    id: r.id,
    gameKey: r.game,
    gameName: r.game_name || '对局',
    opp: `对手 ${opp}`,
    status: r.status,
    done: r.status === 'finished',
    at: r.updated_at || r.created_at,
    route: `/tool/games?room=${r.id}&game=${r.game}`,
  }
}
function normTable(r, myId) {
  const names = (r.seats || [])
    .filter((s) => s.user_id && s.user_id !== myId && !s.is_ai)
    .map((s) => s.name)
  return {
    key: `t${r.id}`,
    kind: 'table',
    id: r.id,
    gameKey: r.game_key,
    gameName: r.game_name || '牌桌',
    opp: names.length ? `${names.join('、')}` : '（空桌）',
    status: r.status,
    done: r.status === 'finished',
    at: r.updated_at || r.created_at,
    route: `/tool/games/table/${r.id}`,
  }
}

async function load() {
  const myId = Number(auth.user?.id) || 0
  loading.value = true
  try {
    const [chess, table] = await Promise.allSettled([
      gameRoomsApi.mine(),
      gameTablesApi.mine(),
    ])
    const next = []
    if (chess.status === 'fulfilled') {
      for (const r of (chess.value?.data?.list || [])) next.push(normChess(r, myId))
    }
    if (table.status === 'fulfilled') {
      for (const r of (table.value?.data?.list || [])) next.push(normTable(r, myId))
    }
    next.sort((a, b) => parseTs(b.at) - parseTs(a.at))
    items.value = next
    emit('update:count', next.length)
  } finally {
    loading.value = false
  }
}

/* ---------- 长按删除 ---------- */
const HOLD_MS = 520
let pressTimer = null
let longFired = false

function buzz() {
  try { if (navigator && navigator.vibrate) navigator.vibrate(10) } catch { /* noop */ }
}

function onDown(it) {
  longFired = false
  pressing.value = it.key
  clearTimeout(pressTimer)
  pressTimer = setTimeout(() => {
    longFired = true
    pressing.value = ''
    confirmKey.value = it.key
    buzz()
  }, HOLD_MS)
}
function onUp() {
  clearTimeout(pressTimer)
  pressing.value = ''
}
/** 短按 = 进房间；长按已经弹了确认，就别再触发跳转（click 一定跟在 pointerup 之后） */
function onTap(it) {
  if (longFired) { longFired = false; return }
  if (confirmKey.value) return
  emit('open-room', it)
}

async function removeOne(it) {
  if (it.kind === 'chess') await gameRoomsApi.dissolve(it.id)
  else await gameTablesApi.dissolve(it.id)
  items.value = items.value.filter((x) => x.key !== it.key)
  emit('update:count', items.value.length)
}

async function doDelete(it) {
  busyKey.value = it.key
  try {
    await removeOne(it)
    confirmKey.value = ''
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.warning(e?.response?.data?.msg || '删除失败，请稍后再试')
  } finally {
    busyKey.value = ''
  }
}

/** 清空已结束：串行删（并发打同一个 SQLite 没意义还容易锁） */
async function clearFinished() {
  const targets = items.value.filter((x) => x.done)
  if (!targets.length) return
  busyKey.value = '__clear__'
  let ok = 0
  for (const it of targets) {
    try { await removeOne(it); ok += 1 } catch { /* 跳过失败项 */ }
  }
  busyKey.value = ''
  if (ok) ElMessage.success(`已清掉 ${ok} 个已结束的对局`)
  if (ok < targets.length) ElMessage.warning(`${targets.length - ok} 个未能删除`)
}

function close() {
  confirmKey.value = ''
  onUp()
  emit('update:open', false)
}

watch(() => props.open, (v) => { if (v) load() })
onMounted(() => { if (auth.isLoggedIn) load() })
</script>

<style scoped>
.mr-mask {
  position: fixed; inset: 0; z-index: 2600;
  display: grid; place-items: center;
  padding: 18px;
  background: rgba(6, 14, 12, .58);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
}
.mr-panel {
  width: min(92vw, 420px);
  max-height: min(74vh, 560px);
  display: flex; flex-direction: column;
  border-radius: 18px;
  border: 1px solid rgba(233, 200, 119, .22);
  background: linear-gradient(168deg, rgba(26, 48, 41, .98), rgba(9, 24, 20, .98));
  box-shadow: 0 28px 70px -26px rgba(0, 0, 0, .95);
  color: #eef2ee;
  overflow: hidden;
}
.mr-head {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 14px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, .09);
}
.mr-title { font-size: 15px; letter-spacing: .02em; }
.mr-n {
  min-width: 20px; height: 20px; padding: 0 6px; border-radius: 999px;
  background: rgba(233, 200, 119, .18); color: var(--gt-gold, #e9c877);
  font-size: 11.5px; font-weight: 600; line-height: 20px; text-align: center;
  font-variant-numeric: tabular-nums;
}
.mr-spacer { flex: 1; }
.mr-clear {
  border-radius: 999px; border: 1px solid rgba(255, 255, 255, .16);
  padding: 4px 11px; font-size: 11.5px; font-family: inherit;
  background: transparent; color: #cfd8d2; cursor: pointer;
  transition: all .18s ease;
}
.mr-clear:hover:not(:disabled) { border-color: rgba(233, 200, 119, .5); color: var(--gt-gold, #e9c877); }
.mr-clear:disabled { opacity: .5; }
.mr-x {
  width: 28px; height: 28px; flex: none; border-radius: 50%; cursor: pointer;
  border: 1px solid rgba(255, 255, 255, .16); background: transparent;
  color: #cfd8d2; font-size: 12px; line-height: 1; font-family: inherit;
}
.mr-x:hover { border-color: rgba(233, 200, 119, .5); color: var(--gt-gold, #e9c877); }

.mr-tip {
  margin: 0; padding: 9px 15px 4px;
  font-size: 11.5px; line-height: 1.6; color: #93a49b;
}
.mr-tip b { color: var(--gt-gold, #e9c877); font-weight: 600; }

.mr-list {
  flex: 1; min-height: 0; overflow-y: auto;
  padding: 6px 10px 12px;
  display: flex; flex-direction: column; gap: 6px;
}
.mr-empty { margin: 22px 0; text-align: center; font-size: 12.5px; color: #93a49b; }

.mr-row {
  position: relative;
  display: flex; align-items: center; gap: 10px;
  padding: 10px 11px; border-radius: 13px;
  background: rgba(255, 255, 255, .05);
  border: 1px solid rgba(255, 255, 255, .1);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  transition: background .18s ease, border-color .18s ease, transform .12s ease;
}
.mr-row:hover { background: rgba(255, 255, 255, .08); }
.mr-row.pressing { transform: scale(.985); border-color: rgba(233, 200, 119, .45); }
.mr-row.done { opacity: .72; }
.mr-ic {
  width: 34px; height: 34px; flex: none; border-radius: 10px;
  display: grid; place-items: center; font-size: 17px;
  background: rgba(0, 0, 0, .3); border: 1px solid rgba(255, 255, 255, .1);
}
.mr-tx { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 2px; }
.mr-line1 { display: flex; align-items: center; gap: 7px; min-width: 0; }
.mr-line1 b {
  font-size: 13px; font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.mr-st {
  flex: none; padding: 1px 7px; border-radius: 999px;
  font-size: 10px; font-weight: 600;
}
.mr-st.st-waiting { background: rgba(109, 154, 212, .2); color: #8ab4e8; }
.mr-st.st-playing { background: rgba(63, 174, 122, .2); color: #6fd3a1; }
.mr-st.st-finished { background: rgba(255, 255, 255, .1); color: #9aa8a0; }
.mr-tx i {
  font-style: normal; font-size: 11px; color: #93a49b;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.mr-dot { width: 6px; height: 6px; flex: none; border-radius: 50%; background: rgba(255, 255, 255, .18); }

.mr-confirm { display: inline-flex; gap: 6px; flex: none; }
.mr-btn {
  border-radius: 999px; border: 1px solid rgba(255, 255, 255, .18);
  padding: 5px 12px; font-size: 11.5px; font-family: inherit;
  background: transparent; color: #cfd8d2; cursor: pointer;
}
.mr-btn.del {
  background: linear-gradient(180deg, #d9483f, #a82f2a);
  border-color: rgba(255, 255, 255, .26); color: #fff;
}
.mr-btn:disabled { opacity: .55; }

.mr-fade-enter-active, .mr-fade-leave-active { transition: opacity .18s ease; }
.mr-fade-enter-from, .mr-fade-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .mr-fade-enter-active, .mr-fade-leave-active { transition-duration: .01s; }
  .mr-row.pressing { transform: none; }
}
</style>
