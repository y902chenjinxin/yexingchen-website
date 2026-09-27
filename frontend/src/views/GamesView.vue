<template>
  <IslandInnerBase type="tool" title="摸鱼小游戏" subtitle="2048 · 贪吃蛇 · 扫雷 · 纯本地">
    <div class="games-tool">
      <div class="gm-tabs">
        <button v-for="g in gamelist" :key="g.key" class="gm-tab" :class="{ active: tab === g.key }" @click="switchTab(g.key)">{{ g.label }}</button>
      </div>

      <!-- 2048 -->
      <div v-if="tab === 'g2048'" class="gm-pane">
        <div class="gm-info">方向键 / 滑动合并方块 · <b>{{ s2048.score }}</b> 分
          <span class="gm-best">最高 {{ best2048 }}</span>
          <button class="gm-mini" @click="init2048">重开</button>
        </div>
        <div class="g2048" ref="g2048El" tabindex="0">
          <div v-for="(row, r) in s2048.grid" :key="r" class="row2048">
            <div v-for="(v, c) in row" :key="c" class="cell2048" :class="'v' + (v || 0)">{{ v || '' }}</div>
          </div>
          <div v-if="s2048.over" class="g2048-over">游戏结束 · {{ s2048.score }} 分
            <button class="gm-mini" @click.stop="init2048">再来</button>
          </div>
        </div>
        <div class="gm-hint">电脑端方向键直接可用 · 手机在棋盘上滑动</div>
      </div>

      <!-- 贪吃蛇 -->
      <div v-if="tab === 'snake'" class="gm-pane">
        <div class="gm-info">方向键转向 · <b>{{ snake.score }}</b> 分
          <span class="gm-best">最高 {{ bestSnake }}</span>
          <button class="gm-mini" @click="initSnake">重开</button>
        </div>
        <canvas ref="snakeEl" width="400" height="400" class="snake-cv" tabindex="0"></canvas>
        <div v-if="snake.over" class="gm-center-msg">撞到了 · {{ snake.score }} 分，按「重开」再来</div>
        <div class="gm-hint">电脑端方向键直接可用 · 手机点「重开」后滑动无效，建议电脑玩</div>
      </div>

      <!-- 扫雷 -->
      <div v-if="tab === 'mine'" class="gm-pane">
        <div class="gm-info">左键翻开 · 右键/旗子模式插旗 · 剩余雷 <b>{{ mine.flagsLeft }}</b>
          <button class="gm-mini" @click="initMine">重开</button>
        </div>
        <div class="mine-grid">
          <div
            v-for="cell in mine.cells"
            :key="cell.i"
            class="mine-cell"
            :class="{ revealed: cell.revealed, boom: cell.boom, flagged: cell.flagged }"
            @click="digCell(cell)"
            @contextmenu.prevent="flagCell(cell)"
          >{{ cellText(cell) }}</div>
        </div>
        <div class="gm-toggle">
          <label class="mine-flagmode"><input v-model="mine.flagMode" type="checkbox"> 旗子模式（手机用）</label>
        </div>
        <div v-if="mine.result" class="gm-center-msg">{{ mine.result }}</div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'

const gamelist = [
  { key: 'g2048', label: '2048' },
  { key: 'snake', label: '贪吃蛇' },
  { key: 'mine', label: '扫雷' },
]
const tab = ref('g2048')
function switchTab(k) {
  tab.value = k
  if (k === 'snake') nextTick(() => { initSnake(); snakeEl.value?.focus() })
}

/* ================= 本机最高分（C5） ================= */
const best2048 = ref(0)
const bestSnake = ref(0)
function loadBests() {
  best2048.value = Number(localStorage.getItem('g2048_best') || 0) || 0
  bestSnake.value = Number(localStorage.getItem('snake_best') || 0) || 0
}
function saveBest(key, score, refObj) {
  if (!score || score <= refObj.value) return
  refObj.value = score
  localStorage.setItem(key, String(score))
}

/* ================= 2048 ================= */
const g2048El = ref(null)
const s2048 = reactive({ grid: [], score: 0, over: false })

function init2048() {
  s2048.grid = Array.from({ length: 4 }, () => [0, 0, 0, 0])
  s2048.score = 0
  s2048.over = false
  spawn2048(); spawn2048()
}
function spawn2048() {
  const empty = []
  s2048.grid.forEach((row, r) => row.forEach((v, c) => { if (!v) empty.push([r, c]) }))
  if (!empty.length) return
  const [r, c] = empty[Math.floor(Math.random() * empty.length)]
  s2048.grid[r][c] = Math.random() < 0.9 ? 2 : 4
}
function slide(row) {
  const arr = row.filter(v => v)
  let gained = 0
  for (let i = 0; i < arr.length - 1; i++) {
    if (arr[i] === arr[i + 1]) { arr[i] *= 2; gained += arr[i]; arr.splice(i + 1, 1) }
  }
  while (arr.length < 4) arr.push(0)
  return { arr, gained }
}
function move2048(dir) {
  if (s2048.over) return
  const g = s2048.grid.map(r => [...r])
  let moved = false, gained = 0
  const rotate = (m) => m[0].map((_, i) => m.map(r => r[i]).reverse())  // 顺时针
  let work = g
  const rot = { left: 0, up: 1, right: 2, down: 3 }[dir]
  for (let i = 0; i < rot; i++) work = rotate(work)
  work = work.map(row => {
    const { arr, gained: gn } = slide(row)
    gained += gn
    if (arr.join() !== row.join()) moved = true
    return arr
  })
  let out = work
  for (let i = 0; i < (4 - rot) % 4; i++) out = rotate(out)
  if (!moved) return
  s2048.grid = out
  s2048.score += gained
  saveBest('g2048_best', s2048.score, best2048)
  spawn2048()
  // 结束判定：无空格且无可合并
  const flat = s2048.grid.flat()
  if (!flat.includes(0)) {
    let can = false
    for (let r = 0; r < 4; r++) for (let c = 0; c < 3; c++) {
      if (s2048.grid[r][c] === s2048.grid[r][c + 1] || s2048.grid[c][r] === s2048.grid[c + 1][r]) can = true
    }
    if (!can) s2048.over = true
  }
}
const onKey2048 = (e) => {
  const map = { ArrowLeft: 'left', ArrowUp: 'up', ArrowRight: 'right', ArrowDown: 'down' }
  if (map[e.key]) move2048(map[e.key])
}

/* ---------- 键盘统一入口（v2.40.18）----------
 * 以前 keydown 绑在各游戏元素上，得先「点一下棋盘」拿到焦点，电脑端直接按方向键毫无反应
 * （而且浏览器默认用它滚动页面）。改为窗口级监听：只要游戏页在显示就生效，
 * 并按当前 tab 分发；顺带 preventDefault 掉方向键的滚动行为。
 * 焦点在输入框里时不拦截（扫雷页有勾选框，别抢走键盘操作）。
 */
const ARROW_KEYS = ['ArrowLeft', 'ArrowUp', 'ArrowRight', 'ArrowDown']
function onWindowKey(e) {
  if (!ARROW_KEYS.includes(e.key)) return
  const t = e.target
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
  e.preventDefault()
  if (tab.value === 'g2048') onKey2048(e)
  else if (tab.value === 'snake') onKeySnake(e)
}
// 触摸滑动
let tStart = null
function bindTouch(el) {
  el.addEventListener('touchstart', e => { tStart = [e.touches[0].clientX, e.touches[0].clientY] }, { passive: true })
  el.addEventListener('touchend', e => {
    if (!tStart) return
    const dx = e.changedTouches[0].clientX - tStart[0], dy = e.changedTouches[0].clientY - tStart[1]
    if (Math.max(Math.abs(dx), Math.abs(dy)) > 24) {
      move2048(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up'))
    }
    tStart = null
  }, { passive: true })
}

/* ================= 贪吃蛇 ================= */
const snakeEl = ref(null)
const snake = reactive({ score: 0, over: false, dir: [1, 0], body: [], food: [0, 0], timer: 0 })

function initSnake() {
  clearInterval(snake.timer)
  snake.score = 0; snake.over = false; snake.dir = [1, 0]
  snake.body = [[8, 10], [7, 10], [6, 10]]
  placeFood()
  drawSnake()
  snake.timer = setInterval(stepSnake, 130)
}
function placeFood() {
  do { snake.food = [Math.floor(Math.random() * 20), Math.floor(Math.random() * 20)] }
  while (snake.body.some(([x, y]) => x === snake.food[0] && y === snake.food[1]))
}
function stepSnake() {
  if (snake.over) return
  const [dx, dy] = snake.dir
  const head = [(snake.body[0][0] + dx + 20) % 20, (snake.body[0][1] + dy + 20) % 20]
  if (snake.body.some(([x, y]) => x === head[0] && y === head[1])) { snake.over = true; clearInterval(snake.timer); drawSnake(); return }
  snake.body.unshift(head)
  if (head[0] === snake.food[0] && head[1] === snake.food[1]) { snake.score += 10; placeFood() }
  else snake.body.pop()
  saveBest('snake_best', snake.score, bestSnake)
  drawSnake()
}
function onKeySnake(e) {
  const map = { ArrowLeft: [-1, 0], ArrowUp: [0, -1], ArrowRight: [1, 0], ArrowDown: [0, 1] }
  const d = map[e.key]
  if (d && (d[0] !== -snake.dir[0] || d[1] !== -snake.dir[1])) snake.dir = d
}
function drawSnake() {
  const cv = snakeEl.value
  if (!cv) return
  const ctx = cv.getContext('2d')
  const S = 20
  ctx.fillStyle = 'rgba(0,0,0,.03)'; ctx.fillRect(0, 0, 400, 400)
  // 食物
  ctx.fillStyle = '#e5484d'
  ctx.beginPath(); ctx.arc(snake.food[0] * S + 10, snake.food[1] * S + 10, 7, 0, 7); ctx.fill()
  // 蛇
  snake.body.forEach(([x, y], i) => {
    ctx.fillStyle = i === 0 ? '#c7a96b' : `rgba(127,168,163,${Math.max(0.35, 1 - i / snake.body.length)})`
    ctx.fillRect(x * S + 1, y * S + 1, S - 2, S - 2)
  })
}

/* ================= 扫雷 ================= */
const SIZE = 10, MINES = 15
const mine = reactive({ cells: [], flagsLeft: MINES, flagMode: false, result: '' })

function initMine() {
  mine.cells = Array.from({ length: SIZE * SIZE }, (_, i) => ({
    i, x: i % SIZE, y: Math.floor(i / SIZE), mine: false, revealed: false, flagged: false, boom: false, n: 0,
  }))
  mine.flagsLeft = MINES; mine.result = ''
  let placed = 0
  while (placed < MINES) {
    const c = mine.cells[Math.floor(Math.random() * SIZE * SIZE)]
    if (!c.mine) { c.mine = true; placed++ }
  }
  mine.cells.forEach(c => {
    c.n = neighbors(c).filter(n => n.mine).length
  })
}
function neighbors(c) {
  const out = []
  for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
    if (!dx && !dy) continue
    const x = c.x + dx, y = c.y + dy
    if (x >= 0 && x < SIZE && y >= 0 && y < SIZE) out.push(mine.cells[y * SIZE + x])
  }
  return out
}
function cellText(c) {
  if (c.flagged && !c.revealed) return '🚩'
  if (!c.revealed) return ''
  if (c.mine) return '💥'
  return c.n || ''
}
function digCell(c) {
  if (mine.flagMode) { flagCell(c); return }
  if (c.revealed || c.flagged || mine.result) return
  if (c.mine) { c.revealed = c.boom = true; revealAll(); mine.result = '💥 踩雷了，重开一局？'; return }
  flood(c)
  checkWin()
}
function flagCell(c) {
  if (c.revealed || mine.result) return
  c.flagged = !c.flagged
  mine.flagsLeft = MINES - mine.cells.filter(x => x.flagged).length
}
function flood(c) {
  if (c.revealed || c.flagged) return
  c.revealed = true
  if (c.n === 0) neighbors(c).forEach(n => flood(n))
}
function revealAll() { mine.cells.forEach(c => { if (c.mine) c.revealed = true }) }
function checkWin() {
  const hidden = mine.cells.filter(c => !c.revealed).length
  if (hidden === MINES) mine.result = '🎉 通关！排雷成功'
}

onMounted(() => {
  init2048(); initMine()
  loadBests()
  if (g2048El.value) bindTouch(g2048El.value)
  window.addEventListener('keydown', onWindowKey)
})
onBeforeUnmount(() => {
  clearInterval(snake.timer)
  window.removeEventListener('keydown', onWindowKey)
})
</script>

<style scoped>
.gm-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.gm-tab {
  padding: 8px 22px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.1));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 13.5px;
}
.gm-tab.active { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.gm-pane { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.gm-info { font-size: 13.5px; color: var(--dp-text2, #45505b); display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center; }
.gm-info b { color: var(--yq-gold, #c7a96b); }
.gm-best { font-size: 12px; color: var(--dp-text3, #8a8f98); }
.gm-mini {
  padding: 4px 14px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b);
}
/* ---------- 窄屏（B 类响应式）：2048 棋盘在 360px 屏上会溢出 4px，格子缩一档 ---------- */
@media (max-width: 480px) {
  .g2048 { padding: 8px; gap: 6px; }
  .row2048 { gap: 6px; }
  .cell2048 { width: 62px; height: 62px; font-size: 21px; }
  .gm-tab { padding: 7px 16px; font-size: 13px; }
  .mine-cell { font-size: 12px; }
}
.gm-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.gm-center-msg { font-size: 14px; color: #e5484d; font-weight: 600; }
/* 2048 */
.g2048 {
  position: relative; display: flex; flex-direction: column; gap: 8px; padding: 10px; border-radius: 12px;
  background: rgba(0,0,0,.06); outline: none; touch-action: none; user-select: none;
}
.row2048 { display: flex; gap: 8px; }
.cell2048 {
  width: 72px; height: 72px; border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-size: 26px; font-weight: 800; background: rgba(255,255,255,.6); color: var(--dp-text, #18202a);
  font-variant-numeric: tabular-nums;
}
.cell2048.v2 { background: #eee9da; } .cell2048.v4 { background: #e8dfc0; }
.cell2048.v8 { background: #f2b179; color: #fff; } .cell2048.v16 { background: #f59563; color: #fff; }
.cell2048.v32 { background: #f67c5f; color: #fff; } .cell2048.v64 { background: #f65e3b; color: #fff; }
.cell2048.v128, .cell2048.v256, .cell2048.v512 { background: #edcf72; }
.cell2048.v1024, .cell2048.v2048 { background: #edc22e; }
.g2048-over {
  position: absolute; inset: 0; border-radius: 12px; background: rgba(255,255,255,.82);
  display: flex; flex-direction: column; gap: 12px; align-items: center; justify-content: center; font-size: 18px; font-weight: 700;
}
/* 贪吃蛇 */
.snake-cv { border-radius: 12px; outline: none; border: 1px solid var(--dp-line, rgba(0,0,0,.1)); max-width: 100%; }
/* 扫雷 */
.mine-grid {
  display: grid; grid-template-columns: repeat(10, 34px); gap: 2px; padding: 8px; border-radius: 12px;
  background: rgba(0,0,0,.06);
}
.mine-cell {
  width: 34px; height: 34px; border-radius: 5px; display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 700; background: #b9c4b9; cursor: pointer; user-select: none;
  color: var(--dp-text, #18202a); font-variant-numeric: tabular-nums;
}
.mine-cell.revealed { background: rgba(255,255,255,.7); cursor: default; }
.mine-cell.flagged { background: #e8dfc0; }
.mine-cell.boom { background: #f6b0b3; }
.gm-toggle { font-size: 13px; color: var(--dp-text2, #45505b); }
</style>
