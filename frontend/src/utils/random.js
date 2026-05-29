/**
 * 伪随机数生成器（seeded） - 保证多次生成一致的随机序列
 * 用于粒子动画等需要确定性随机结果的场景
 */

// Mulberry32算法 - 轻量级高质量PRNG
function mulberry32(seed) {
  return function () {
    let t = (seed += 0x6d2b79f5)
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// 创建全局随机生成器（固定种子，保证页面刷新后粒子位置一致）
const globalRng = mulberry32(42)

export function random() {
  return globalRng()
}

export function randInt(min, max) {
  return Math.floor(random() * (max - min + 1)) + min
}

export function randFloat(min, max) {
  return random() * (max - min) + min
}