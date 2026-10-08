/* 验证掼蛋划选「主轴投影」算法（V2462-001 回归）
 *
 * 复刻 GuandanBoard.vue 里 handAxis / cardIndexAt / cacheCardRects 的几何算法，
 * 喂入**旋转 90° 后的屏幕轴对齐包围盒**（手机竖屏全屏牌桌的真实形态），
 * 断言「手指落在第 i 张牌的可见条带上 → 命中索引就是 i」。
 *
 * 旧算法（固定用 clientX 撞 rect.left/right）在旋转下会恒返回同一个索引，
 * 本脚本会把两种算法都跑一遍做对照，确保新算法真的修好了。
 *
 * 跑法：node artifacts/_probe/verify_guandan_swipe.js
 */

const H = 390            // 逻辑画布高（手机横屏视野）
const CARD_W = 64        // 牌宽
const STEP = 22          // 每张牌露出的宽度（重叠布局）
const N = 27             // 掼蛋 4 人局每人 27 张
const LOG_TOP = 280      // 手牌区在逻辑坐标里的上边
const LOG_H = 91         // 手牌区高度（≈ CARD_W × 1.42）
const PAD = Math.max(28, CARD_W * 0.5)

/* 逻辑点 → 屏幕点：transform: rotate(90deg) translateY(-100%)，transform-origin: top left
   （GamesView 的竖屏兜底）。推导：先 translateY(-100%) 再 rotate90 → f(x,y) = (H - y, x) */
const f = (x, y) => [H - y, x]

function rectOf(x0, y0, w, h) {
  const pts = [f(x0, y0), f(x0 + w, y0), f(x0, y0 + h), f(x0 + w, y0 + h)]
  const xs = pts.map((p) => p[0])
  const ys = pts.map((p) => p[1])
  const left = Math.min(...xs)
  const right = Math.max(...xs)
  const top = Math.min(...ys)
  const bottom = Math.max(...ys)
  // 真实 DOMRect 一定带 width/height，模拟对象必须一并给出，
  // 否则 handAxis() 里的 height > width 会退化成 undefined > undefined = false
  return { left, right, top, bottom, width: right - left, height: bottom - top }
}

const handRect = rectOf(0, LOG_TOP, N * STEP, LOG_H)
const cardRects = []
for (let i = 0; i < N; i++) cardRects.push({ i, ...rectOf(i * STEP, LOG_TOP, CARD_W, LOG_H) })

/* ---------- 新算法（与源码一致） ---------- */
function handAxis() {
  return handRect.height > handRect.width ? 'y' : 'x'
}
function cardIndexNew(clientX, clientY, ignoreCross = false) {
  if (!cardRects.length) return -1
  const axis = handAxis()
  const p = axis === 'y' ? clientY : clientX
  if (!ignoreCross) {
    const q = axis === 'y' ? clientX : clientY
    const lo = axis === 'y' ? handRect.left : handRect.top
    const hi = axis === 'y' ? handRect.right : handRect.bottom
    if (q < lo - PAD || q > hi + PAD) return -1
  }
  let hit = -1
  for (const c of cardRects) {
    const a = axis === 'y' ? c.top : c.left
    const b = axis === 'y' ? c.bottom : c.right
    if (p >= a && p <= b) hit = c.i
  }
  return hit
}

/* ---------- 旧算法（固定 clientX） ---------- */
function cardIndexOld(clientX) {
  let hit = -1
  for (const c of cardRects) {
    if (clientX >= c.left && clientX <= c.right) hit = c.i
  }
  return hit
}

/* ---------- 断言 ---------- */
let fail = 0
function ok(cond, msg) {
  if (cond) { console.log(`  ✓ ${msg}`); return }
  fail += 1
  console.log(`  ✗ ${msg}`)
}

console.log(`手牌区 AABB: ${JSON.stringify(handRect)}`)
console.log(`主轴判定: handAxis() = '${handAxis()}'  (height=${handRect.height} vs width=${handRect.width})`)

const midX = (handRect.left + handRect.right) / 2

console.log('\n[1] 手指落在每张牌的可见条带中心 —— 新算法应命中同一索引')
for (let i = 0; i < N; i++) {
  const y = i * STEP + STEP / 2          // 条带中心（屏幕 y）
  const got = cardIndexNew(midX, y)
  ok(got === i, `第 ${i} 张条带 (y=${y.toFixed(1)}) → 命中 ${got}`)
}

console.log('\n[2] 同一批坐标喂给旧算法 —— 应大面积错位（证明旧实现确实坏了）')
let oldWrong = 0
for (let i = 0; i < N; i++) {
  const y = i * STEP + STEP / 2
  const got = cardIndexOld(midX)
  if (got !== i) oldWrong += 1
  if (i < 3 || i > N - 2) console.log(`  第 ${i} 张 → 旧算法命中 ${got}`)
}
ok(oldWrong > N * 0.7, `旧算法错位 ${oldWrong}/${N} 张（>70% 即视为失效）`)

console.log('\n[3] 连续划选模拟：手指从第 0 张滑到第 26 张（每步 +5px）')
const covered = new Set()
let lastIdx = -1
for (let y = STEP / 2; y <= (N - 1) * STEP + STEP / 2; y += 5) {
  const idx = cardIndexNew(midX, y, true)   // ignoreCross=true，与划选进行中一致
  if (idx < 0) continue
  const from = lastIdx < 0 ? idx : Math.min(lastIdx, idx)
  const to = lastIdx < 0 ? idx : Math.max(lastIdx, idx)
  lastIdx = idx
  for (let k = from; k <= to; k++) covered.add(k)
}
ok(covered.size === N, `划选覆盖 ${covered.size}/${N} 张（应为全部）`)
const missing = []
for (let i = 0; i < N; i++) if (!covered.has(i)) missing.push(i)
if (missing.length) console.log(`  漏选: ${missing.join(', ')}`)

console.log('\n[4] 反向划选：从第 26 张滑回第 0 张')
const back = new Set()
lastIdx = -1
for (let y = (N - 1) * STEP + STEP / 2; y >= STEP / 2; y -= 5) {
  const idx = cardIndexNew(midX, y, true)
  if (idx < 0) continue
  const from = lastIdx < 0 ? idx : Math.min(lastIdx, idx)
  const to = lastIdx < 0 ? idx : Math.max(lastIdx, idx)
  lastIdx = idx
  for (let k = from; k <= to; k++) back.add(k)
}
ok(back.size === N, `反向划选覆盖 ${back.size}/${N} 张`)

console.log('\n[5] 横屏未旋转时仍走 x 轴（回归保护）')
const flatHand = { left: 0, right: N * STEP, top: LOG_TOP, bottom: LOG_TOP + LOG_H }
const axisFlat = flatHand.bottom - flatHand.top > flatHand.right - flatHand.left ? 'y' : 'x'
ok(axisFlat === 'x', `横条手牌区主轴 = '${axisFlat}'（应为 x）`)

console.log(fail ? `\n❌ ${fail} 项失败` : '\n✅ 全部通过')
process.exit(fail ? 1 : 0)
