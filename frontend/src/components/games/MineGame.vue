<template>
  <div class="mn-wrap">
    <div class="mn-info">左键翻开 · 右键/旗子模式插旗 · 剩余雷 <b>{{ mine.flagsLeft }}</b>
      <button class="mn-btn" @click="initMine">重开</button>
    </div>
    <div class="mn-grid">
      <div
        v-for="cell in mine.cells"
        :key="cell.i"
        class="mn-cell"
        :class="{ revealed: cell.revealed, boom: cell.boom, flagged: cell.flagged }"
        @click="digCell(cell)"
        @contextmenu.prevent="flagCell(cell)"
      >{{ cellText(cell) }}</div>
    </div>
    <div class="mn-toggle">
      <label class="mn-flagmode"><input v-model="mine.flagMode" type="checkbox"> 旗子模式（手机用）</label>
    </div>
    <div v-if="mine.result" class="mn-msg">{{ mine.result }}</div>
  </div>
</template>

<script setup>
/** 扫雷：从旧 GamesView 原样迁移。 */
import { reactive } from 'vue'

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
  mine.cells.forEach(c => { c.n = neighbors(c).filter(n => n.mine).length })
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
initMine()
</script>

<style scoped>
.mn-wrap { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.mn-info { font-size: 13.5px; color: var(--dp-text2, #45505b); display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: center; }
.mn-info b { color: var(--yq-gold, #c7a96b); }
.mn-btn { padding: 4px 14px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b); font-family: inherit; }
.mn-grid {
  display: grid; grid-template-columns: repeat(10, 34px); gap: 2px; padding: 8px; border-radius: 12px;
  background: rgba(0,0,0,.06);
}
.mn-cell {
  width: 34px; height: 34px; border-radius: 5px; display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 700; background: #b9c4b9; cursor: pointer; user-select: none;
  color: var(--dp-text, #18202a); font-variant-numeric: tabular-nums;
}
.mn-cell.revealed { background: rgba(255,255,255,.7); cursor: default; }
.mn-cell.flagged { background: #e8dfc0; }
.mn-cell.boom { background: #f6b0b3; }
.mn-toggle { font-size: 13px; color: var(--dp-text2, #45505b); }
.mn-msg { font-size: 14px; font-weight: 600; color: var(--yq-gold, #c7a96b); }

@media (max-width: 480px) {
  .mn-grid { grid-template-columns: repeat(10, 30px); }
  .mn-cell { width: 30px; height: 30px; font-size: 12px; }
}
</style>
