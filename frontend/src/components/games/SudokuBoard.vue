<template>
  <div class="sd-wrap">
    <div class="sd-toolbar">
      <div v-if="!bare" class="sd-modes">
        <button v-for="m in modes" :key="m.key" class="sd-mode" :class="{ on: diff === m.key }" @click="setDiff(m.key)">{{ m.label }}</button>
      </div>
      <div class="sd-status">
        <span>⏱ {{ fmtTime(elapsed) }}</span>
        <span>剩余 <b>{{ remain }}</b></span>
        <button class="sd-btn" @click="newGame">新开一局</button>
        <button class="sd-btn" :disabled="!selected || done" @click="hint">提示一格</button>
      </div>
    </div>

    <div class="sd-board" :class="{ done }">
      <div
        v-for="idx in 81"
        :key="idx"
        class="sd-cell"
        :class="{
          given: given[idx - 1],
          sel: selected === idx - 1,
          bad: isBad(idx - 1),
          peer: samePeer(idx - 1),
          same: sameNumber(idx - 1),
        }"
        @click="selected = idx - 1"
      >{{ grid[idx - 1] || '' }}</div>
    </div>

    <div class="sd-pad">
      <button v-for="n in 9" :key="n" class="sd-num" :disabled="done" @click="input(n)">{{ n }}</button>
      <button class="sd-num sd-erase" :disabled="!selected || given[selected]" @click="input(0)">⌫</button>
    </div>
    <div v-if="done" class="sd-done">🎉 完成！用时 {{ fmtTime(elapsed) }}<button class="sd-btn" @click="newGame">再来一局</button></div>
    <p class="sd-hint">点格子再点数字填入 · 填错的数字会标红（同行/列/宫重复）· 卡住就点「提示一格」</p>
  </div>
</template>

<script setup>
/** 数独（自写）：对角宫随机填充 → 回溯求解出完整解 → 挖洞（带唯一解校验）。
 * 难度：入门挖 38 洞 / 进阶 45 / 困难 52。
 * 交互：点选格 → 数字键盘；填错（同行/列/宫冲突）标红；提示格永久固定。
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { loadGame, saveGame, clearGame } from '@/utils/gameSave'

const props = defineProps({
  initialMode: { type: String, default: '' },   // 难度由页面「第一步」选定
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
})
const modes = [
  { key: 'easy', label: '入门' },
  { key: 'mid', label: '进阶' },
  { key: 'hard', label: '困难' },
]
const HOLES = { easy: 38, mid: 45, hard: 52 }
const diff = ref(props.initialMode || 'easy')
const grid = ref(Array(81).fill(0))
const solution = ref(Array(81).fill(0))
const given = ref(Array(81).fill(false))
const selected = ref(-1)
const elapsed = ref(0)
const done = ref(false)
let timer = null

const remain = computed(() => grid.value.filter(v => !v).length)

function rc(idx) { return [Math.floor(idx / 9), idx % 9] }
function peersOf(idx) {
  const [r, c] = rc(idx)
  const out = new Set()
  for (let i = 0; i < 9; i++) { out.add(r * 9 + i); out.add(i * 9 + c) }
  const br = Math.floor(r / 3) * 3, bc = Math.floor(c / 3) * 3
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) out.add((br + i) * 9 + bc + j)
  out.delete(idx)
  return out
}
const PEERS = Array.from({ length: 81 }, (_, i) => peersOf(i))

function okAt(bd, idx, v) {
  for (const p of PEERS[idx]) if (bd[p] === v) return false
  return true
}
function solve(bd, limit = 2) {
  // 回溯求解；count 超过 limit 提前返回（用于唯一解校验）
  let count = 0
  const rec = () => {
    const idx = bd.indexOf(0)
    if (idx < 0) { count++; return count <= limit }
    for (let v = 1; v <= 9; v++) {
      if (okAt(bd, idx, v)) {
        bd[idx] = v
        if (!rec()) { bd[idx] = 0; return false }
        bd[idx] = 0
        if (count > limit) return false
      }
    }
    return true
  }
  rec()
  return count
}

function fullSolution() {
  const bd = Array(81).fill(0)
  // 三个对角宫先随机填，剩下回溯，生成快且随机性好
  for (const b of [0, 4, 8]) {
    const nums = [1, 2, 3, 4, 5, 6, 7, 8, 9].sort(() => Math.random() - 0.5)
    let k = 0
    const br = Math.floor(b / 3) * 3, bc = (b % 3) * 3
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) bd[(br + i) * 9 + bc + j] = nums[k++]
  }
  const rec = () => {
    const idx = bd.indexOf(0)
    if (idx < 0) return true
    for (let v = 1; v <= 9; v++) {
      if (okAt(bd, idx, v)) { bd[idx] = v; if (rec()) return true; bd[idx] = 0 }
    }
    return false
  }
  rec()
  return bd
}

function newGame() {
  clearGame(SAVE_KEY)
  const sol = fullSolution()
  const puzzle = [...sol]
  const order = Array.from({ length: 81 }, (_, i) => i).sort(() => Math.random() - 0.5)
  let holes = 0
  for (const idx of order) {
    if (holes >= HOLES[diff.value]) break
    const backup = puzzle[idx]
    puzzle[idx] = 0
    if (solve([...puzzle], 2) !== 1) puzzle[idx] = backup   // 挖掉后解不唯一 → 填回
    else holes++
  }
  solution.value = sol
  grid.value = puzzle
  given.value = puzzle.map(v => !!v)
  selected.value = -1
  done.value = false
  elapsed.value = 0
}

function setDiff(k) { diff.value = k; newGame() }

function isBad(idx) {
  const v = grid.value[idx]
  if (!v || given.value[idx]) return false
  for (const p of PEERS[idx]) if (grid.value[p] === v) return true
  return false
}
function samePeer(idx) {
  if (selected.value < 0) return false
  return PEERS[selected.value].has(idx)
}
function sameNumber(idx) {
  const v = grid.value[idx]
  return v && selected.value >= 0 && grid.value[selected.value] === v && idx !== selected.value
}

function input(n) {
  if (done.value || selected.value < 0 || given.value[selected.value]) return
  grid.value[selected.value] = n
  if (grid.value.every(v => v) && !grid.value.some((_, i) => isBad(i))) done.value = true
}

function hint() {
  if (selected.value < 0 || given.value[selected.value]) return
  grid.value[selected.value] = solution.value[selected.value]
  given.value[selected.value] = true   // 提示后视为固定
  if (grid.value.every(v => v) && !grid.value.some((_, i) => isBad(i))) done.value = true
}

function fmtTime(s) {
  const m = Math.floor(s / 60)
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

/* ---------- 本地存档：返回列表后可「继续上一局」（含计时延续） ---------- */
const SAVE_KEY = 'sudoku'
let saveTimer = null
const diffLabel = computed(() => (modes.find(m => m.key === diff.value) || {}).label || '')
function saveLocal() {
  if (done.value || !given.value.some(Boolean)) return
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveGame(SAVE_KEY, {
      mode: diff.value,
      summary: `${diffLabel.value} · 已填 ${81 - remain.value}/81 · ${fmtTime(elapsed.value)}`,
      grid: grid.value, given: given.value, solution: solution.value,
      elapsed: elapsed.value, done: done.value,
    })
  }, 500)
}
function restoreLocal() {
  const s = loadGame(SAVE_KEY)
  if (!s || !Array.isArray(s.grid) || s.grid.length !== 81) return false
  if (s.mode) diff.value = s.mode
  grid.value = s.grid
  given.value = s.given || s.grid.map(v => !!v)
  solution.value = Array.isArray(s.solution) && s.solution.length === 81 ? s.solution : []
  elapsed.value = s.elapsed || 0
  done.value = !!s.done
  selected.value = -1
  return true
}
watch([grid, done], saveLocal, { deep: true })

onMounted(() => {
  if (props.resume && restoreLocal()) { /* 续局 */ } else { newGame() }
  timer = setInterval(() => { if (!done.value) elapsed.value++ }, 1000)
})
onBeforeUnmount(() => { clearInterval(timer); clearTimeout(saveTimer) })
</script>

<style scoped>
.sd-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; width: 100%; }
.sd-toolbar { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; justify-content: center; width: 100%; }
.sd-modes { display: flex; gap: 6px; }
.sd-mode { padding: 6px 14px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 12.5px; font-family: inherit; }
.sd-mode.on { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.sd-status { display: flex; align-items: center; gap: 12px; font-size: 13px; color: var(--dp-text2, #45505b); }
.sd-status b { color: var(--yq-gold, #c7a96b); }
.sd-btn { padding: 4px 13px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b); font-family: inherit; }
.sd-btn:disabled { opacity: .5; cursor: default; }

.sd-board {
  display: grid; grid-template-columns: repeat(9, var(--cell, 38px)); grid-auto-rows: var(--cell, 38px);
  gap: 1px; background: var(--dp-line, rgba(0,0,0,.25)); padding: 2px; border-radius: 10px;
  touch-action: manipulation; user-select: none;
}
.sd-cell {
  background: var(--dp-surface, #fff); border: none; padding: 0; cursor: pointer;
  font-size: 17px; font-weight: 600; color: var(--dp-text, #18202a); font-family: inherit;
  font-variant-numeric: tabular-nums;
}
.sd-cell:nth-child(3n) { margin-right: 3px; }
.sd-cell:nth-child(9n) { margin-right: 0; }
.sd-cell:nth-child(n + 19):nth-child(-n + 27),
.sd-cell:nth-child(n + 46):nth-child(-n + 54) { margin-bottom: 3px; }
.sd-cell.given { color: var(--dp-text2, #45505b); background: rgba(74,95,99,.07); cursor: default; }
.sd-cell.peer { background: rgba(127,168,163,.14); }
.sd-cell.same { background: rgba(199,169,107,.3); }
.sd-cell.sel { outline: 2px solid var(--yq-gold, #c7a96b); outline-offset: -2px; }
.sd-cell.bad { color: #e5484d !important; }
.sd-board.done .sd-cell { background: rgba(127,168,163,.2); }

.sd-pad { display: grid; grid-template-columns: repeat(10, var(--cell, 38px)); gap: 4px; }
.sd-num {
  height: 38px; border-radius: 8px; border: 1px solid var(--dp-line, rgba(0,0,0,.14));
  background: var(--dp-surface, #fff); color: var(--dp-text, #18202a); font-size: 15px; font-weight: 600;
  cursor: pointer; font-family: inherit; font-variant-numeric: tabular-nums;
}
.sd-num:hover { border-color: var(--yq-gold, #c7a96b); }
.sd-num:disabled { opacity: .5; cursor: default; }
.sd-erase { font-size: 13px; }
.sd-done { font-size: 15px; font-weight: 700; color: var(--yq-gold, #c7a96b); display: flex; gap: 12px; align-items: center; }
.sd-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); text-align: center; max-width: 460px; }

@media (max-width: 480px) {
  .sd-board { --cell: 32px; }
  .sd-pad { --cell: 30px; }
  .sd-pad { grid-template-columns: repeat(10, 1fr); width: 100%; }
}
</style>
