/**
 * 触觉 / 听觉反馈中心（APP_design.md #13 起）
 *
 * 一个模块管三件事，别拆成两个名字近似的文件（曾经差点出现 haptic.js + haptics.js）：
 *
 *  1. **分级震动**（v2.46.33 起）：`haptic.light/medium/heavy/success/error`
 *     —— 语义化调用点（Tab 切换、保存成功、删除确认）。
 *  2. **刻度「哒」**（v2.46.323）：`tick()` + `stepTick()`
 *     —— 复刻「手机指南针」转盘的刻度阻尼：声音用 Web Audio 实时合成，
 *        0 字节资源、<1ms 延迟（滚动里对延迟极敏感，mp3 解码根本来不及）。
 *  3. **全站按钮震感**：`installTapFeedback()` 用 document 级事件委托挂一次，
 *     不逐个包 200+ 个按钮，弹窗/抽屉/虚拟列表里的动态按钮也自动覆盖。
 *
 * 三条纪律（改之前先读）：
 *  1. **限流 50ms**：1 秒跨 5 张卡时，声音重叠会变成刺耳噪音（人耳也分不清）。
 *  2. **envelope 两头都要到 0.0001**，绝不能 `gain=0.2 → stop`：
 *     波形被硬切在非零位置就是"啪"的爆音。
 *  3. **AudioContext 必须在用户手势栈内 resume**（iOS）：滚动事件里 resume 会被拒，
 *     所以首个 pointerdown/touchstart 时预热一次（`installUnlock`）。
 *
 * 所有反馈受「个人中心 → 刻度反馈」开关统一控制（`setEnabled`），默认开。
 *
 * 用法：
 *   import { haptic, tick, stepTick, installUnlock, installTapFeedback } from '@/utils/haptic'
 *   haptic.light()          // Tab 切换、轻点
 *   haptic.medium()         // 保存成功、确认
 *   haptic.heavy()          // 删除、校验失败
 *   tick()                  // 横向吸附跨格
 *   stepTick(e)             // <input type="range"> @input
 */

/** 两次「哒」的最小间隔（ms）。低于 50 人耳听成一串电流声。 */
const MIN_GAP_MS = 50
/** 全站按钮兜底：与组件自己发的 haptic 之间的「已反馈」判定窗口（ms）。 */
const TAP_DEDUPE_MS = 80

let enabled = true
let ctx = null
let master = null
let lastTickAt = 0
let lastFireAt = 0

export function setEnabled(v) {
  enabled = !!v
}

export function isEnabled() {
  return enabled
}

/* ============================ 声音 ============================ */

function nowMs() {
  return typeof performance !== 'undefined' ? performance.now() : Date.now()
}

function ensureCtx() {
  if (ctx) return ctx
  if (typeof window === 'undefined') return null
  const AC = window.AudioContext || window.webkitAudioContext
  if (!AC) return null
  try {
    ctx = new AC({ latencyHint: 'interactive' })
  } catch {
    try { ctx = new AC() } catch { return null }
  }
  master = ctx.createGain()
  // 总线压到 0.5：单次 tick 很短，过响会显廉价
  master.gain.value = 0.5
  master.connect(ctx.destination)
  return ctx
}

/** 在首个用户手势里调用一次：iOS 只允许在手势栈内启动/恢复 AudioContext。 */
export function installUnlock() {
  if (typeof window === 'undefined') return
  const resume = () => {
    const c = ensureCtx()
    if (c && c.state === 'suspended') c.resume().catch(() => {})
    window.removeEventListener('pointerdown', resume)
    window.removeEventListener('touchstart', resume)
    window.removeEventListener('keydown', resume)
  }
  window.addEventListener('pointerdown', resume, { passive: true })
  window.addEventListener('touchstart', resume, { passive: true })
  window.addEventListener('keydown', resume)
}

/** 设备是否有任何反馈通道（iOS 无 vibrate，但有声音）。 */
export function hasAnyFeedback() {
  const hasAudio = typeof window !== 'undefined' && !!(window.AudioContext || window.webkitAudioContext)
  const hasVibrate = typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function'
  return hasAudio || hasVibrate
}

/**
 * 一声刻度「哒」（横向吸附跨格用）。
 * @param {number} strength 0.35~1，滑得越快可以给越大
 */
export function tick(strength = 1) {
  if (!enabled) return
  const now = nowMs()
  if (now - lastTickAt < MIN_GAP_MS) return
  lastTickAt = now
  playTick(strength)
  fire(10)
}

/**
 * `<input type="range">` 的 input 事件专用：**只有档位真的变了才响**。
 *
 * 按元素记上次值（WeakMap）而不是全局变量：阅读设置里 5 个滑杆共用一个 handler，
 * 全局变量会在「从字号滑到行距」时因为值不同而多响一声（明明没跨档）。
 */
const lastVals = new WeakMap()
export function stepTick(e) {
  const el = e?.target
  if (!el) return
  const v = el.value
  if (!v || lastVals.get(el) === v) return
  lastVals.set(el, v)
  tick()
}

function playTick(strength) {
  const c = ensureCtx()
  if (!c) return
  if (c.state === 'suspended') c.resume().catch(() => {})

  const t0 = c.currentTime
  const dur = 0.03
  const s = Math.max(0.35, Math.min(1, strength))

  const osc = c.createOscillator()
  const gain = c.createGain()
  osc.type = 'sine'
  // 频率滑落一点（1.75k → 1.15k）：定频听起来像"电子哔"，带下滑才有指针摩擦感
  const f0 = 1750 + Math.random() * 120
  osc.frequency.setValueAtTime(f0, t0)
  osc.frequency.exponentialRampToValueAtTime(f0 * 0.66, t0 + dur)

  const peak = 0.14 * s
  gain.gain.setValueAtTime(0.0001, t0)
  gain.gain.exponentialRampToValueAtTime(peak, t0 + 0.003)
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)

  osc.connect(gain)
  gain.connect(master)
  osc.start(t0)
  osc.stop(t0 + dur + 0.005)
  // 主动断开：滑久了已结束的节点不该一直挂在音频图上
  osc.onended = () => {
    try { osc.disconnect(); gain.disconnect() } catch { /* noop */ }
  }
}

/** 按钮兜底用的极轻一声（比刻度更短更小），自带 40ms 去重。 */
let lastSoftAt = 0
function softClick() {
  const c = ensureCtx()
  if (!c) return
  const now = nowMs()
  if (now - lastSoftAt < 40) return
  lastSoftAt = now
  if (c.state === 'suspended') c.resume().catch(() => {})

  const t0 = c.currentTime
  const osc = c.createOscillator()
  const gain = c.createGain()
  osc.type = 'sine'
  osc.frequency.setValueAtTime(1180, t0)
  gain.gain.setValueAtTime(0.0001, t0)
  gain.gain.exponentialRampToValueAtTime(0.05, t0 + 0.002)
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.018)
  osc.connect(gain)
  gain.connect(master)
  osc.start(t0)
  osc.stop(t0 + 0.022)
  osc.onended = () => {
    try { osc.disconnect(); gain.disconnect() } catch { /* noop */ }
  }
}

/* ============================ 震动 ============================ */

function fire(pattern) {
  lastFireAt = nowMs()
  if (!enabled) return
  try {
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') navigator.vibrate(pattern)
  } catch {
    /* iOS Safari 根本没有 vibrate，静默降级 */
  }
}

/* ============================ 分级 API（旧调用点保持不变） ============================ */

export const haptic = {
  light: () => fire(8),
  medium: () => fire(18),
  heavy: () => fire(32),
  /** 双击节奏：成功提示（配合视觉成功态） */
  success: () => fire([10, 40, 14]),
  /** 三段急促：错误/警告 */
  error: () => fire([10, 30, 10, 30, 14]),
}

/** 只震不响（老名字，等价 haptic.light）。 */
export function buzz(ms = 8) {
  fire(ms)
}

/* ============================ 全站按钮震感 ============================ */

/**
 * 一次 click 就能命中的可点元素。用 closest 兜住：
 *  `button` / `a[href]` 覆盖 90%，其余是自定义组件把 role 挂在 div 上的写法。
 */
const TAP_SELECTOR = [
  'button',
  'a[href]',
  '[role="button"]',
  '[role="tab"]',
  '[role="switch"]',
  '[role="menuitem"]',
  '[role="option"]',
  '[role="checkbox"]',
  '.el-switch',
  '.el-checkbox',
  '.el-radio',
  '.el-pagination button',
  'label.el-checkbox',
  'label.el-radio',
  'input[type="checkbox"]',
  'input[type="radio"]',
].join(',')

let tapBound = false

/**
 * 全站按钮「点一下就震」——document 级事件委托挂一次。
 *
 * 为什么挂 click 而不是 pointerdown：
 *  项目里有 8 个文件自己调了 `haptic.medium()/heavy()`，那些是**语义化**反馈
 *  （保存成功、删除确认）。挂在 click 且位于冒泡末端（document）时，组件自己的
 *  处理先跑、`lastFireAt` 已更新，这里就识别出「已经有人反馈过」而跳过，
 *  不会出现 8ms + 18ms 的「连震两下」。
 *
 * @returns {() => void} 解绑
 */
/** 触摸设备判定：兜底音只在真机（无马达的 iOS）放，桌面浏览器点了不该有声音。 */
function isTouchDevice() {
  if (typeof window === 'undefined') return false
  return (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window
}

export function installTapFeedback() {
  if (tapBound || typeof document === 'undefined') return () => {}
  tapBound = true

  const onClick = (e) => {
    if (!enabled) return
    const t = e.target
    if (!t || !t.closest) return
    const el = t.closest(TAP_SELECTOR)
    if (!el) return
    if (el.disabled || el.getAttribute('aria-disabled') === 'true' || el.classList.contains('is-disabled')) return
    // 组件自己刚发过反馈（同一事件的冒泡里）→ 不重复
    if (nowMs() - lastFireAt < TAP_DEDUPE_MS) return
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') fire(8)
    // iOS / 无马达设备：一声极轻的「嗒」兜底，别让手指毫无反馈。
    // ⚠️ 必须限定触摸设备：桌面 Firefox/Safari 没有 navigator.vibrate，
    //    按鼠标也放声音会变成"满屏点击音"，很吵。
    else if (isTouchDevice()) softClick()
  }

  document.addEventListener('click', onClick, { passive: true })
  return () => {
    document.removeEventListener('click', onClick)
    tapBound = false
  }
}
