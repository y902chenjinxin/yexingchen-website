<template>
  <IslandInnerBase type="tool" title="棋类游戏" subtitle="五子棋 · 围棋 · 飞行棋 · 数独 · 扫雷 · 贪吃蛇">
    <div class="gm-root" :class="{ 'is-big': isBig }">
      <!-- ===== 左：游戏类型 ===== -->
      <aside v-show="!isBig" class="gm-rail">
        <div v-for="grp in groups" :key="grp.name" class="gm-grp">
          <div class="gm-grp-name">{{ grp.name }}</div>
          <button
            v-for="g in grp.items"
            :key="g.key"
            class="gm-item"
            :class="{ on: tab === g.key, dim: itemLocked(g) }"
            :disabled="itemLocked(g)"
            :title="itemLocked(g) ? '对局进行中 —— 退出对局后才能切换' : ''"
            @click="pick(g.key)"
          >
            <!-- eslint-disable-next-line vue/no-v-html -- 图标为本地常量字符串，无外部输入 -->
            <span class="gm-item-ic" v-html="g.icon"></span>
            <span class="gm-item-tx">
              <b>{{ g.label }}</b>
              <i>{{ g.tag }}</i>
            </span>
            <span v-if="saves[g.key]" class="gm-item-dot" title="有未完成的存档"></span>
          </button>
        </div>
      </aside>

      <!-- ===== 右：游戏空间 ===== -->
      <section ref="stageRef" class="gm-stage">
        <!-- 空态：默认什么都不摆，避免一屏平铺 -->
        <div v-if="!tab" class="gm-empty">
          <div class="gm-empty-ic">♟</div>
          <b>从左边挑一个游戏</b>
          <p>选中后先选模式，再进对局。想看得舒服一点，进去后可点「放大」全屏玩，随时能退出或续上进度。</p>
        </div>

        <template v-else>
          <header class="gm-head">
            <div class="gm-head-tx">
              <b>{{ cur.label }}</b>
              <i>{{ cur.desc }}</i>
            </div>
            <div class="gm-head-ops">
              <span v-if="roomLocked" class="gm-locktip">🔒 对局进行中</span>
              <button class="gm-op" @click="toggleBig">{{ isBig ? '退出全屏' : '放大' }}</button>
              <button class="gm-op ghost" @click="backToList">返回列表</button>
            </div>
          </header>

          <!-- 第一步：先选模式 -->
          <div v-if="phase === 'setup'" class="gm-setup">
            <div class="gm-setup-title">选择模式</div>
            <div class="gm-modecards">
              <button
                v-for="m in cur.modes"
                :key="m.key"
                class="gm-modecard"
                @click="startGame(m.key)"
              >
                <b>{{ m.label }}</b>
                <i>{{ m.hint }}</i>
              </button>
            </div>
            <div v-if="cur.boardSizes" class="gm-size">
              <span class="gm-size-label">棋盘大小</span>
              <button
                v-for="s in cur.boardSizes"
                :key="s"
                class="gm-sizebtn"
                :class="{ on: chosenBoard === s }"
                @click="chosenBoard = s"
              >{{ s }}×{{ s }}</button>
              <span class="gm-size-hint">开局定好就不再变（在线对战固定 15×15）</span>
            </div>
            <button v-if="saves[tab]" class="gm-resume" @click="resumeGame">
              ▶ 继续上一局 · {{ saves[tab].summary }}
              <em>{{ age(saves[tab].ts) }}</em>
            </button>
          </div>

          <!-- 第二步：对局 -->
          <div v-else class="gm-play">
            <component
              :is="cur.component"
              :key="runKey"
              :initial-mode="chosenMode"
              :board-size="chosenBoard"
              :resume="resumeFlag"
              :bare="true"
              :join-room-id="pendingRoom.game === cur.key ? pendingRoom.id : 0"
              @room-lock="roomLocked = true"
              @room-unlock="roomLocked = false"
            />
          </div>
        </template>
      </section>
    </div>
  </IslandInnerBase>
</template>

<script setup>
/** 棋类游戏（v2.40.29 交互重构）。
 *
 * 布局：左「游戏类型」栏 + 右「游戏空间」，默认空态（不预渲染任何棋盘）；
 * 分步：选类型 → 选模式 → 进对局，避免一屏平铺；
 * 大屏：舞台容器全屏化（fixed），组件**不重新挂载**，因此对局与进度天然保留；
 * 进度：自研游戏写 localStorage 存档（utils/gameSave），回列表后可「继续上一局」。
 * 加新游戏 = 写一个自包含组件 + 在 gamelist 加一行（modes/boardSizes/big 声明能力）。
 * v2.40.33：按夜星要求**黑白棋下架**（不是他要的，组件 OthelloBoard.vue 保留，说一声可恢复），
 *           换成**围棋**（新组件 GoBoard.vue，中国规则数子法）。
 * v2.40.34：飞行棋由 iframe 嵌第三方静态页（LudoEmbed.vue）改为**自写 LudoBoard.vue** ——
 *           原方案的「选择人数」弹层被 iframe 高度裁切，点了人数看不到「开始游戏」按钮（表现为点了没反应），
 *           且第三方是同屏多人、无联机能力，无法「邀请家人」。现在支持 2/3/4 人同屏 + 在线邀请。
 */
import { ref, reactive, computed, watch, nextTick, onBeforeUnmount, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { loadGame, clearGame, saveAge } from '@/utils/gameSave'

const ICON = {
  gomoku: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/><circle cx="9" cy="9" r="2" fill="currentColor" stroke="none"/></svg>',
  othello: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/></svg>',
  ludo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 4v16M4 12h16"/><circle cx="8.2" cy="8.2" r="1.4" fill="currentColor" stroke="none"/><circle cx="15.8" cy="15.8" r="1.4" fill="currentColor" stroke="none"/></svg>',
  sudoku: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M9.2 3.5v17M14.8 3.5v17M3.5 9.2h17M3.5 14.8h17"/></svg>',
  mine: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="13" r="6"/><path d="M12 7V3M4.6 10.6 2 8M19.4 10.6 22 8M7 19l-2 2M17 19l2 2"/></svg>',
  go: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3.5" y="3.5" width="17" height="17" rx="2"/><path d="M9.2 3.5v17M14.8 3.5v17M3.5 9.2h17M3.5 14.8h17"/><circle cx="9.2" cy="9.2" r="2" fill="currentColor" stroke="none"/><circle cx="14.8" cy="14.8" r="2" fill="currentColor" stroke="none"/></svg>',
  snake: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 17h7a3 3 0 0 0 3-3V8a3 3 0 0 1 3-3h2"/><rect x="2" y="15.5" width="2.6" height="2.6" rx="1" fill="currentColor" stroke="none"/><circle cx="18.6" cy="4.6" r="1.5" fill="currentColor" stroke="none"/></svg>',
}

const gamelist = [
  {
    key: 'gomoku', label: '五子棋', tag: '15×15 · AI 三档', group: '棋类',
    desc: '五子连珠取胜；同屏双人、单机陪练，或在线邀请家人。',
    icon: ICON.gomoku,
    component: defineAsyncComponent(() => import('@/components/games/GomokuBoard.vue')),
    boardSizes: [15, 19, 23],   // 开局可选棋盘大小（对局中固定，不自动变化）
    modes: [
      { key: 'pvp', label: '双人同屏', hint: '一台设备轮着下' },
      { key: 'easy', label: '单机 · 简单', hint: 'AI 只看一步，适合陪练' },
      { key: 'hard', label: '单机 · 困难', hint: 'AI 三层搜索，会堵会攻' },
      { key: 'online', label: '在线 · 邀请对战', hint: '建房邀请家人，跨设备同步' },
    ],
  },
  {
    key: 'go', label: '围棋', tag: '9/13/19 路 · 入门 AI', group: '棋类',
    desc: '气与提子、禁自杀、打劫；双方各停一手后自动数子（中国规则，黑贴 7.5 目）。',
    icon: ICON.go,
    component: defineAsyncComponent(() => import('@/components/games/GoBoard.vue')),
    boardSizes: [9, 13, 19],
    modes: [
      { key: 'pvp', label: '双人同屏', hint: '一台设备轮着下' },
      { key: 'easy', label: '单机 · 入门', hint: 'AI 会吃子、会逃跑，但不强' },
      { key: 'hard', label: '单机 · 稍强', hint: '多看一层；仍是入门水平' },
    ],
  },
  {
    key: 'ludo', label: '飞行棋', tag: '中国规则 · 大屏', group: '棋类', big: true,
    desc: '掷 6 起飞、踩同色飞跃、飞行通道直飞；双人/三人/四人同屏，或在线邀请家人。',
    icon: ICON.ludo,
    component: defineAsyncComponent(() => import('@/components/games/LudoBoard.vue')),
    modes: [
      { key: 'pvp2', label: '双人同屏', hint: '红 vs 黄，一台设备轮着掷' },
      { key: 'pvp3', label: '三人同屏', hint: '红绿黄混战，谁先归航' },
      { key: 'pvp4', label: '四人同屏', hint: '四色全上，最热闹' },
      { key: 'online', label: '在线 · 邀请对战', hint: '建房邀请家人，跨设备同步' },
    ],
  },
  {
    key: 'sudoku', label: '数独', tag: '唯一解 · 三档', group: '益智',
    desc: '挖洞带唯一解校验；填错标红，卡住可提示一格。',
    icon: ICON.sudoku,
    component: defineAsyncComponent(() => import('@/components/games/SudokuBoard.vue')),
    modes: [
      { key: 'easy', label: '入门', hint: '挖 38 洞，轻松热手' },
      { key: 'mid', label: '进阶', hint: '挖 45 洞，需要点耐心' },
      { key: 'hard', label: '困难', hint: '挖 52 洞，慢慢来' },
    ],
  },
  {
    key: 'mine', label: '扫雷', tag: '10×10 · 15 雷', group: '益智',
    desc: '经典扫雷，手机上可开「旗子模式」代替右键。',
    icon: ICON.mine,
    component: defineAsyncComponent(() => import('@/components/games/MineGame.vue')),
    modes: null,
  },
  {
    key: 'snake', label: '贪吃蛇', tag: '最高分记录', group: '休闲',
    desc: '经典贪吃蛇，记录本机最高分。',
    icon: ICON.snake,
    component: defineAsyncComponent(() => import('@/components/games/SnakeGame.vue')),
    modes: null,
  },
]
const ALL = Object.fromEntries(gamelist.map(g => [g.key, g]))
const groups = ['棋类', '益智', '休闲']
  .map(name => ({ name, items: gamelist.filter(g => g.group === name) }))
  .filter(g => g.items.length)

/* ---------- 状态 ---------- */
const tab = ref('')            // '' = 空态（默认什么都不摆）
const phase = ref('setup')     // setup=选模式 / play=对局
const chosenMode = ref('')
const chosenBoard = ref(15)   // 开局棋盘边长（五子棋可选 15/19/23）
const resumeFlag = ref(false)
const runId = ref(0)           // 变更即强制重新挂载组件（开新局）
const isBig = ref(false)       // 舞台全屏
const roomLocked = ref(false)  // 在线对局进行中 → 锁左栏
const pendingRoom = ref({ id: 0, game: '' })

const cur = computed(() => ALL[tab.value] || {})
const runKey = computed(() => `${tab.value}-${runId.value}`)

const saves = reactive({})
function refreshSaves() {
  for (const g of gamelist) saves[g.key] = loadGame(g.key)
}
refreshSaves()
const age = saveAge

function itemLocked(g) {
  return roomLocked.value && tab.value && g.key !== tab.value
}

/* ---------- 分步流程 ---------- */
function pick(key) {
  const g = ALL[key]
  if (!g) return
  if (itemLocked(g)) { ElMessage.warning('对局进行中 —— 先点「退出对局」再切换'); return }
  tab.value = key
  chosenMode.value = ''
  chosenBoard.value = g.boardSizes ? g.boardSizes[0] : 15
  resumeFlag.value = false
  isBig.value = !!g.big
  phase.value = g.modes ? 'setup' : 'play'
  runId.value += 1
  refreshSaves()
}

function startGame(modeKey) {
  clearGame(tab.value)         // 开新局 → 旧存档作废
  refreshSaves()
  chosenMode.value = modeKey
  resumeFlag.value = false
  phase.value = 'play'
  runId.value += 1
}

function resumeGame() {
  const s = saves[tab.value]
  if (!s) return
  chosenMode.value = s.mode || ''
  resumeFlag.value = true
  phase.value = 'play'
  runId.value += 1
}

function backToList() {
  if (roomLocked.value) { ElMessage.warning('对局进行中 —— 先「退出对局（认输）」再离开'); return }
  isBig.value = false
  refreshSaves()
  tab.value = ''
  phase.value = 'setup'
  chosenMode.value = ''
  runId.value += 1
}

function toggleBig() { isBig.value = !isBig.value }

/* 大屏要把整座岛抬到应用侧栏(90)/顶栏(1000)之上。
 * 坑：.island-inner / .inner-content 自身是 position:relative + z-index:1 —— **自成层叠上下文**，
 * 子树里再大的 z-index 也只能在 z=1 这一层里排，于是 fixed 舞台会被侧栏盖住。
 * 所以必须抬祖先，而不是加大屏自己的 z-index。 */
const stageRef = ref(null)
function raiseHost(on) {
  let p = stageRef.value?.parentElement
  while (p && p !== document.body) {
    if (p.classList?.contains('inner-content') || p.classList?.contains('island-inner')) {
      p.style.zIndex = on ? '1200' : ''
    }
    p = p.parentElement
  }
}
watch(isBig, async (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
  await nextTick()
  raiseHost(v)
})
onBeforeUnmount(() => { document.body.style.overflow = ''; raiseHost(false) })

/* ---------- 从全局邀请弹窗跳进来（/tool/games?room=ID&game=gomoku） ----------
 * ⚠️ 清 URL 参数**绝不能**用 router.replace({query:{}})：App.vue 的 RouterView 是
 * `:key="route.fullPath"`，URL 一变整页就销毁重建、刚设好的 tab/phase 全丢 ——
 * 这正是「接受邀请后回到空态、进不去对局」的根因（桌面端同样中招，上一版用 sessionStorage
 * 兜底也只是亡羊补牢）。这里直接改 history，不触发 vue-router 导航，状态原地保留。
 * 保留 history.state（含 router 内部字段），避免前进/后退信息错乱。 */
const route = useRoute()

function enterRoom(id, game) {
  pendingRoom.value = { id, game }
  tab.value = game
  chosenMode.value = 'online'
  resumeFlag.value = false
  phase.value = 'play'          // 受邀方直接进对局，不再走模式选择
  isBig.value = false
  runId.value += 1
}

watch(() => route.query.room, (v) => {
  const id = Number(v) || 0
  const game = String(route.query.game || '')
  if (!id || !ALL[game]) return
  enterRoom(id, game)
  try { window.history.replaceState(window.history.state, '', route.path) } catch { /* 忽略 */ }
}, { immediate: true })
</script>

<style scoped>
/* ===== 布局：左栏 + 舞台 ===== */
.gm-root {
  display: grid; grid-template-columns: 232px minmax(0, 1fr); gap: 18px;
  align-items: start; width: 100%;
}
/* 大屏：压过应用侧栏(90/95)与顶栏，整屏沉浸；头部吸顶，保证「退出全屏/返回列表」随时可点 */
.gm-root.is-big .gm-stage {
  position: fixed; inset: 0; z-index: 400; overflow-y: auto;
  background: var(--dp-bg, #f7f5f0); padding: 14px 24px 36px;
}
.gm-root.is-big .gm-head {
  position: sticky; top: 0; z-index: 3; background: var(--dp-bg, #f7f5f0);
  padding: 8px 0 10px; box-shadow: 0 8px 16px -12px rgba(20, 30, 40, .5);
}

/* ===== 左栏 ===== */
.gm-rail { display: flex; flex-direction: column; gap: 16px; }
.gm-grp { display: flex; flex-direction: column; gap: 6px; }
.gm-grp-name {
  font-size: 11.5px; letter-spacing: .08em; color: var(--dp-text3, #8a8f98);
  padding: 0 4px 4px; font-weight: 600;
}
.gm-item {
  display: flex; align-items: center; gap: 10px; width: 100%; text-align: left;
  padding: 9px 11px; border-radius: 13px; cursor: pointer; font-family: inherit;
  border: 1px solid transparent; background: transparent; transition: all .18s;
  position: relative;
}
.gm-item:hover { background: rgba(255,255,255,.6); }
.gm-item.on {
  background: var(--dp-surface, #fff); border-color: var(--yq-gold, #c7a96b);
  box-shadow: 0 4px 14px rgba(20,30,40,.07);
}
.gm-item.dim { opacity: .38; cursor: not-allowed; }
.gm-item-ic { width: 22px; height: 22px; flex: none; color: var(--yq-gold, #c7a96b); }
.gm-item-ic :deep(svg) { width: 22px; height: 22px; display: block; }
.gm-item-tx { min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.gm-item-tx b { font-size: 13.5px; color: var(--dp-text, #18202a); font-weight: 600; }
.gm-item-tx i { font-style: normal; font-size: 11px; color: var(--dp-text3, #8a8f98); }
.gm-item-dot {
  position: absolute; right: 10px; top: 50%; margin-top: -3px; width: 6px; height: 6px;
  border-radius: 50%; background: var(--yq-gold, #c7a96b);
}

/* ===== 舞台 ===== */
.gm-stage { min-height: 340px; display: flex; flex-direction: column; gap: 14px; }
.gm-empty {
  flex: 1; min-height: 320px; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 8px; text-align: center; padding: 40px 20px;
  border: 1px dashed var(--dp-line, rgba(0,0,0,.14)); border-radius: 18px;
  background: linear-gradient(160deg, rgba(255,255,255,.5), rgba(255,255,255,.25));
}
.gm-empty-ic { font-size: 40px; color: var(--yq-gold, #c7a96b); line-height: 1; }
.gm-empty b { font-size: 15px; color: var(--dp-text, #18202a); }
.gm-empty p { max-width: 380px; font-size: 12.5px; line-height: 1.8; color: var(--dp-text3, #8a8f98); margin: 0; }

.gm-head {
  display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap;
  padding-bottom: 10px; border-bottom: 1px solid var(--dp-line, rgba(0,0,0,.08));
}
.gm-head-tx { flex: 1; min-width: 180px; display: flex; flex-direction: column; gap: 2px; }
.gm-head-tx b { font-size: 16px; color: var(--dp-text, #18202a); }
.gm-head-tx i { font-style: normal; font-size: 12px; color: var(--dp-text3, #8a8f98); }
.gm-head-ops { display: flex; align-items: center; gap: 8px; }
.gm-op {
  padding: 6px 14px; border-radius: 999px; font-size: 12.5px; cursor: pointer; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text2, #45505b); transition: all .18s;
}
.gm-op:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.gm-op.ghost { background: transparent; }
.gm-locktip {
  font-size: 11.5px; color: var(--dp-text3, #8a8f98); background: rgba(199,169,107,.14);
  padding: 5px 12px; border-radius: 999px;
}

/* ===== 第一步：选模式 ===== */
.gm-setup { display: flex; flex-direction: column; gap: 12px; max-width: 620px; }
.gm-setup-title { font-size: 13px; font-weight: 600; color: var(--dp-text2, #45505b); }
.gm-modecards { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
.gm-modecard {
  display: flex; flex-direction: column; gap: 4px; text-align: left; cursor: pointer;
  padding: 14px 16px; border-radius: 15px; font-family: inherit;
  border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  background: linear-gradient(160deg, rgba(255,255,255,.85), rgba(255,255,255,.55));
  transition: all .18s;
}
.gm-modecard:hover {
  border-color: var(--yq-gold, #c7a96b); transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(20,30,40,.09);
}
.gm-modecard b { font-size: 14px; color: var(--dp-text, #18202a); }
.gm-modecard i { font-style: normal; font-size: 11.5px; line-height: 1.6; color: var(--dp-text3, #8a8f98); }
.gm-size { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.gm-size-label { font-size: 12.5px; color: var(--dp-text2, #45505b); font-weight: 600; }
.gm-sizebtn {
  padding: 6px 14px; border-radius: 999px; cursor: pointer; font-family: inherit; font-size: 12.5px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: transparent; color: var(--dp-text2, #45505b);
  transition: all .18s;
}
.gm-sizebtn.on { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.gm-size-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.gm-resume {
  align-self: flex-start; display: flex; align-items: center; gap: 8px;
  padding: 9px 16px; border-radius: 999px; cursor: pointer; font-family: inherit; font-size: 12.5px;
  border: 1px dashed var(--yq-gold, #c7a96b); background: rgba(199,169,107,.08);
  color: var(--yq-gold, #c7a96b); font-weight: 600;
}
.gm-resume em { font-style: normal; font-weight: 400; opacity: .75; }

/* ===== 第二步：对局 ===== */
.gm-play { display: flex; flex-direction: column; align-items: center; width: 100%; }
.gm-root.is-big .gm-play { max-width: 1000px; margin: 0 auto; }

@media (max-width: 860px) {
  .gm-root { grid-template-columns: 1fr; gap: 12px; }
  .gm-rail {
    flex-direction: row; gap: 10px; overflow-x: auto; padding-bottom: 4px;
  }
  .gm-grp { flex-direction: row; align-items: center; gap: 6px; }
  .gm-grp-name { display: none; }
  .gm-item { width: auto; padding: 7px 12px; }
  .gm-item-tx i { display: none; }
  .gm-empty { min-height: 220px; }
}
</style>
