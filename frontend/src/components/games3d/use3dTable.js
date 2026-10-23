/** 3D 棋牌共用变换助手（v2.46.122）
 *
 * 纯函数，无 Vue 依赖。数值与 Games3DView.vue 原实现一致：
 * 固定正视微前倾视角（VIEW_RX），牌桌顶面 z=15、立牌高 60 → 中心 z=45 等。 */

export const VIEW_RX = 66
export const CENTER_TF = 'translate(-50%,-50%) translate3d(0px,0px,240px) scale(0.16)'

/** 3D 盒子的宽/高/厚 CSS 变量 */
export function boxVars(w, h, t) {
  return { '--w': w + 'px', '--h': h + 'px', '--t': t + 'px' }
}

/** 通用 3D 块样式：dealt=false 时收拢到中央；instant=true 用于摸牌飞入（无错峰延迟） */
export function pieceBox(dealt, w, h, t, finalTF, delayIdx, clickable, instant) {
  return {
    ...boxVars(w, h, t),
    transform: dealt ? finalTF : CENTER_TF,
    transitionDelay: instant ? '0ms' : (delayIdx * 28) + 'ms',
    cursor: clickable ? 'pointer' : 'default',
  }
}

/** 牌墙：'N'|'W'|'E'，step=45（牌宽 46，1px 搭接），桌面顶 z=15 + 半牌高 30 = 45 */
export function wallTF(side, i, n) {
  const step = 45
  const off = (i - (n - 1) / 2) * step
  let x = 0, y = 0, rotZ = 0
  if (side === 'N') { x = off; y = -270; rotZ = 180 }
  else if (side === 'W') { x = -270; y = off; rotZ = 90 }
  else { x = 270; y = off; rotZ = -90 }
  return `translate(-50%,-50%) translate3d(${x}px,${y}px,45px) rotateZ(${rotZ}deg) rotateX(-90deg)`
}

/** 玩家手牌：两种形态 —— 麻将竖插在桌上，扑克立起后仰像拿在手里。
 *  step 自适应：牌多时（掼蛋 27 张）自动收窄重叠，总宽不超过约 1000px；
 *  lift>0 表示选中抬升（沿 z 轴抬）。
 *
 * 🔴 v2.46.228：掼蛋原来走 stand=false 完全不加旋转，牌跟着世界 rotateX(66°)
 *    平躺在桌面，玩家看到的是一条压扁牌带 —— "牌不是对着我的"。
 * 🔴 v2.46.229：上一版直接照搬麻将的 rotateX(-90°)（竖直插在桌上）也不对 ——
 *    扑克不是麻将，参考主流掼蛋手游（欢乐掼蛋 / 微信掼蛋）的持牌：
 *    **牌立起约 60°、牌面朝玩家并略微后仰**，保留 6° 与视线的夹角出立体感
 *    （能看见牌的侧厚度，而不是一张贴在屏幕上的平面贴图）。
 *    与中央出牌区 centerTF 的 rotateX(-52°) 同一语系。 */
export function handTF(i, n, stand, ty = 324, lift = 0) {
  const step = Math.min(44, 1000 / Math.max(1, n))
  const off = (i - (n - 1) / 2) * step
  if (stand) return `translate(-50%,-50%) translate3d(${off}px,${ty}px,${46 + lift}px) rotateX(-90deg)`
  return `translate(-50%,-50%) translate3d(${off}px,${ty}px,${46 + lift}px) rotateX(-60deg)`
}

/** 对手手牌背面：'N'|'W'|'E' */
export function oppTF(side, k, n) {
  const step = 50
  const off = (k - (n - 1) / 2) * step
  let x = 0, y = 0
  if (side === 'N') { x = off; y = -300 }
  else if (side === 'W') { x = -300; y = off }
  else { x = 300; y = off }
  return `translate(-50%,-50%) translate3d(${x}px,${y}px,21px)`
}

/** 中央出牌区：错位螺旋排布，立起 52° 朝镜头 */
export function centerTF(i, lift = 40, perSeatOffset) {
  const base = perSeatOffset || { x: 0, y: 0 }
  const a = i * 0.7
  const x = base.x + Math.cos(a) * (i * 6)
  const y = base.y + Math.sin(a) * (i * 6)
  return `translate(-50%,-50%) translate3d(${x}px,${y}px,${lift}px) rotateX(-52deg)`
}

/** 座位铭牌 billboard：抵消世界倾斜，始终竖立正对镜头 */
export function seatTF(s) {
  return { transform: `translate(-50%,-50%) translate3d(${s.pos[0]}px,${s.pos[1]}px,${s.lift}px) rotateX(-${VIEW_RX}deg)` }
}

/** 三点一线：把 s（0..3，相对本家）映射到屏幕位（0=下 1=右 2=上 3=左） */
export function screenPos(s, povSeat) { return ((Number(s) - povSeat) % 4 + 4) % 4 }

/** 四个座位在 3D 世界的固定位（下标 = 屏幕位：0下 1右 2上 3左） */
export const SEAT_SLOT = [
  { pos: [0, 398], lift: 24 },    // 0 下（你）
  { pos: [392, 0], lift: 80 },   // 1 右
  { pos: [0, -318], lift: 96 },  // 2 上
  { pos: [-392, 0], lift: 80 },  // 3 左
]

/** 手牌区中央牌墙/出牌区的原点偏移（按屏幕位） */
export const CENTER_SLOT = [
  { x: 0, y: 0 }, { x: 0, y: 0 }, { x: 0, y: 0 }, { x: 0, y: 0 },
]
