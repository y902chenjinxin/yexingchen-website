<template>
  <div class="sn-wrap">
    <div class="sn-info">方向键转向 · <b>{{ snake.score }}</b> 分
      <span class="sn-best">最高 {{ best }}</span>
      <button class="sn-btn" @click="initSnake">重开</button>
    </div>
    <canvas ref="snakeEl" width="400" height="400" class="sn-cv" tabindex="0"></canvas>
    <div v-if="snake.over" class="sn-msg">撞到了 · {{ snake.score }} 分，按「重开」再来</div>
    <p class="sn-hint">电脑端方向键直接可用（无需点棋盘）· 手机建议电脑玩</p>
  </div>
</template>

<script setup>
/** 贪吃蛇：从旧 GamesView 原样迁移（v2.40.18 的窗口级键盘监听改为组件内自管）。 */
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'

// 页面（GamesView）统一传模式/续局/门面标记；贪吃蛇无模式也不续局，声明以免落到根元素属性上
defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
})

const snakeEl = ref(null)
const snake = reactive({ score: 0, over: false, dir: [1, 0], body: [], food: [0, 0], timer: 0 })
const best = ref(Number(localStorage.getItem('snake_best') || 0) || 0)

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
  if (snake.body.some(([x, y]) => x === head[0] && y === head[1])) {
    snake.over = true; clearInterval(snake.timer); drawSnake(); return
  }
  snake.body.unshift(head)
  if (head[0] === snake.food[0] && head[1] === snake.food[1]) { snake.score += 10; placeFood() }
  else snake.body.pop()
  if (snake.score > best.value) { best.value = snake.score; localStorage.setItem('snake_best', String(best.value)) }
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
  ctx.fillStyle = '#e5484d'
  ctx.beginPath(); ctx.arc(snake.food[0] * S + 10, snake.food[1] * S + 10, 7, 0, 7); ctx.fill()
  snake.body.forEach(([x, y], i) => {
    ctx.fillStyle = i === 0 ? '#c7a96b' : `rgba(127,168,163,${Math.max(0.35, 1 - i / snake.body.length)})`
    ctx.fillRect(x * S + 1, y * S + 1, S - 2, S - 2)
  })
}
function onWindowKey(e) {
  const t = e.target
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
  if (e.key.startsWith('Arrow')) { e.preventDefault(); onKeySnake(e) }
}
onMounted(() => {
  initSnake()
  window.addEventListener('keydown', onWindowKey)
})
onBeforeUnmount(() => {
  clearInterval(snake.timer)
  window.removeEventListener('keydown', onWindowKey)
})
</script>

<style scoped>
.sn-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.sn-info { font-size: 13.5px; color: var(--dp-text2, #45505b); display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center; }
.sn-info b { color: var(--yq-gold, #c7a96b); }
.sn-best { font-size: 12px; color: var(--dp-text3, #8a8f98); }
.sn-btn { padding: 4px 14px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b); font-family: inherit; }
.sn-cv { border-radius: 12px; outline: none; border: 1px solid var(--dp-line, rgba(0,0,0,.1)); max-width: 100%; }
.sn-msg { font-size: 14px; color: #e5484d; font-weight: 600; }
.sn-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
</style>
