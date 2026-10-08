<template>
  <IslandInnerBase type="tool" :title="pageTitle" :subtitle="pageSubtitle">
    <div class="gtv-root">
      <!-- ========== 建房（id=new） ========== -->
      <section v-if="mode === 'create'" class="gtv-card">
        <header class="gtv-head">
          <div class="gtv-head-tx">
            <b>开一桌{{ gameLabel }}</b>
            <i>选好家人与底注，建房后把邀请发给他们；开局时空位由机器人补上。</i>
          </div>
          <button class="gtv-btn ghost" @click="goBack">返回</button>
        </header>

        <div class="gtv-form">
          <div class="gtv-field">
            <label class="gtv-label">邀请家人（可多选，空位由机器人补）</label>
            <div class="gtv-members">
              <button
                v-for="m in families"
                :key="m.user_id"
                class="gtv-member"
                :class="{ on: invitees.includes(m.user_id) }"
                @click="toggleInvitee(m.user_id)"
              >
                <span class="gtv-ava">{{ m.avatar || '🌿' }}</span>
                <span class="gtv-name">{{ m.display_name || '家人' }}</span>
                <span v-if="invitees.includes(m.user_id)" class="gtv-check">✓</span>
              </button>
              <p v-if="!families.length" class="gtv-empty">家庭里还没有其他账号可以邀请。</p>
            </div>
          </div>

          <div v-if="gameKey === 'monopoly'" class="gtv-field">
            <label class="gtv-label">席位</label>
            <div class="gtv-chips">
              <button
                v-for="n in [2, 3, 4, 5, 6, 7, 8]"
                :key="n"
                class="gtv-chip"
                :class="{ on: seatCount === n }"
                @click="seatCount = n"
              >{{ n }} 人</button>
            </div>
          </div>

          <div class="gtv-field">
            <label class="gtv-label">底注（每人开局预扣一份）</label>
            <div class="gtv-chips">
              <button
                v-for="s in stakes"
                :key="s.value"
                class="gtv-chip"
                :class="{ on: baseStake === s.value }"
                @click="baseStake = s.value"
              >{{ s.label }}</button>
            </div>
          </div>
        </div>

        <div class="gtv-actions">
          <button class="gtv-btn primary" :disabled="busy" @click="doCreate">
            {{ busy ? '建房中…' : '建房并邀请' }}
          </button>
        </div>
      </section>

      <!-- ========== 等待房 / 对局 ========== -->
      <section v-else class="gtv-stage">
        <!-- 等待房 -->
        <div v-if="room && room.status === 'waiting'" class="gtv-card">
          <header class="gtv-head">
            <div class="gtv-head-tx">
              <b>等待房 · {{ gameLabel }}</b>
              <i>房号 {{ room.id }} · 底注 {{ baseStake }} 豆 · 已入座 {{ joinedCount }}/{{ room.seats.length }}</i>
            </div>
            <div class="gtv-head-ops">
              <button class="gtv-btn ghost" @click="refresh">刷新</button>
              <button v-if="!room.is_host" class="gtv-btn ghost" @click="leaveRoom">退出</button>
              <button class="gtv-btn ghost danger" @click="dissolveRoom">解散牌桌</button>
            </div>
          </header>

          <div class="gtv-seats">
            <div
              v-for="s in room.seats"
              :key="s.seat"
              class="gtv-seat"
              :class="{ empty: !s.user_id, me: s.seat === room.my_seat, ai: s.is_ai, offline: s.autopilot }"
            >
              <span class="gtv-seat-av">{{ seatAvatar(s) }}</span>
              <b class="gtv-seat-name">{{ s.name || '空位' }}</b>
              <i class="gtv-seat-tag">
                <template v-if="s.is_ai">机器人</template>
                <template v-else-if="!s.user_id">空位</template>
                <template v-else-if="s.seat === room.my_seat">你</template>
                <template v-else-if="s.joined && s.online">已入座</template>
                <template v-else-if="s.joined">掉线托管</template>
                <template v-else>待入座</template>
              </i>
              <button
                v-if="room.is_host && s.user_id && s.seat !== room.my_seat && !s.is_ai"
                class="gtv-kick"
                title="移出该席位"
                @click="kick(s.seat)"
              >✕</button>
            </div>
          </div>

          <div class="gtv-actions">
            <template v-if="room.is_host">
              <button class="gtv-btn primary" :disabled="joinedCount < 2 || busy" @click="doStart">
                {{ busy ? '开局中…' : '开始牌局' }}
              </button>
              <span v-if="joinedCount < 2" class="gtv-hint">至少 2 位家人入座才能开局（1 人请玩单人练习）</span>
            </template>
            <span v-else class="gtv-hint">等房主开局…</span>
          </div>
        </div>

        <!-- 对局 / 结算（仅进行中或刚结束才渲染牌桌；abandoned 等终态走下方空态） -->
        <div
          v-else-if="room && (room.status === 'playing' || room.status === 'finished')"
          class="gtv-boardwrap"
          :class="{ 'is-fs': fullscreen }"
        >
          <!-- 顶部横条：全屏（放大）时隐藏，功能移到右侧竖栏 -->
          <div v-if="!fullscreen" class="gtv-boardhead">
            <span class="gtv-pill">{{ gameLabel }}</span>
            <span class="gtv-pill">房号 {{ room.id }}</span>
            <span class="gtv-pill">底注 {{ baseStake }}</span>
            <span class="gtv-pill">第 {{ room.round_no }} 局</span>
            <span class="gtv-spacer"></span>
            <span v-if="view && view.turn !== null && view.turn !== undefined" class="gtv-turnpill" :class="{ mine: isMyTurn }">
              {{ isMyTurn ? '轮到你' : `等 ${seatName(view.turn)} 行动` }}
            </span>
            <button class="gtv-btn ghost" @click="enterFullscreen">全屏</button>
            <button class="gtv-btn ghost danger" @click="dissolveRoom">解散牌桌</button>
            <button class="gtv-btn ghost" title="退出＝认输，本局立即按当前名次结算" @click="leaveRoom">退出对局（认输）</button>
          </div>

          <div ref="stageRef" class="gtv-viewstage" :class="{ 'is-fs': fullscreen }">
            <div
              ref="zoomRef"
              class="gtv-viewzoom"
              :class="{ 'is-fs': fullscreen }"
              :style="fullscreen ? zoomStyle : {}"
            >
              <component
                :is="boardComp"
                :key="room.id + '-' + room.round_no"
                online
                :online-view="view"
                :online-seat="room.my_seat ?? 0"
                :seat-names="seatNames"
                :is-host="room.is_host"
                :acting="busy"
                :big="true"
                @act="onAct"
                @rematch="doRematch"
                @exit="leaveRoom"
              />
            </div>
          </div>

          <!-- 全屏右侧竖栏：游戏说明 / 退出全屏 / 解散牌桌 / 返回列表 -->
          <nav v-if="fullscreen" class="gtv-rail" aria-label="牌桌操作">
            <button class="gtv-rail-btn" @click="showHelp = true">
              <i aria-hidden="true">📖</i><span>游戏说明</span>
            </button>
            <button class="gtv-rail-btn" @click="exitFullscreen">
              <i aria-hidden="true">⤡</i><span>退出全屏</span>
            </button>
            <button class="gtv-rail-btn danger" @click="dissolveRoom">
              <i aria-hidden="true">⛔</i><span>解散牌桌</span>
            </button>
            <button class="gtv-rail-btn" @click="goBack">
              <i aria-hidden="true">↩</i><span>返回列表</span>
            </button>
          </nav>

          <!-- 游戏说明（页内抽屉，非居中弹窗） -->
          <transition name="gtv-drawer">
            <div v-if="showHelp" class="gtv-help" @click.self="showHelp = false">
              <aside class="gtv-help-panel" role="dialog" aria-label="游戏说明">
                <header class="gtv-help-head">
                  <b>{{ gameLabel }} · 玩法说明</b>
                  <button class="gtv-rail-btn sm" aria-label="关闭说明" @click="showHelp = false">✕</button>
                </header>
                <ol class="gtv-help-list">
                  <li v-for="(r, i) in helpRules" :key="i">{{ r }}</li>
                </ol>
                <button class="gtv-btn primary" @click="showHelp = false">知道了</button>
              </aside>
            </div>
          </transition>
        </div>

        <!-- 加载 / 空态 / 已解散 -->
        <div v-else class="gtv-card gtv-loading">
          <span v-if="loading" class="gtv-spin" aria-hidden="true"></span>
          <p>{{ emptyText }}</p>
          <button class="gtv-btn ghost" @click="goBack">返回游戏列表</button>
        </div>
      </section>

      <!-- 手机端进入牌桌即自动全屏 + 尝试锁横屏，牌桌等比缩放铺满一屏（不再弹文案提示） -->

      <p v-if="error" class="gtv-error">{{ error }}</p>
    </div>
  </IslandInnerBase>
</template>

<script setup>
/** 牌类在线对局 · 等待房 / 牌桌宿主（v2.44）。
 *
 * 路由 `/tool/games/table/:id`：
 *   - `id === 'new'` → 建房表单（游戏从 `?game=` 取）
 *   - 其余 → 进入指定房间（等待房 → 对局 → 结算）
 *
 * 服务端权威：手牌由后端保管，前端只渲染 `view` 投影；动作走 `useGameTable().act()`。
 * 三款牌桌（掼蛋 / 麻将 / 大富翁）共用本页，靠 `game_key` 选板子。
 *
 * 全屏（v2.44.1）：隐藏顶部横条，改由右侧竖栏提供「游戏说明 / 退出全屏 / 返回列表」；
 * 手机端进入牌桌即自动全屏，牌桌按逻辑画布等比缩放铺满一屏，支持双指缩放 / 单指拖动。
 */
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { useGameTable } from '@/composables/useGameTable'
import { usePinchZoom } from '@/composables/usePinchZoom'
import { familyMembers } from '@/api/lifeExtra'
import { useIsMobile } from '@/composables/useIsMobile'

const route = useRoute()
const router = useRouter()
const t = useGameTable()

const GAME_META = {
  guandan: { label: '掼蛋', comp: () => import('@/components/games/GuandanBoard.vue'), seats: 4 },
  mahjong: { label: '四川麻将', comp: () => import('@/components/games/MahjongBoard.vue'), seats: 4 },
  monopoly: { label: '大富翁', comp: () => import('@/components/games/MonopolyBoard.vue'), seats: 4 },
}
const stakes = [
  { value: 100, label: '100 豆 · 轻松' },
  { value: 500, label: '500 豆 · 标准' },
  { value: 2000, label: '2000 豆 · 豪局' },
]
const HELP = {
  guandan: [
    '两副牌 108 张，4 人分两队：你与对家一队，左右两家一队。',
    '逢人配：红桃级牌可当除大小王以外的任意一张牌。',
    '牌型：单张 / 对子 / 三张 / 三带二 / 顺子（5 张）/ 三连对（6 张）/ 钢板（6 张）/ 炸弹（4 张及以上）/ 同花顺 / 四大天王。',
    '比大小：同牌型同张数比点数；炸弹压普通牌型，同花顺大于 5 张以下的炸弹，四大天王最大。',
    '升级：双上（头游、二游同队）+3 级，一三 +2 级，一四 +1 级；先打过 A 的一方整场获胜。',
    '进贡：上局输方按名次向赢方各进贡一张牌（逢人配除外），赢方各还一张 ≤10 的牌；进贡方合计持有两张大王可抗贡。',
  ],
  mahjong: [
    '四川麻将 · 血战到底，仅用万 / 条 / 筒 108 张，不含字牌。',
    '定缺：开局每人选一门作为缺门，该门牌必须先打完，之后才能碰、杠、胡。',
    '不能吃，只能碰与杠；有人胡牌后不下桌，继续打到牌墙摸完（血战到底）。',
    '刮风下雨：明杠 / 暗杠即时结算，由其余玩家付分。',
    '番型：平胡、对对胡、清一色、七对、龙七对、金钩钓、杠上花、杠上炮、抢杠胡等。',
  ],
  monopoly: [
    '掷骰前进，落在无主地块可购买，落在他人地块需付租金。',
    '同色地块集齐后可升级加盖，租金大幅提升。',
    '机会 / 命运格触发随机事件；税格缴税；监狱格暂停行动。',
    '在线对局支持拍卖、交易与道具等玩法。',
    '现金为负即破产出局，最后存活者获胜。',
  ],
}

const mode = ref('create')            // create | room
const gameKey = ref('guandan')
const invitees = ref([])
const baseStake = ref(100)
const seatCount = ref(4)
const families = ref([])
const error = ref('')
const showHelp = ref(false)
const fullscreen = ref(false)
const { isMobile } = useIsMobile()

const room = t.room
const view = t.view
const busy = t.busy
const loading = t.loading

const meta = computed(() => GAME_META[gameKey.value] || GAME_META.guandan)
const gameLabel = computed(() => meta.value.label)
const pageTitle = computed(() => (mode.value === 'create' ? `开桌 · ${gameLabel.value}` : `牌桌 · ${gameLabel.value}`))
const pageSubtitle = computed(() => '服务端权威发牌 · 跨设备同步 · 空位机器人补位')
const helpRules = computed(() => HELP[gameKey.value] || HELP.guandan)

const boardComp = computed(() => defineAsyncComponent(meta.value.comp))
const seatNames = computed(() => (room.value?.seats || []).map(s => s.name || '家人'))
const joinedCount = computed(() =>
  (room.value?.seats || []).filter(s => s.is_ai || (s.user_id && s.joined)).length)
const isMyTurn = computed(() => t.isMyTurn.value)
/** 空态文案：区分「进入中 / 已解散 / 不存在」 */
const emptyText = computed(() => {
  if (loading.value) return '正在进入牌桌…'
  if (room.value?.status === 'dissolved') return '牌桌已解散（有人解散了本桌，可回列表重新开一局）'
  if (room.value?.status === 'abandoned') return '牌桌已失效（长时间无操作）'
  return '牌桌不存在或已结束'
})

/* ---------- 全屏 + 缩放/拖动 ---------- */
const stageRef = ref(null)
const zoomRef = ref(null)
const { style: zoomStyle, ready: zoomReady, measure: zoomMeasure, bind: zoomBind } = usePinchZoom(
  stageRef, () => fullscreen.value,
)
let unbindZoom = null
let measureTimer = null
let contentRO = null

function scheduleMeasure() {
  clearTimeout(measureTimer)
  let tries = 0
  const tick = () => {
    zoomMeasure()
    if (!zoomReady.value && tries++ < 40) measureTimer = setTimeout(tick, 60)
  }
  nextTick(() => requestAnimationFrame(tick))
}

function enterFullscreen() {
  fullscreen.value = true
  // lock() 返回 Promise，多数浏览器会异步 reject；不接住会变成未处理拒绝（控制台报错）
  try { screen.orientation?.lock?.('landscape')?.catch?.(() => {}) } catch { /* 忽略 */ }
}
function exitFullscreen() {
  fullscreen.value = false
  try { screen.orientation?.unlock?.() } catch { /* 忽略 */ }
}

watch(fullscreen, async (v) => {
  unbindZoom?.()
  unbindZoom = null
  contentRO?.disconnect()
  contentRO = null
  if (!v) return
  await nextTick()
  unbindZoom = zoomBind(stageRef.value)
  scheduleMeasure()
  // 牌桌是异步组件：挂载/换局/内容变化后重新量一次，保证「铺满一屏」始终按最新尺寸算
  if (typeof ResizeObserver !== 'undefined' && zoomRef.value) {
    contentRO = new ResizeObserver(() => { if (fullscreen.value) scheduleMeasure() })
    contentRO.observe(zoomRef.value)
  }
})

function onResize() { if (fullscreen.value) scheduleMeasure() }

function seatName(seat) {
  const s = (room.value?.seats || []).find(x => x.seat === seat)
  if (!s) return `座位${seat + 1}`
  if (seat === room.value.my_seat) return '你'
  return s.name || `座位${seat + 1}`
}
function seatAvatar(s) {
  if (s.seat === room.value?.my_seat) return '🙂'
  if (s.is_ai) return '🤖'
  if (!s.user_id) return '➕'
  return '🙃'
}

function toggleInvitee(uid) {
  const i = invitees.value.indexOf(uid)
  if (i >= 0) invitees.value.splice(i, 1)
  else invitees.value.push(uid)
}

async function loadFamilies() {
  try {
    const res = await familyMembers()
    families.value = (res?.data?.list || []).filter(m => m.user_id && m.user_id !== t.myUserId.value)
  } catch { families.value = [] }
}

async function doCreate() {
  error.value = ''
  try {
    const seat = gameKey.value === 'monopoly' ? seatCount.value : null
    await t.create(gameKey.value, {
      inviteeUserIds: invitees.value,
      baseStake: baseStake.value,
      seatCount: seat,
    })
    if (room.value?.id) {
      mode.value = 'room'
      router.replace(`/tool/games/table/${room.value.id}`)
      ElMessage.success('牌桌已创建，等家人入座')
    }
  } catch (e) {
    error.value = e?.msg || e?.response?.data?.detail || '建房失败'
    ElMessage.warning(error.value)
  }
}

async function refresh() { await t.refresh() }

async function kick(seat) {
  try { await t.seatOp({ action: 'kick', seat }) } catch (e) { ElMessage.warning(e?.msg || '操作失败') }
}

async function doStart() {
  error.value = ''
  try { await t.start() } catch (e) {
    error.value = e?.msg || e?.response?.data?.detail || '开局失败'
    ElMessage.warning(error.value)
  }
}

async function onAct(action) {
  error.value = ''
  try { await t.act(action) } catch (e) {
    error.value = e?.msg || e?.response?.data?.detail || '操作失败'
    ElMessage.warning(error.value)
  }
}

async function doRematch() {
  try { await t.rematch() } catch (e) { ElMessage.warning(e?.msg || '重开失败') }
}

async function leaveRoom() {
  await t.leave()
  goBack()
}

/** 解散整桌：任何在座家人都可；不判输赢（已开局会退还底注），随后回列表 */
async function dissolveRoom() {
  error.value = ''
  try { await t.dissolve() } catch (e) {
    ElMessage.warning(e?.msg || e?.response?.data?.detail || '解散失败')
  }
  goBack()
}

function goBack() { router.push('/tool/games') }

/* ---------- 生命周期 ---------- */
async function enterRoom(id) {
  try {
    await t.join(id, { autoJoin: true })
    gameKey.value = room.value?.game_key || gameKey.value
  } catch (e) {
    error.value = e?.msg || e?.response?.data?.detail || '进入牌桌失败'
  }
}

onMounted(async () => {
  const id = route.params.id
  if (!id || id === 'new') {
    mode.value = 'create'
    gameKey.value = String(route.query.game || 'guandan')
    if (!GAME_META[gameKey.value]) gameKey.value = 'guandan'
    await loadFamilies()
  } else {
    mode.value = 'room'
    await enterRoom(Number(id))
  }
  if (isMobile.value) {
    try { await screen.orientation?.lock?.('landscape') } catch { /* 多数浏览器不允许，忽略 */ }
    // 手机端进入牌桌默认全屏：一屏放下整张牌桌
    if (mode.value === 'room') fullscreen.value = true
  }
  window.addEventListener('resize', onResize)
})

function onUnload() { t.leaveOnUnload() }
window.addEventListener('pagehide', onUnload)
onBeforeUnmount(() => {
  window.removeEventListener('pagehide', onUnload)
  window.removeEventListener('resize', onResize)
  clearTimeout(measureTimer)
  unbindZoom?.()
  contentRO?.disconnect()
  t.leaveOnUnload()
})
</script>

<style scoped>
.gtv-root { padding: 4px 2px 20px; }
.gtv-card {
  border-radius: 18px; padding: 18px 20px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.1));
  background: linear-gradient(160deg, rgba(255,255,255,.86), rgba(250,248,243,.72));
  box-shadow: 0 10px 30px rgba(20,30,40,.06);
  backdrop-filter: blur(14px);
}
:root[data-theme="night"] .gtv-card {
  background: linear-gradient(160deg, rgba(38,44,58,.86), rgba(22,26,36,.8));
  border-color: rgba(199,169,107,.22);
}
.gtv-head { display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.gtv-head-tx { flex: 1; min-width: 200px; }
.gtv-head-tx b { font-size: 16px; color: var(--dp-text, #18202a); }
.gtv-head-tx i { display: block; margin-top: 3px; font-style: normal; font-size: 12.5px; color: var(--dp-text3, #8a8f98); }
:root[data-theme="night"] .gtv-head-tx b { color: #f2eee4; }
.gtv-head-ops { display: flex; gap: 8px; }

.gtv-form { display: flex; flex-direction: column; gap: 16px; margin: 16px 0; }
.gtv-field { display: flex; flex-direction: column; gap: 8px; }
.gtv-label { font-size: 13px; font-weight: 600; color: var(--dp-text2, #45505b); }
:root[data-theme="night"] .gtv-label { color: #cfc9dd; }
.gtv-members { display: flex; flex-wrap: wrap; gap: 8px; }
.gtv-member {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 12px;
  cursor: pointer; font-family: inherit; font-size: 13.5px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14));
  background: rgba(255,255,255,.6); color: var(--dp-text, #18202a);
  transition: border-color .2s, background .2s;
}
.gtv-member.on { border-color: var(--yq-gold, #c7a96b); background: rgba(199,169,107,.16); font-weight: 600; }
:root[data-theme="night"] .gtv-member { background: rgba(255,255,255,.06); color: #f2eee4; }
.gtv-ava { font-size: 15px; }
.gtv-check { color: var(--yq-gold, #c7a96b); }
.gtv-empty { margin: 0; font-size: 12.5px; color: var(--dp-text3, #8a8f98); }

.gtv-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.gtv-chip {
  padding: 7px 14px; border-radius: 10px; cursor: pointer; font-family: inherit; font-size: 13px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: rgba(255,255,255,.6);
  color: var(--dp-text, #18202a); transition: border-color .2s, background .2s;
}
.gtv-chip.on { border-color: var(--yq-gold, #c7a96b); background: rgba(199,169,107,.18); font-weight: 600; }
:root[data-theme="night"] .gtv-chip { background: rgba(255,255,255,.06); color: #f2eee4; }

.gtv-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 14px; }
.gtv-btn {
  padding: 9px 18px; border-radius: 12px; cursor: pointer; font-family: inherit; font-size: 13.5px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: rgba(255,255,255,.7);
  color: var(--dp-text, #18202a); transition: transform .15s, box-shadow .2s, border-color .2s;
}
.gtv-btn:hover { transform: translateY(-1px); border-color: rgba(199,169,107,.6); }
.gtv-btn.primary { background: linear-gradient(160deg, #c7a96b, #b2914f); color: #241d0c; border-color: transparent; font-weight: 700; }
.gtv-btn.primary:disabled, .gtv-btn:disabled { opacity: .5; cursor: not-allowed; transform: none; }
.gtv-btn.ghost { background: transparent; }
.gtv-btn.danger { color: #c85050; border-color: rgba(200,80,80,.4); }
.gtv-btn.danger:hover { border-color: rgba(200,80,80,.75); background: rgba(200,80,80,.1); }
:root[data-theme="night"] .gtv-btn.danger { color: #e78b8b; border-color: rgba(231,139,139,.45); }
:root[data-theme="night"] .gtv-btn { background: rgba(255,255,255,.08); color: #f2eee4; }
.gtv-btn.primary { color: #241d0c; }
.gtv-hint { font-size: 12.5px; color: var(--dp-text3, #8a8f98); }

/* 席位网格 */
.gtv-seats {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px; margin: 18px 0;
}
.gtv-seat {
  position: relative; display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 16px 12px; border-radius: 16px; text-align: center;
  border: 1px solid var(--dp-line, rgba(0,0,0,.12)); background: rgba(255,255,255,.55);
}
.gtv-seat.me { border-color: var(--yq-gold, #c7a96b); background: rgba(199,169,107,.14); }
.gtv-seat.empty { border-style: dashed; opacity: .72; }
.gtv-seat.ai { background: rgba(127,168,163,.12); }
.gtv-seat.offline { opacity: .66; }
:root[data-theme="night"] .gtv-seat { background: rgba(255,255,255,.05); }
.gtv-seat-av { font-size: 26px; line-height: 1; }
.gtv-seat-name { font-size: 14px; color: var(--dp-text, #18202a); }
:root[data-theme="night"] .gtv-seat-name { color: #f2eee4; }
.gtv-seat-tag { font-style: normal; font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.gtv-kick {
  position: absolute; top: 6px; right: 6px; width: 22px; height: 22px; border-radius: 50%;
  border: none; cursor: pointer; font-size: 11px; line-height: 1;
  background: rgba(0,0,0,.08); color: var(--dp-text2, #45505b);
}
.gtv-kick:hover { background: rgba(200,80,80,.18); color: #c85050; }

/* 对局 */
.gtv-boardwrap { display: flex; flex-direction: column; gap: 10px; }
.gtv-boardhead { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.gtv-pill {
  padding: 5px 12px; border-radius: 999px; font-size: 12.5px;
  background: rgba(127,168,163,.14); color: var(--dp-text2, #45505b);
  border: 1px solid rgba(127,168,163,.28);
}
:root[data-theme="night"] .gtv-pill { color: #cfc9dd; }
.gtv-spacer { flex: 1; }
.gtv-turnpill {
  padding: 5px 12px; border-radius: 999px; font-size: 12.5px; font-weight: 600;
  background: rgba(127,168,163,.18); color: var(--dp-text2, #45505b);
}
.gtv-turnpill.mine { background: rgba(199,169,107,.24); color: #7a5f1d; }
:root[data-theme="night"] .gtv-turnpill.mine { color: #f0d79a; }

/* ---------- 全屏牌桌 ---------- */
.gtv-boardwrap.is-fs {
  position: fixed; inset: 0; z-index: 3000; display: block; padding: 0;
  background: radial-gradient(120% 90% at 50% 0%, #123a2e, #061410 70%);
}
.gtv-viewstage.is-fs {
  position: absolute; top: 0; left: 0; right: 64px; bottom: 0;
  overflow: hidden; touch-action: none; overscroll-behavior: none;
}
/* 逻辑画布：按桌面布局渲染，再整体等比缩放到一屏。
   宽高由 usePinchZoom 内联给出（宽随舞台宽高比、高固定），故此处 1280×720 仅作 JS 就绪前的兜底。 */
.gtv-viewzoom.is-fs {
  position: absolute; top: 0; left: 0; width: 1280px; height: 720px;
  transform-origin: 0 0; will-change: transform;
}
/* 中间层 .gt-landscape 必须给出确定高度：否则 .gt-shell 的 height:100% 会解析成 auto，
   高度退回内容尺寸（大富翁方棋盘 760 + padding ≈ 788 > 720）→ fit 被高度卡住 → 左右留黑边。 */
.gtv-viewzoom.is-fs :deep(.gt-landscape) { height: 100%; }
/* 牌桌外壳撑满逻辑画布：这样外壳宽高比 = 舞台宽高比，等比缩放后两轴都铺满 */
.gtv-viewzoom.is-fs :deep(.gt-shell) { width: 100%; height: 100%; min-height: 0; }
/* 全屏时顶栏横条让位，牌桌本体顶到最上 */
.gtv-boardwrap.is-fs :deep(.gd-top),
.gtv-boardwrap.is-fs :deep(.mj-top),
.gtv-boardwrap.is-fs :deep(.mp-side-bar) { display: none; }

/* 全屏画布按**桌面布局**渲染后再整体缩放，故需抵消牌桌自身针对窄屏的响应式收窄：
   否则手机横屏（viewport ≤1100px）下大富翁右栏会被折到棋盘下方，整块被压得极小。 */
.gtv-viewzoom.is-fs :deep(.mp) { grid-template-columns: minmax(0, 1fr) 306px; min-height: 640px; }
.gtv-viewzoom.is-fs :deep(.mp-cname) { font-size: 9px; }
/* 方棋盘受可用高度约束（否则 760px 见方撑破 720 逻辑高度，等比缩放后左右留黑边） */
.gtv-viewzoom.is-fs :deep(.mp-board) { max-height: 100%; }

/* 右侧竖向三按钮 */
.gtv-rail {
  position: absolute; top: 50%; right: 8px; transform: translateY(-50%);
  z-index: 5; display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.gtv-rail-btn {
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  width: 52px; padding: 8px 4px; border-radius: 14px; cursor: pointer;
  font-family: inherit; font-size: 10.5px; line-height: 1.15; text-align: center;
  color: #f2eee4; border: 1px solid rgba(233,200,119,.34);
  background: linear-gradient(180deg, rgba(30,52,44,.9), rgba(12,26,21,.9));
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 8px 20px -12px rgba(0,0,0,.9);
  transition: border-color .2s, transform .15s;
}
.gtv-rail-btn:hover { border-color: var(--yq-gold, #c7a96b); transform: translateY(-1px); }
.gtv-rail-btn.danger { border-color: rgba(231,139,139,.5); }
.gtv-rail-btn.danger:hover { border-color: #e78b8b; }
.gtv-rail-btn i { font-style: normal; font-size: 16px; line-height: 1; }
.gtv-rail-btn.sm { width: 28px; height: 28px; padding: 0; border-radius: 50%; font-size: 12px; }

/* 游戏说明抽屉（页内右侧滑入，非居中弹窗） */
.gtv-help {
  position: fixed; inset: 0; z-index: 3100;
  background: rgba(4,12,10,.5); backdrop-filter: blur(3px);
}
.gtv-help-panel {
  position: absolute; top: 0; right: 0; bottom: 0;
  width: min(88vw, 380px); display: flex; flex-direction: column; gap: 14px;
  padding: 18px 18px 22px; overflow-y: auto;
  background: linear-gradient(165deg, rgba(26,48,41,.98), rgba(8,22,18,.98));
  border-left: 1px solid rgba(233,200,119,.4);
  box-shadow: -20px 0 50px -20px rgba(0,0,0,.95);
}
.gtv-help-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.gtv-help-head b { font-size: 15px; color: var(--yq-gold, #c7a96b); }
.gtv-help-list { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 9px; }
.gtv-help-list li { font-size: 12.5px; line-height: 1.7; color: #e6e2d6; }
.gtv-help-panel .gtv-btn { align-self: flex-start; }
.gtv-drawer-enter-active, .gtv-drawer-leave-active { transition: opacity .2s ease; }
.gtv-drawer-enter-active .gtv-help-panel, .gtv-drawer-leave-active .gtv-help-panel {
  transition: transform .24s ease;
}
.gtv-drawer-enter-from, .gtv-drawer-leave-to { opacity: 0; }
.gtv-drawer-enter-from .gtv-help-panel, .gtv-drawer-leave-to .gtv-help-panel { transform: translateX(100%); }

/* 加载 */
.gtv-loading { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 48px 20px; }
.gtv-spin {
  width: 30px; height: 30px; border-radius: 50%;
  border: 3px solid rgba(127,168,163,.25); border-top-color: var(--yq-jade, #7fa8a3);
  animation: gtv-spin .8s linear infinite;
}
@keyframes gtv-spin { to { transform: rotate(360deg); } }

/* 横屏提示已移除：手机端进桌即自动全屏并等比铺满一屏，不再用文案打断操作 */

.gtv-error { margin: 12px 0 0; font-size: 13px; color: #c85050; }

@media (prefers-reduced-motion: reduce) {
  .gtv-drawer-enter-active, .gtv-drawer-leave-active,
  .gtv-drawer-enter-active .gtv-help-panel, .gtv-drawer-leave-active .gtv-help-panel { transition: none; }
}
</style>
