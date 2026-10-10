<template>
  <!-- 开局仪式（v2.46.42，夜星）：码牌 → 庄家掷骰 → 开门 → 三轮流牌 → 庄家跳牌。
       纯表现层：真实对局状态在父组件里早已就位，本组件只负责「演」一遍——
       任意点击立即跳过（skip → emit done），约 6.5 秒自然播完自动收场。 -->
  <div class="mjo" @click="skip">
    <div class="mjo-scene">
      <div class="mjo-table" :style="{ '--sz': '1' }">
        <div
          v-for="side in SIDES"
          :key="side"
          class="mjo-wall"
          :class="'mjo-wall-' + side"
        >
          <span
            v-for="s in 15"
            :key="s"
            class="mjo-cell"
            :class="cellCls(side, s - 1)"
            :style="cellStyle(side, s - 1)"
          ></span>
        </div>

        <!-- 掷骰（build/open 阶段不显示；dice 阶段滚动，open 阶段定格） -->
        <div v-if="stage === 'dice' || stage === 'open'" class="mjo-dice" aria-hidden="true">
          <svg
            v-for="(v, di) in dice"
            :key="di"
            class="mjo-die"
            :class="{ 'is-roll': stage === 'dice' }"
            :style="{ animationDelay: di * 0.12 + 's' }"
            viewBox="0 0 40 40"
          >
            <rect x="2.5" y="2.5" width="35" height="35" rx="8" fill="#f7f2e6" stroke="#8a6d3b" stroke-width="1.5" />
            <circle v-for="(p, pi) in PIPS[v]" :key="pi" :cx="20 + p[0] * 10.5" :cy="20 + p[1] * 10.5" r="3.2" fill="#3a2c14" />
          </svg>
        </div>
        <b v-if="stage === 'open'" class="mjo-total">{{ dice[0] }}+{{ dice[1] }}</b>

        <!-- 各家手牌行：流牌阶段逐轮长出 4 张牌背，跳牌阶段庄 +2 / 其余 +1 -->
        <div
          v-for="side in SIDES"
          :key="'h' + side"
          class="mjo-hand"
          :class="['mjo-hand-' + side, { 'is-dealer': side === info.dealerPos }]"
        >
          <i class="mjo-zhu" v-if="side === info.dealerPos">庄</i>
          <span
            v-for="n in handCount(side)"
            :key="n"
            class="mjo-htile"
            :class="{ 'is-jump': isJumpTile(side, n) }"
          ></span>
        </div>
      </div>
      <p class="mjo-cap">{{ caption }}</p>
      <em class="mjo-skip">点击任意处跳过</em>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { sfx } from '@/utils/games/sfx'
import { MJ_OPEN_SIDE_NAME } from '@/utils/games/mahjong.js'

const props = defineProps({
  dice: { type: Array, required: true },          // [d1, d2]
  info: { type: Object, required: true },         // 父组件 openingInfo（投影后的方位/环序）
})
const emit = defineEmits(['done'])

const SIDES = ['down', 'right', 'up', 'left']
const POS_IDX = { down: 0, right: 1, up: 2, left: 3 }
const POS_LABEL = { down: '你', right: '右家', up: '对家', left: '左家' }
// 骰面点位（-1/0/1 网格坐标）
const PIPS = {
  1: [[0, 0]],
  2: [[-1, -1], [1, 1]],
  3: [[-1, -1], [0, 0], [1, 1]],
  4: [[-1, -1], [1, -1], [-1, 1], [1, 1]],
  5: [[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]],
  6: [[-1, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [1, 1]],
}

/* 环序 → 屏幕格子反查：ringSlots[k] = {side, slot}，键 'side:slot' → 环内墩号 k */
const ringOf = {}
props.info.ringSlots.forEach((r, k) => { ringOf[`${r.side}:${r.slot}`] = k })

/* 开门边相对庄的方位名（本门/下家/对家/上家）：屏幕方位差 = 座位相对差 */
const openRelName = computed(() => {
  const rel = (POS_IDX[props.info.openSide] - POS_IDX[props.info.dealerPos] + 4) % 4
  return MJ_OPEN_SIDE_NAME[rel]
})
const dealerLabel = computed(() => POS_LABEL[props.info.dealerPos])

const stage = ref('build')        // build → dice → open → deal → jump → done
const round = ref(0)              // deal 阶段已完成的轮数 0..3
let timers = []
function later(fn, ms) { timers.push(setTimeout(fn, ms)) }
function clearTimers() { timers.forEach(clearTimeout); timers = [] }

onMounted(() => {
  later(() => { stage.value = 'dice'; sfx.dice() }, 1500)
  later(() => { stage.value = 'open' }, 2600)
  later(() => { stage.value = 'deal'; round.value = 0; sfx.deal() }, 3800)
  later(() => { round.value = 1; sfx.deal() }, 4700)
  later(() => { round.value = 2; sfx.deal() }, 5600)
  later(() => { stage.value = 'jump'; sfx.deal() }, 6500)
  later(finish, 7600)
})
onUnmounted(clearTimers)
function finish() { clearTimers(); emit('done') }
function skip() { finish() }

const CAPTIONS = {
  build: '码牌 · 四方各十五墩',
  dice: () => `${dealerLabel.value}掷骰…`,
  open: () => `掷出 ${props.dice[0]}+${props.dice[1]}=${props.dice[0] + props.dice[1]} · 自${openRelName.value}第${Math.min(props.dice[0], props.dice[1]) + 1}墩开牌`,
  deal: () => `流牌 · 第 ${round.value + 1} 轮 · 每家两墩 4 张`,
  jump: '庄家跳牌 · 其余各家补一张',
}
const caption = computed(() => {
  const c = CAPTIONS[stage.value]
  return typeof c === 'function' ? c() : (c || '')
})

/* 某边手牌张数：流牌阶段每轮 +4；跳牌阶段庄 +2、其余 +1 */
function handCount(side) {
  if (stage.value === 'build' || stage.value === 'dice' || stage.value === 'open') return 0
  if (stage.value === 'deal') return round.value * 4
  const base = 12
  return side === props.info.dealerPos ? base + 2 : base + 1
}
/* 跳牌那张（第 14 张）鎏金一下：庄家的第 13、14 张 */
function isJumpTile(side, n) {
  return stage.value === 'jump' && side === props.info.dealerPos && n >= 13
}

/* 墩格状态：full / half / gone / open（开门墩鎏金标记） */
function cellState(side, slot) {
  const k = ringOf[`${side}:${slot}`]
  if (stage.value === 'build' || stage.value === 'dice') return 'full'
  if (stage.value === 'open') {
    return (side === props.info.openSide && slot === props.info.openSlot) ? 'open' : 'full'
  }
  if (stage.value === 'deal') {
    const u = round.value * 16
    if (u >= 2 * k + 2) return 'gone'
    if (u === 2 * k + 1) return 'half'
    return 'full'
  }
  return k < 24 ? 'gone' : (k < 29 ? 'half' : 'full')   // jump/done：跳牌零头
}
function cellCls(side, slot) {
  const st = cellState(side, slot)
  return { 'is-gone': st === 'gone', 'is-half': st === 'half', 'is-open': st === 'open' }
}
function cellStyle(side, slot) {
  if (stage.value !== 'build') return null
  const k = ringOf[`${side}:${slot}`] ?? 0
  return { '--d': (k * 20) + 'ms' }   // 码牌波次：从环原点顺时针铺开
}
</script>

<style scoped>
.mjo {
  position: absolute; inset: 0; z-index: 90;
  display: flex; align-items: center; justify-content: center;
  background: rgba(5, 9, 7, .78);
  -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px);
  cursor: pointer;
  animation: mjo-in .28s ease both;
}
@keyframes mjo-in { from { opacity: 0; } }
.mjo-scene { display: flex; flex-direction: column; align-items: center; gap: 10px; }
.mjo-table {
  position: relative;
  width: min(78vw, calc((100vh - 160px) * 1.35), 520px);
  aspect-ratio: 1.5 / 1;
  border-radius: 18px;
  background: rgba(16, 46, 34, .55);
  box-shadow: inset 0 0 0 1px rgba(222, 186, 106, .22);
}
/* ---- 四方牌墙 ---- */
.mjo-wall { position: absolute; display: flex; gap: 1px; }
.mjo-wall-up   { top: 4px; left: 50%; transform: translateX(-50%); }
.mjo-wall-down { bottom: 4px; left: 50%; transform: translateX(-50%); }
.mjo-wall-left   { left: 4px; top: 50%; transform: translateY(-50%) ; flex-direction: column; }
.mjo-wall-right  { right: 4px; top: 50%; transform: translateY(-50%); flex-direction: column; }
.mjo-cell {
  width: 11px; height: 15px; border-radius: 2.5px;
  background: linear-gradient(180deg, #ead9b8, #c8b48c);
  box-shadow: inset 0 0 0 1px rgba(58, 44, 20, .35);
  opacity: 1; transition: opacity .3s ease, box-shadow .3s ease, transform .3s ease;
  animation: mjo-cell-in .3s ease both;
  animation-delay: var(--d, 0ms);
}
@keyframes mjo-cell-in { from { opacity: 0; transform: translateY(-6px); } }
.mjo-wall-left .mjo-cell, .mjo-wall-right .mjo-cell { width: 15px; height: 11px; }
.mjo-cell.is-half { opacity: .5; }
.mjo-cell.is-gone { opacity: 0; transform: scale(.6); }
.mjo-cell.is-open {
  box-shadow: 0 0 0 2px rgba(222, 186, 106, .95), 0 0 12px rgba(222, 186, 106, .55);
  transform: scale(1.15);
}
/* ---- 骰子 ---- */
.mjo-dice {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  display: flex; gap: 10px; z-index: 5;
}
.mjo-die { width: 44px; height: 44px; filter: drop-shadow(0 4px 8px rgba(0, 0, 0, .5)); }
.mjo-die.is-roll { animation: mjo-roll .8s cubic-bezier(.3, 1.3, .4, 1) both; }
@keyframes mjo-roll {
  0% { transform: rotate(0deg) scale(.6); }
  55% { transform: rotate(320deg) scale(1.15); }
  75% { transform: rotate(350deg) scale(.96); }
  100% { transform: rotate(360deg) scale(1); }
}
@media (prefers-reduced-motion: reduce) { .mjo-die.is-roll { animation: none; } }
.mjo-total {
  position: absolute; left: 50%; top: 26%; transform: translateX(-50%);
  padding: 4px 16px; border-radius: 999px;
  font-size: 20px; font-weight: 700; color: #2a1d05; letter-spacing: .1em;
  background: linear-gradient(180deg, #f4dc9c, #d9b65f);
  box-shadow: 0 6px 16px -6px rgba(0, 0, 0, .8);
}
/* ---- 手牌行 ---- */
.mjo-hand {
  position: absolute; display: flex; gap: 2px; align-items: center;
  min-height: 20px;
}
/* 手牌行贴墙内侧：墙占边 4~19px，手牌从 24px 起，避免与牌墙重叠 */
.mjo-hand-down  { bottom: 24px; left: 50%; transform: translateX(-50%); }
.mjo-hand-up    { top: 24px; left: 50%; transform: translateX(-50%); }
.mjo-hand-left  { left: 24px; top: 50%; transform: translateY(-50%) ; flex-direction: column; }
.mjo-hand-right { right: 24px; top: 50%; transform: translateY(-50%); flex-direction: column; }
.mjo-htile {
  width: 13px; height: 18px; border-radius: 2.5px;
  background: linear-gradient(180deg, #2f4a3e, #1d332b);
  box-shadow: inset 0 0 0 1px rgba(222, 186, 106, .3);
  animation: mjo-fly .35s ease both;
}
.mjo-wall-left ~ .mjo-hand .mjo-htile, .mjo-hand-left .mjo-htile, .mjo-hand-right .mjo-htile {
  width: 18px; height: 13px;
}
.mjo-htile.is-jump {
  background: linear-gradient(180deg, #f4dc9c, #d9b65f);
  box-shadow: 0 0 10px rgba(222, 186, 106, .6);
}
@keyframes mjo-fly { from { opacity: 0; transform: translateY(-10px) scale(.8); } }
.mjo-zhu {
  flex: none; width: 16px; height: 16px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 10px; font-style: normal; font-weight: 700; color: #2a1d05;
  background: linear-gradient(180deg, #f4dc9c, #d9b65f);
  margin-right: 4px;
}
.mjo-hand-up .mjo-zhu, .mjo-hand-left .mjo-zhu { margin-right: 0; margin-left: 4px; order: 2; }
/* ---- 文案 ---- */
.mjo-cap {
  margin: 0; min-height: 22px;
  font-size: 15px; font-weight: 600; letter-spacing: .06em;
  color: #ead9b8;
}
.mjo-skip { font-size: 11px; font-style: normal; color: rgba(234, 217, 184, .45); }
@media (prefers-reduced-motion: reduce) {
  .mjo { animation: none; }
  .mjo-cell { animation: none; }
  .mjo-htile { animation: none; }
}
</style>
