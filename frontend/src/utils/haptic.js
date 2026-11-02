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

/* 震动时长（ms）。v2.46.324 实测反馈「手指没感觉」——8ms 对 ERM 转子马达
   基本等于 0：转子从静止到有可感振幅要约 10~15ms，8ms 指令到的时候已经结束了。
   跨格给 16ms（够短，50ms 一格不会糊成连续震），点击给 26ms（明显"咔"一下）。 */
const TICK_MS = 16
const TAP_MS = 26
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
  fire(TICK_MS)
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

/**
 * 一声「咔哒」——**低沉木鱼感**，不是电子哔。
 *
 * v2.46.324 反馈「清脆了点，需要沉闷点」，所以三个参数一起往下压：
 *   · 基频从 1.75kHz 降到 620Hz（高频是"脆"的直接来源）；
 *   · 加一个 0.42 倍频的低八度"胸腔"，给重量感（只降频不加低频会变"闷哑"而不是"沉"）；
 *   · 串一个 1kHz 低通，削掉起音瞬间的宽带瞬态（那个瞬态就是"啪啪"的塑料感）；
 *   · 起音 3ms → 6ms，别让波形包络太陡。
 */
function playHit({ f0 = 620, f1 = 330, dur = 0.042, peak = 0.18, body = 0.6, cut = 1000 } = {}) {
  const c = ensureCtx()
  if (!c) return
  if (c.state === 'suspended') c.resume().catch(() => {})

  const t0 = c.currentTime

  // 低通放在总出口，两个振荡器共用
  const lp = c.createBiquadFilter()
  lp.type = 'lowpass'
  lp.frequency.setValueAtTime(cut, t0)
  lp.Q.value = 0.7
  lp.connect(master)

  // 主体：中低频下滑，是"芯"
  const o1 = c.createOscillator()
  const g1 = c.createGain()
  o1.type = 'sine'
  o1.frequency.setValueAtTime(f0, t0)
  o1.frequency.exponentialRampToValueAtTime(f1, t0 + dur)
  g1.gain.setValueAtTime(0.0001, t0)
  g1.gain.exponentialRampToValueAtTime(peak, t0 + 0.006)
  g1.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
  o1.connect(g1)
  g1.connect(lp)

  // 胸腔：再低八度，给"沉"的分量
  const o2 = c.createOscillator()
  const g2 = c.createGain()
  o2.type = 'sine'
  o2.frequency.setValueAtTime(f0 * 0.42, t0)
  o2.frequency.exponentialRampToValueAtTime(Math.max(60, f1 * 0.5), t0 + dur)
  g2.gain.setValueAtTime(0.0001, t0)
  g2.gain.exponentialRampToValueAtTime(peak * body, t0 + 0.006)
  g2.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
  o2.connect(g2)
  g2.connect(lp)

  o1.start(t0)
  o2.start(t0)
  const stopAt = t0 + dur + 0.01
  o1.stop(stopAt)
  o2.stop(stopAt)
  o1.onended = () => {
    try { o1.disconnect(); o2.disconnect(); g1.disconnect(); g2.disconnect(); lp.disconnect() } catch { /* noop */ }
  }
}

/** 刻度音：低沉、短、起音偏软（力度越大低频越多）。 */
function playTick(strength) {
  const s = Math.max(0.35, Math.min(1, strength))
  playHit({ f0: 640, f1: 330, dur: 0.042, peak: 0.2 * s + 0.06, body: 0.62, cut: 1000 })
}

/** 按钮音：比刻度更钝一点，避免连点时"嗒嗒嗒"很吵。scale 用来在"已震到"时压低音量。 */
let lastSoftAt = 0
function softClick(scale = 1) {
  const now = nowMs()
  if (now - lastSoftAt < 40) return
  lastSoftAt = now
  playHit({ f0: 520, f1: 290, dur: 0.055, peak: 0.15 * scale, body: 0.72, cut: 780 })
}

/* ============================ 震动 ============================ */

/* 连续失败几次就认定「这台设备震不了」，之后不再白调 —— 省得每帧调一次
   无效 API，也让我们能立刻切到声音兜底。iOS Safari 连 vibrate 都不存在，
   第一次调用就计入失败。 */
let vibFails = 0
let vibrateBroken = false

/**
 * 调一次振动，返回**是否真的震到了**。
 *
 * `navigator.vibrate()` 的返回值就是判定依据：返回 false = 没硬件 / 没权限 /
 * 页面没有用户激活。这是唯一能在前端探到的信号（不像摄像头有权限查询接口）。
 */
function vibrate(pattern) {
  if (!enabled) return false
  if (vibrateBroken) return false
  try {
    if (typeof navigator === 'undefined' || typeof navigator.vibrate !== 'function') {
      vibrateBroken = true
      return false
    }
    const ok = navigator.vibrate(pattern)
    if (ok === false) {
      vibFails += 1
      // 阈值 3：首次滑动时页面可能还没"用户激活"，Chrome 会给 false，
      // 直接判死会误伤 —— 连续三次都不行才是真不支持
      if (vibFails >= 3) vibrateBroken = true
      return false
    }
    vibFails = 0
    return true
  } catch {
    vibrateBroken = true
    return false
  }
}

/** 供「个人中心 → 试一下」展示用：这台设备当前能不能震。 */
export function vibrationAvailable() {
  return !vibrateBroken && typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function'
}

function fire(pattern) {
  lastFireAt = nowMs()
  vibrate(pattern)
}

/* ============================ 分级 API（旧调用点保持不变） ============================ */

export const haptic = {
  light: () => fire(12),
  medium: () => fire(22),
  heavy: () => fire(38),
  /** 双击节奏：成功提示（配合视觉成功态） */
  success: () => fire([12, 40, 16]),
  /** 三段急促：错误/警告 */
  error: () => fire([12, 30, 12, 30, 16]),
}

/** 只震不响（老名字）。 */
export function buzz(ms = 12) {
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
    // 组件自己刚发过反馈（同一事件的冒泡里）→ 不再重复震
    const already = nowMs() - lastFireAt < TAP_DEDUPE_MS
    const vibrated = already ? false : vibrate(TAP_MS)

    /* 触摸设备上一律再补一声很轻的「咔」：
       v2.46.324 夜星反馈"手指没感受到"，而 navigator.vibrate 在
       华为/鸿蒙浏览器里可能"存在但静默 no-op"（返回 true 也不震），
       前端没有任何办法识别。所以声音必须是**常开**的兜底，
       震到了是"声 + 震"（iOS 键盘那种质感），震不到至少还有一下触感错觉。
       音量按是否震到分两档：震到了就压到 0.6，避免叠得太满。
       ⚠️ 仍然限定触摸设备 —— 桌面 Firefox/Safari 没 vibrate，
          按鼠标也响会变成满屏点击音。 */
    if (isTouchDevice()) softClick(vibrated ? 0.6 : 1)
  }

  document.addEventListener('click', onClick, { passive: true })
  return () => {
    document.removeEventListener('click', onClick)
    tapBound = false
  }
}

/* ============================ 全站滑杆刻度 ============================ */

let rangeBound = false

/**
 * 全站 `<input type="range">` 的刻度反馈 —— document 级 input 委托。
 *
 * 为什么不在每个工具页写 `@input="stepTick"`：全站 10 个滑杆散在 6 个文件里
 * （压缩质量/证件照缩放与容差/密码长度/二维码尺寸/弹幕字号与速度/转盘权重），
 * 逐个改既容易漏，又会被后续新页面忘掉。委托一次覆盖全部，含动态插入的。
 *
 * @returns {() => void} 解绑
 */
export function installRangeTicks() {
  if (rangeBound || typeof document === 'undefined') return () => {}
  rangeBound = true
  const onInput = (e) => {
    const el = e.target
    if (!el || el.tagName !== 'INPUT' || el.type !== 'range') return
    stepTick(e)
  }
  document.addEventListener('input', onInput, { passive: true })
  return () => {
    document.removeEventListener('input', onInput)
    rangeBound = false
  }
}
