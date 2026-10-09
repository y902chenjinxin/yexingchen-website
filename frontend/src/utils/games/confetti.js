/** 棋牌 · 胜利彩带粒子（v2.46.19）。
 *
 * 纯 CSS transform 实现的彩带雨（样式在 game-table.css 的 .gt-confetti），
 * 这里只负责生成每条彩带的确定性伪随机参数（位置 / 延迟 / 时长 / 旋转 / 颜色）——
 * 用 index 做种子的 LCG，同一屏每次渲染分布一致，不会闪变。
 * prefers-reduced-motion 下 CSS 直接 display:none，JS 不用管。
 */
const COLORS = ['#e9c877', '#f4dc9c', '#7fd0a8', '#6db3f2', '#e2554c', '#c9a227']

export function confettiPieces(n = 26) {
  const out = []
  let s = 7
  const rnd = () => { s = (s * 48271) % 2147483647; return s / 2147483647 }
  for (let i = 0; i < n; i++) {
    out.push({
      '--cx': `${(rnd() * 96 + 2).toFixed(1)}%`,
      '--cd': `${(rnd() * 1.6).toFixed(2)}s`,
      '--cdur': `${(rnd() * 1.2 + 1.6).toFixed(2)}s`,
      '--crot': `${Math.round(rnd() * 900 - 450)}deg`,
      '--cc': COLORS[i % COLORS.length],
    })
  }
  return out
}

export default confettiPieces
