<template>
  <div class="g3d-root" :class="{ 'is-guandan': mode === 'guandan' }">
    <!-- 顶栏：标题 + 模式切换 + 操作 -->
    <header class="g3d-bar">
      <div class="g3d-title">
        <span class="g3d-logo">3D</span>
        <div class="g3d-tx">
          <b>3D 棋牌</b>
          <i>腾讯棋牌风 · 真 3D 透视牌桌</i>
        </div>
      </div>

      <div class="g3d-modes">
        <button class="g3d-mode" :class="{ on: mode === 'mahjong' }" @click="switchMode('mahjong')">麻将</button>
        <button class="g3d-mode" :class="{ on: mode === 'guandan' }" @click="switchMode('guandan')">掼蛋</button>
      </div>

      <div class="g3d-ops">
        <button class="g3d-op" @click="deal">{{ dealt ? '重新发牌' : '发牌' }}</button>
        <button class="g3d-op" :class="{ on: auto }" @click="toggleAuto">{{ auto ? '停止出牌' : '自动出牌' }}</button>
      </div>
    </header>

    <!-- 3D 舞台（固定正视角度，纯透视立体，无旋转交互） -->
    <div class="g3d-stage">
      <div class="g3d-world" :style="{ transform: worldTF }">
        <!-- 牌桌（真实 3D 板：6 面挤出，看得见厚度与边缘） -->
        <div class="gt3-table" :style="boxVars(660, 660, 30)">
          <div class="gt3-face gt3-top">
            <div class="gt3-felt">
              <div class="gt3-woven"></div>
              <div class="gt3-vignette"></div>
              <!-- 中央东南西北罗盘 -->
              <div class="gt3-compass">
                <span class="cw cw-n">北</span>
                <span class="cw cw-e">东</span>
                <span class="cw cw-s">南</span>
                <span class="cw cw-w">西</span>
                <span class="cw-core">中</span>
              </div>
            </div>
          </div>
          <div class="gt3-face gt3-bottom"></div>
          <div class="gt3-face gt3-left"></div>
          <div class="gt3-face gt3-right"></div>
          <div class="gt3-face gt3-front"></div>
          <div class="gt3-face gt3-back"></div>
        </div>

        <!-- 座位铭牌（billboard 浮动卡：分数作头像角标，窄卡不压牌墙） -->
        <div
          v-for="s in seats"
          :key="s.key"
          class="gt3-seat"
          :style="seatTF(s)"
        >
          <div class="gt3-ava" :style="{ background: s.color }">
            {{ s.face }}
            <i class="gt3-score" :class="{ 'is-you': s.key === 'you' }">{{ scores[s.key] }}</i>
          </div>
          <div class="gt3-meta">
            <b>{{ s.name }}</b>
            <i :class="{ turn: turn === s.key }">{{ turn === s.key ? '出牌中…' : '准备' }}</i>
          </div>
        </div>

        <!-- ===== 麻将：三面立体牌墙 + 手牌 ===== -->
        <template v-if="mode === 'mahjong'">
          <div
            v-for="(t, i) in walls.N"
            :key="'n'+t.id"
            class="pc3d mj-wall"
            :style="pieceBox(46, 60, 16, wallTF('N', i, walls.N.length), i)"
          >
            <div class="pc-face pc-front mj-back"></div>
            <div class="pc-face pc-back mj-back"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
          <div
            v-for="(t, i) in walls.W"
            :key="'w'+t.id"
            class="pc3d mj-wall"
            :style="pieceBox(46, 60, 16, wallTF('W', i, walls.W.length), i)"
          >
            <div class="pc-face pc-front mj-back"></div>
            <div class="pc-face pc-back mj-back"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
          <div
            v-for="(t, i) in walls.E"
            :key="'e'+t.id"
            class="pc3d mj-wall"
            :style="pieceBox(46, 60, 16, wallTF('E', i, walls.E.length), i)"
          >
            <div class="pc-face pc-front mj-back"></div>
            <div class="pc-face pc-back mj-back"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>

          <!-- 玩家手牌：13 张，真矢量牌面 -->
          <div
            v-for="(t, i) in hand"
            :key="t.id"
            class="pc3d mj-hand"
            :class="{ fresh: freshIds.has(t.id) }"
            :style="pieceBox(46, 62, 16, freshIds.has(t.id) ? 'translate(-50%,-50%) translate3d(0px,-258px,46px) rotateX(-90deg)' : handTF(i, hand.length, true), i, true, freshIds.has(t.id))"
            @click="playMj(i)"
          >
            <div class="pc-face pc-front mj-front"><MahjongTileFace :suit="t.suit" :rank="t.rank" /></div>
            <div class="pc-face pc-back mj-ivory"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>

          <!-- 中央出牌区 -->
          <div
            v-for="(p, i) in mCenter"
            :key="'mc'+p.id"
            class="pc3d mj-hand mj-center"
            :style="pieceBox(46, 62, 20, centerTF(i), i, false)"
          >
            <div class="pc-face pc-front mj-front"><MahjongTileFace :suit="p.suit" :rank="p.rank" /></div>
            <div class="pc-face pc-back mj-ivory"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
        </template>

        <!-- ===== 掼蛋：三面手牌背面 + 玩家手牌 ===== -->
        <template v-else>
          <div
            v-for="c in ['N','W','E']"
            :key="'opp'+c"
          >
            <div
              v-for="k in 5"
              :key="c+k"
              class="pc3d gd-back"
              :style="pieceBox(46, 64, 12, oppTF(c, k - 1, 5), k - 1)"
            >
              <div class="pc-face pc-front card-back"></div>
              <div class="pc-face pc-back card-back"></div>
              <div class="pc-face pc-top mj-ivory"></div>
              <div class="pc-face pc-bottom mj-ivory"></div>
              <div class="pc-face pc-left mj-edge"></div>
              <div class="pc-face pc-right mj-edge"></div>
            </div>
          </div>

          <!-- 玩家手牌：13 张 3D 扑克牌 -->
          <div
            v-for="(t, i) in gHand"
            :key="t.id"
            class="pc3d gd-hand"
            :class="{ fresh: freshIds.has(t.id) }"
            :style="pieceBox(46, 64, 11, freshIds.has(t.id) ? 'translate(-50%,-50%) translate3d(0px,-258px,21px)' : handTF(i, gHand.length, false), i, true, freshIds.has(t.id))"
            @click="playGd(i)"
          >
            <div class="pc-face pc-front card-front" :class="t.red ? 'red' : 'blk'">
              <span class="cf-rank">{{ t.rank }}</span>
              <span class="cf-suit">{{ t.suitGlyph }}</span>
            </div>
            <div class="pc-face pc-back card-back"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>

          <!-- 中央出牌区 -->
          <div
            v-for="(p, i) in gCenter"
            :key="'gc'+p.id"
            class="pc3d gd-hand mj-center"
            :style="pieceBox(46, 64, 11, centerTF(i), i, false)"
          >
            <div class="pc-face pc-front card-front" :class="p.red ? 'red' : 'blk'">
              <span class="cf-rank">{{ p.rank }}</span>
              <span class="cf-suit">{{ p.suitGlyph }}</span>
            </div>
            <div class="pc-face pc-back card-back"></div>
            <div class="pc-face pc-top mj-ivory"></div>
            <div class="pc-face pc-bottom mj-ivory"></div>
            <div class="pc-face pc-left mj-edge"></div>
            <div class="pc-face pc-right mj-edge"></div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import MahjongTileFace from '@/components/games/MahjongTileFace.vue'
import { useImmersive } from '@/composables/useImmersive'

/* ---------- v2.46.114：横屏沉浸态 ----------
 * 3D 棋牌是演示视图，横屏时 App 底部 Tab 栏（fixed z-index 1500）会压住手牌
 * （夜星截图复现）。进入横屏即 enterImmersive 让 App.vue 收起 Tab 栏，
 * 竖屏恢复。引用计数防重复 enter/漏 exit。 */
const { enterImmersive, exitImmersive } = useImmersive()
let immersiveOn = false
function syncImmersive() {
  const landscape = window.innerWidth > window.innerHeight
  if (landscape && !immersiveOn) { enterImmersive(); immersiveOn = true }
  else if (!landscape && immersiveOn) { exitImmersive(); immersiveOn = false }
}

/* ---------- 基础数据 ---------- */
const SUITS = ['wan', 'tiao', 'tong']
const ZI = [1, 2, 3, 4, 5, 6, 7]
const CARD_SUITS = [
  { k: 'spade', g: '♠', red: false },
  { k: 'heart', g: '♥', red: true },
  { k: 'diamond', g: '♦', red: true },
  { k: 'club', g: '♣', red: false },
]
const CARD_RANKS = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']

/* 排序次序：手牌自动整理用 */
const SUIT_ORDER = { wan: 0, tiao: 1, tong: 2, zi: 3 }
const CARD_ORDER = { spade: 0, club: 1, heart: 2, diamond: 3 }
const RANK_ORDER = { '3':0,'4':1,'5':2,'6':3,'7':4,'8':5,'9':6,'10':7,'J':8,'Q':9,'K':10,'A':11,'2':12 }
/* 正在飞入（摸牌）的牌 id，用于触发「上牌」动画 */
const freshIds = ref(new Set())

const rnd = (n) => Math.floor(Math.random() * n)
const pick = (a) => a[rnd(a.length)]
let uid = 0
const nextId = () => 'p' + (uid++)

const mode = ref('mahjong')
const dealt = ref(false)
const auto = ref(false)
const turn = ref('you')

/* 固定正视、微微前倾对着你：只要透视立体感，不做旋转/俯仰交互 */
const VIEW_RX = 66
const worldTF = `rotateX(${VIEW_RX}deg) scale3d(.94, .94, .94)`

/* 座位（billboard 浮动铭牌：lift 为悬浮高度，N/W/E 抬到牌墙顶以上避免遮挡） */
const seats = [
  { key: 'N', name: '上家', face: '🀄', color: 'linear-gradient(160deg,#3a7,#276)', pos: [0, -318], lift: 96 },
  { key: 'W', name: '左家', face: '🎴', color: 'linear-gradient(160deg,#a76,#743)', pos: [-392, 0], lift: 80 },
  { key: 'E', name: '右家', face: '🌟', color: 'linear-gradient(160deg,#67a,#345)', pos: [392, 0], lift: 80 },
  { key: 'you', name: '你', face: '🀆', color: 'linear-gradient(160deg,#e9c877,#a9812f)', pos: [0, 398], lift: 24 },
]
const scores = reactive({ you: 1280, N: 980, W: 1510, E: 760 })

/* 麻将 */
const hand = ref([])
const walls = reactive({ N: [], W: [], E: [] })
const mCenter = ref([])

/* 掼蛋 */
const gHand = ref([])
const gCenter = ref([])

/* ---------- 构建牌堆 ---------- */
function buildMjHand() {
  const a = []
  for (let i = 0; i < 13; i++) {
    const s = pick(SUITS)
    a.push({ id: nextId(), suit: s, rank: s === 'zi' ? pick(ZI) : 1 + rnd(9) })
  }
  return a
}
function buildWalls() {
  const mk = () => Array.from({ length: 12 }, () => ({ id: nextId() }))
  return { N: mk(), W: mk(), E: mk() }
}
function buildGdHand() {
  // 54 张去大小王之外的简化牌堆，随机抽 13 张给玩家
  const deck = []
  for (const s of CARD_SUITS) for (const r of CARD_RANKS) deck.push({ suit: s.k, suitGlyph: s.g, red: s.red, rank: r })
  for (let i = deck.length - 1; i > 0; i--) { const j = rnd(i + 1);[deck[i], deck[j]] = [deck[j], deck[i]] }
  return deck.slice(0, 13).map((d) => ({ id: nextId(), ...d }))
}

function rebuild() {
  freshIds.value.clear()
  hand.value = buildMjHand()
  sortMj()
  const w = buildWalls(); walls.N = w.N; walls.W = w.W; walls.E = w.E
  mCenter.value = []
  gHand.value = buildGdHand()
  sortGd()
  gCenter.value = []
  scores.you = 1280; scores.N = 980; scores.W = 1510; scores.E = 760
  dealt.value = false
  requestAnimationFrame(() => requestAnimationFrame(() => { dealt.value = true }))
}

/* ---------- 3D 变换 ---------- */
const CENTER_TF = 'translate(-50%,-50%) translate3d(0px,0px,240px) scale(0.16)'

function boxVars(w, h, t) {
  return { '--w': w + 'px', '--h': h + 'px', '--t': t + 'px' }
}
// 牌桌 6 面挤出（face 由模板内 .gt3-* 类直接定义，无需 JS）
// 通用 3D 块样式：传入 w/h/t、最终变换、错峰延迟；未发牌时收拢到中央；instant=true 用于摸牌飞入（无错峰延迟）
function pieceBox(w, h, t, finalTF, delayIdx, clickable, instant) {
  const tf = dealt.value ? finalTF : CENTER_TF
  return {
    ...boxVars(w, h, t),
    transform: tf,
    transitionDelay: instant ? '0ms' : (delayIdx * 28) + 'ms',
    cursor: clickable ? 'pointer' : 'default',
  }
}

function wallTF(side, i, n) {
  // 12 张/面、step=45（牌宽46，1px 搭接）：两端牌边正好到 ±270.5，与墙线 ±270 齐平，四角闭合
  const step = 45
  const off = (i - (n - 1) / 2) * step
  let x = 0, y = 0, rotZ = 0
  if (side === 'N') { x = off; y = -270; rotZ = 180 }
  else if (side === 'W') { x = -270; y = off; rotZ = 90 }
  else { x = 270; y = off; rotZ = -90 }
  // 桌面顶 z=15；立牌高 60 → 中心 15+30=45，牌底恰好落在桌面
  return `translate(-50%,-50%) translate3d(${x}px,${y}px,45px) rotateZ(${rotZ}deg) rotateX(-90deg)`
}
function handTF(i, n, stand) {
  // 齐整：无扇形、无高低差，纯直排
  const step = 44
  const off = (i - (n - 1) / 2) * step
  if (stand) {
    // 麻将手牌：立起来、牌面朝玩家（与牌墙同款立姿，桌面顶 z=15 + 半牌高 31）
    return `translate(-50%,-50%) translate3d(${off}px,324px,46px) rotateX(-90deg)`
  }
  // 掼蛋手牌：平贴桌面（桌面顶 15 + 半厚 5.5）
  return `translate(-50%,-50%) translate3d(${off}px,322px,21px)`
}
function oppTF(side, k, n) {
  const step = 50
  const off = (k - (n - 1) / 2) * step
  let x = 0, y = 0
  if (side === 'N') { x = off; y = -300 }
  else if (side === 'W') { x = -300; y = off }
  else { x = 300; y = off }
  return `translate(-50%,-50%) translate3d(${x}px,${y}px,21px)`
}
function centerTF(i, lift = 40) {
  const a = i * 0.7
  const x = Math.cos(a) * (i * 6)
  const y = Math.sin(a) * (i * 6)
  // 打出去的牌：立起 52° 朝向你，牌面正对镜头好认（中心抬到 40 让牌底边贴桌面）
  return `translate(-50%,-50%) translate3d(${x}px,${y}px,${lift}px) rotateX(-52deg)`
}
function seatTF(s) {
  // 铭牌 billboard：rotateX(-VIEW_RX) 抵消世界倾斜，始终竖立正对镜头、悬浮桌沿上方（不再平贴桌面被透视压扁）
  return { transform: `translate(-50%,-50%) translate3d(${s.pos[0]}px,${s.pos[1]}px,${s.lift}px) rotateX(-${VIEW_RX}deg)` }
}

/* ---------- 出牌模拟 ---------- */
let autoTimer = null
function sortMj() {
  hand.value.sort((a, b) => SUIT_ORDER[a.suit] - SUIT_ORDER[b.suit] || a.rank - b.rank)
}
function sortGd() {
  gHand.value.sort((a, b) => CARD_ORDER[a.suit] - CARD_ORDER[b.suit] || RANK_ORDER[a.rank] - RANK_ORDER[b.rank])
}
function bump(scoreKey) {
  scores[scoreKey] = (scores[scoreKey] || 0) + 8
}
/* 摸一张新牌：插入后立即整理，并标记为「飞入」，触发从牌墙滑入的上牌动画 */
function drawFreshMj() {
  const s = pick(SUITS)
  const t = { id: nextId(), suit: s, rank: s === 'zi' ? pick(ZI) : 1 + rnd(9), fresh: true }
  hand.value.push(t); sortMj(); freshIds.value.add(t.id)
  requestAnimationFrame(() => requestAnimationFrame(() => freshIds.value.delete(t.id)))
}
function drawFreshGd() {
  const s = pick(CARD_SUITS)
  const t = { id: nextId(), suit: s.k, suitGlyph: s.g, red: s.red, rank: pick(CARD_RANKS), fresh: true }
  gHand.value.push(t); sortGd(); freshIds.value.add(t.id)
  requestAnimationFrame(() => requestAnimationFrame(() => freshIds.value.delete(t.id)))
}
function playMj(i) {
  if (!dealt.value) return
  const t = hand.value.splice(i, 1)[0]
  if (!t) return
  turn.value = 'you'
  bump('you')
  mCenter.value.push({ id: nextId(), suit: t.suit, rank: t.rank })
  sortMj()
  drawFreshMj() // 出牌后摸牌 → 短暂上牌过程
  if (auto.value) scheduleAi('mj')
}
function aiPlayMj() {
  const side = pick(['N', 'W', 'E'])
  turn.value = side
  bump(side)
  mCenter.value.push({ id: nextId(), suit: pick(SUITS), rank: pick(SUITS) === 'zi' ? pick(ZI) : 1 + rnd(9) })
  if (hand.value.length === 0) rebuild()
}
function playGd(i) {
  if (!dealt.value) return
  const t = gHand.value.splice(i, 1)[0]
  if (!t) return
  turn.value = 'you'
  bump('you')
  gCenter.value.push({ id: nextId(), suit: t.suit, suitGlyph: t.suitGlyph, red: t.red, rank: t.rank })
  sortGd()
  drawFreshGd()
  if (auto.value) scheduleAi('gd')
}
function aiPlayGd() {
  const side = pick(['N', 'W', 'E'])
  turn.value = side
  bump(side)
  const s = pick(CARD_SUITS)
  gCenter.value.push({ id: nextId(), suit: s.k, suitGlyph: s.g, red: s.red, rank: pick(CARD_RANKS) })
  if (gHand.value.length === 0) rebuild()
}
function scheduleAi(kind) {
  clearTimeout(autoTimer)
  autoTimer = setTimeout(() => { kind === 'mj' ? aiPlayMj() : aiPlayGd() }, 950)
}
function toggleAuto() {
  auto.value = !auto.value
  if (auto.value) { mode.value === 'mahjong' ? (hand.value.length && scheduleAi('mj')) : (gHand.value.length && scheduleAi('gd')) }
  else clearTimeout(autoTimer)
}

/* ---------- 模式切换 / 发牌 ---------- */
function switchMode(m) {
  if (m === mode.value) return
  mode.value = m
  clearTimeout(autoTimer)
  auto.value = false
  rebuild()
}
function deal() { rebuild() }

onMounted(() => {
  rebuild()
  syncImmersive()
  window.addEventListener('resize', syncImmersive)
  window.addEventListener('orientationchange', syncImmersive)
})
onBeforeUnmount(() => {
  clearTimeout(autoTimer)
  window.removeEventListener('resize', syncImmersive)
  window.removeEventListener('orientationchange', syncImmersive)
  if (immersiveOn) { exitImmersive(); immersiveOn = false }
})
</script>

<style scoped>
.g3d-root {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(120% 90% at 50% -10%, rgba(120, 200, 170, .10), transparent 58%),
    radial-gradient(140% 120% at 50% 120%, rgba(0, 0, 0, .55), transparent 60%),
    linear-gradient(160deg, #0a1612 0%, #07100d 55%, #04090a 100%);
  color: #eef3f0;
  user-select: none;
  -webkit-user-select: none;
}

/* 顶栏 */
.g3d-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 14px 22px;
  background: linear-gradient(180deg, rgba(6, 14, 11, .82), rgba(6, 14, 11, 0));
  backdrop-filter: blur(6px);
}
.g3d-title { display: flex; align-items: center; gap: 12px; }
.g3d-logo {
  font-weight: 800; font-size: 20px; letter-spacing: 1px;
  padding: 4px 10px; border-radius: 10px;
  background: linear-gradient(160deg, #e9c877, #a9812f);
  color: #2a1d05; box-shadow: 0 4px 14px -4px rgba(233, 200, 119, .6);
}
.g3d-tx { display: flex; flex-direction: column; line-height: 1.15; }
.g3d-tx b { font-size: 16px; }
.g3d-tx i { font-size: 11.5px; color: #9fc4b6; font-style: normal; }

.g3d-modes { display: flex; gap: 6px; padding: 4px; border-radius: 12px;
  background: rgba(255, 255, 255, .06); border: 1px solid rgba(255, 255, 255, .1); }
.g3d-mode {
  border: 0; padding: 7px 18px; border-radius: 9px; cursor: pointer;
  font-size: 14px; color: #cfe2da; background: transparent; transition: .2s;
}
.g3d-mode.on { background: linear-gradient(160deg, #e9c877, #c9a44e); color: #2a1d05; font-weight: 700; }

.g3d-ops { margin-left: auto; display: flex; gap: 8px; }
.g3d-op {
  border: 1px solid rgba(233, 200, 119, .5);
  background: rgba(233, 200, 119, .12);
  color: #e9c877; padding: 8px 16px; border-radius: 10px;
  font-size: 13.5px; cursor: pointer; transition: .2s;
}
.g3d-op:hover { background: rgba(233, 200, 119, .22); }
.g3d-op.on { background: linear-gradient(160deg, #e9c877, #c9a44e); color: #2a1d05; font-weight: 700; }
.g3d-op.ghost { border-color: rgba(255, 255, 255, .2); background: rgba(255, 255, 255, .05); color: #cfe2da; }

/* 舞台 / 世界 */
.g3d-stage {
  position: absolute; inset: 0;
  perspective: 1500px;
  perspective-origin: 50% 42%;
  overflow: hidden;
}
.g3d-world {
  position: absolute; left: 50%; top: 52%;
  width: 0; height: 0;
  transform-style: preserve-3d;
}

/* 牌桌 3D 板 */
.gt3-table { position: absolute; left: 0; top: 0; transform-style: preserve-3d; }
.gt3-face { position: absolute; left: 50%; top: 50%; }
.gt3-top {
  width: var(--w); height: var(--h);
  transform: translate(-50%, -50%) translateZ(calc(var(--t) / 2));
  border-radius: 26px;
}
.gt3-bottom {
  width: var(--w); height: var(--h);
  transform: translate(-50%, -50%) rotateX(180deg) translateZ(calc(var(--t) / 2));
  border-radius: 26px; background: #06231b;
}
.gt3-left {
  width: var(--t); height: var(--h);
  transform: translate(-50%, -50%) rotateY(-90deg) translateZ(calc(var(--w) / 2));
  background: linear-gradient(180deg, #164433, #061a12);
}
.gt3-right {
  width: var(--t); height: var(--h);
  transform: translate(-50%, -50%) rotateY(90deg) translateZ(calc(var(--w) / 2));
  background: linear-gradient(180deg, #164433, #061a12);
}
.gt3-front {
  width: var(--w); height: var(--t);
  transform: translate(-50%, -50%) rotateX(90deg) translateZ(calc(var(--h) / 2));
  background: linear-gradient(90deg, #164433, #061a12);
}
.gt3-back {
  width: var(--w); height: var(--t);
  transform: translate(-50%, -50%) rotateX(-90deg) translateZ(calc(var(--h) / 2));
  background: linear-gradient(90deg, #061a12, #164433);
}
.gt3-felt {
  position: absolute; inset: 0; border-radius: 26px; overflow: hidden;
  background:
    radial-gradient(120% 90% at 50% 40%, rgba(255, 255, 255, .07), transparent 60%),
    linear-gradient(160deg, #1d5c46, #0f3a2c 58%, #082019);
  box-shadow:
    inset 0 0 0 3px rgba(233, 200, 119, .38),
    inset 0 0 0 12px rgba(233, 200, 119, .1),
    inset 0 0 40px rgba(0, 0, 0, .5);
}
.gt3-woven {
  position: absolute; inset: 0; opacity: .5;
  background:
    repeating-linear-gradient(45deg, rgba(255, 255, 255, .025) 0 2px, transparent 2px 4px),
    repeating-linear-gradient(-45deg, rgba(0, 0, 0, .05) 0 2px, transparent 2px 4px);
}
.gt3-vignette { position: absolute; inset: 0; background: radial-gradient(115% 78% at 50% 42%, transparent 52%, rgba(0, 0, 0, .42)); }

/* 中央罗盘 */
.gt3-compass {
  position: absolute; left: 50%; top: 50%; width: 150px; height: 150px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 2px solid rgba(233, 200, 119, .5);
  background: radial-gradient(circle, rgba(233, 200, 119, .12), rgba(0, 0, 0, .2) 70%);
  box-shadow: 0 0 22px -4px rgba(233, 200, 119, .4);
}
.gt3-compass .cw { position: absolute; font-size: 17px; font-weight: 700; color: #e9c877; }
.cw-n { top: 8px; left: 50%; transform: translateX(-50%); }
.cw-s { bottom: 8px; left: 50%; transform: translateX(-50%); }
.cw-e { right: 10px; top: 50%; transform: translateY(-50%); }
.cw-w { left: 10px; top: 50%; transform: translateY(-50%); }
.cw-core {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  font-size: 22px; font-weight: 800; color: #fff;
  text-shadow: 0 0 8px rgba(233, 200, 119, .7);
}

/* 座位铭牌 */
.gt3-seat {
  position: absolute; left: 0; top: 0;
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px 7px 7px; border-radius: 14px;
  background: rgba(8, 20, 16, .86);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, .16);
  box-shadow: 0 12px 26px -12px rgba(0, 0, 0, .85);
  white-space: nowrap;
}
.gt3-ava {
  position: relative;
  width: 38px; height: 38px; border-radius: 50%;
  display: grid; place-items: center; font-size: 18px;
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, .25);
}
.gt3-score {
  position: absolute; right: -8px; bottom: -8px;
  font-size: 11px; font-weight: 800; font-style: normal;
  font-variant-numeric: tabular-nums; line-height: 1;
  color: #2a1d05; padding: 3px 7px; border-radius: 9px;
  background: linear-gradient(160deg, #f2d89a, #c9a44e);
  box-shadow: 0 2px 7px rgba(0, 0, 0, .55);
  white-space: nowrap;
}
.gt3-score.is-you { background: linear-gradient(160deg, #fff3d6, #e9c877); }
.gt3-meta { display: flex; flex-direction: column; line-height: 1.1; }
.gt3-meta b { font-size: 13px; }
.gt3-meta i { font-size: 10.5px; color: #9fc4b6; font-style: normal; }
.gt3-meta i.turn { color: #e9c877; }

/* 通用 3D 块 */
.pc3d {
  position: absolute; left: 0; top: 0;
  width: var(--w); height: var(--h);
  transform-style: preserve-3d;
  transition: transform .7s cubic-bezier(.22, .9, .28, 1), opacity .5s;
}
.pc3d.mj-hand, .pc3d.gd-hand { transition: transform .7s cubic-bezier(.22, .9, .28, 1), opacity .5s, box-shadow .2s; }
.pc3d.mj-hand:hover, .pc3d.gd-hand:hover { filter: brightness(1.08); }
/* 摸牌飞入：从牌墙滑入，无错峰延迟、稍快 */
.pc3d.fresh { transition: transform .5s cubic-bezier(.22, .7, .25, 1), opacity .3s; }
.pc3d.mj-center, .pc3d.mj-center { animation: pop .42s ease both; }
@keyframes pop { from { transform: translate(-50%, -50%) translate3d(0, 0, 220px) scale(.3); opacity: 0; } }
.pc-face { position: absolute; left: 50%; top: 50%; backface-visibility: hidden; }
.pc-front { width: var(--w); height: var(--h); transform: translate(-50%, -50%) translateZ(calc(var(--t) / 2)); }
.pc-back { width: var(--w); height: var(--h); transform: translate(-50%, -50%) rotateY(180deg) translateZ(calc(var(--t) / 2)); }
.pc-top { width: var(--w); height: var(--t); transform: translate(-50%, -50%) rotateX(90deg) translateZ(calc(var(--h) / 2)); }
.pc-bottom { width: var(--w); height: var(--t); transform: translate(-50%, -50%) rotateX(-90deg) translateZ(calc(var(--h) / 2)); }
.pc-left { width: var(--t); height: var(--h); transform: translate(-50%, -50%) rotateY(-90deg) translateZ(calc(var(--w) / 2)); }
.pc-right { width: var(--t); height: var(--h); transform: translate(-50%, -50%) rotateY(90deg) translateZ(calc(var(--w) / 2)); }

/* 麻将牌面（玉牌质感） */
.mj-front {
  border-radius: 5px; overflow: hidden;
  background: linear-gradient(175deg, #fdfbf4 0%, #f3efe2 62%, #ddd6c2 100%);
  box-shadow: inset 0 0 0 1px rgba(120, 100, 60, .25);
}
.mj-ivory {
  border-radius: 4px;
  background: linear-gradient(175deg, #f6f1e2 0%, #eae2cd 55%, #d6ccb1 100%);
  box-shadow: inset 0 0 0 1px rgba(140, 118, 78, .32);
}
.mj-edge { background: linear-gradient(90deg, #eee6d2, #d3c9ad); border-radius: 3px; }
.mj-back {
  border-radius: 5px;
  background:
    repeating-linear-gradient(45deg, rgba(255, 255, 255, .05) 0 6px, transparent 6px 12px),
    radial-gradient(circle at 50% 30%, rgba(255, 255, 255, .15), transparent 62%),
    linear-gradient(165deg, #2f8a74 0%, #1c6a57 55%, #11503f 100%);
  box-shadow: inset 0 0 0 2px rgba(233, 200, 119, .48), inset 0 0 14px rgba(0, 0, 0, .28);
}

/* 扑克牌 */
.card-front {
  border-radius: 6px; overflow: hidden;
  background: linear-gradient(180deg, #fffdf8, #f1ece0);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  box-shadow: inset 0 0 0 1px rgba(120, 100, 60, .2);
}
.card-front .cf-rank { font-size: 22px; font-weight: 800; line-height: 1; }
.card-front .cf-suit { font-size: 22px; line-height: 1; margin-top: 3px; }
.card-front.red { color: #d23b3b; }
.card-front.blk { color: #1c2733; }
.card-back {
  border-radius: 6px;
  background:
    repeating-linear-gradient(45deg, rgba(255, 255, 255, .12) 0 3px, transparent 3px 6px),
    linear-gradient(160deg, #b8342f, #7e1f1c);
  box-shadow: inset 0 0 0 2px rgba(233, 200, 119, .4);
}

/* 提示条已按夜星要求移除（v2.46.112） */
</style>
