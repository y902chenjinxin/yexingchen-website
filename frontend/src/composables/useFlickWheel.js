/**
 * 物理惯性转盘（v2.46.330）—— 手指拖拽 + 阻尼惯性 + 精准吸附 + Canvas 火花粒子。
 *
 * 为什么不用 CSS transition：
 *   拖拽要"手指到哪盘到哪"，必须每帧直接写 transform；一旦有 transition，
 *   拖拽会带 4.2s 的尾巴，完全跟不上手指。所以整套交给 rAF 逐帧驱动。
 *
 * 为什么判定用"角度"而不是"位移"：
 *   手指绕圆心转 30° 在小盘上是 40px，在大盘上是 80px。用角度算，
 *   半径不同的设备手感一致；用位移算，平板上一转就飞出去。
 *
 * 🔴 三条硬规则（踩过就知道）：
 *   1. 速度必须按"角度差 / 时间差"算，且只取最后 110ms 的样本 ——
 *      取全程会被起手那下的停顿拉低，松手后转不起来。
 *   2. 阻尼必须乘 `pow(0.985, dt*60)` 而不是每帧固定乘 0.985 ——
 *      120Hz 屏每帧乘一次 = 衰减速度快一倍，"同样的手速，iPad 上转两圈，手机转五圈"。
 *   3. 吸附的落点由**指针当前所在的扇区**决定（不是重新随机）——
 *      手指停下时指针指着哪块就落哪块，这样"我能控制落点"的手感才成立。
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const D2R = Math.PI / 180

/** 角速度硬上限（deg/s）。约 4.2 圈/秒，再快就看不清扇区、只剩糊影。 */
const MAX_SPEED = 1500
/** 每 1/60 秒保留的速度比例（0.985 ≈ 3.6 秒衰减到 5%）。 */
const DAMPING = 0.985
/** 低于这个角速度就放弃惯性，进入吸附（deg/s）。 */
const MIN_SPEED = 46
/** 惯性最长持续时间，到点强制收尾。 */
const MAX_SPIN_MS = 5000
/** 累计转动小于这个角度、且时间很短 → 视为"点了一下"（防误触）。 */
const TAP_DEG = 5
const TAP_MS = 420
/** 出火花的角速度门槛。 */
const FX_SPEED = 260

const mod = (v, m) => ((v % m) + m) % m
const clamp = (v, a, b) => Math.max(a, Math.min(b, v))

export function useFlickWheel({ wheelRef, canvasRef, getSpans, onSettle, onHint, onCross }) {
  /** 当前旋转角（度，顺时针为正，累积值，可能上千）。 */
  const rot = ref(0)
  /** 惯性 / 吸附 / 脚本旋转进行中 —— 期间禁止再次拖拽。 */
  const spinning = ref(false)
  const dragging = ref(false)
  /** 高速态（给 CSS 加发光环）。 */
  const fast = ref(false)
  const speed = ref(0)

  /* 旋转用**命令式**写 style.transform，不走 Vue 的 style 绑定：
     60fps 改一个 ref 会让整个组件重渲染（含一串扇区标签 vnode），
     而 transform 只需要一次 DOM 属性写入。rot 仍然保留成 ref，
     是为了切签组/重置时能直接把它归零。 */
  function applyTransform() {
    const el = wheelRef.value
    if (el) el.style.transform = `rotate(${rot.value}deg)`
  }
  watch(rot, applyTransform, { flush: 'sync' })

  let mode = ''          // '' | 'inertia' | 'ease' | 'snap'
  let vel = 0            // deg/s，带符号
  let rafId = 0
  let lastT = 0
  let startedAt = 0
  let lastIdx = -1

  /* ---------- 脚本缓动（GO 按钮 / 吸附共用一套 easeOutCubic） ---------- */
  let easeFrom = 0
  let easeDist = 0
  let easeDur = 0
  let easeT0 = 0

  /* ---------- 拖拽状态 ---------- */
  let cx = 0
  let cy = 0
  let lastAngle = 0
  let startT = 0
  let moved = 0
  const samples = []     // [{t, r}]

  /* ---------- 粒子 ---------- */
  const particles = []
  let ctx = null
  let cw = 0
  let ch = 0
  let emitAcc = 0
  let reduceMotion = false
  const PALETTE = ['#ffe9a8', '#ffd274', '#ffb04a', '#ff8a3d', '#ff6b3d']
  const GRAVITY = 340

  /* ============================ 几何 ============================ */

  /** 各扇区跨度（度），合计 360。 */
  function spans() {
    const s = (getSpans() || []).filter((n) => Number.isFinite(n) && n > 0)
    return s.length ? s : [360]
  }
  /** 各扇区中线角度（从正上方顺时针算）。 */
  function mids() {
    const out = []
    let acc = 0
    for (const s of spans()) {
      out.push(acc + s / 2)
      acc += s
    }
    return out
  }
  function idxAt(angle) {
    const sp = spans()
    let acc = 0
    for (let i = 0; i < sp.length; i++) {
      if (angle < acc + sp[i]) return i
      acc += sp[i]
    }
    return sp.length - 1
  }
  /** 指针（正上方）现在指着第几块。 */
  function segUnderPointer() {
    return idxAt(mod(-rot.value, 360))
  }

  function emitCross() {
    const i = segUnderPointer()
    if (i === lastIdx) return
    lastIdx = i
    onCross?.(i)
  }

  /* ============================ 粒子：Canvas ============================ */

  function resizeCanvas() {
    const c = canvasRef.value
    if (!c) return
    const r = c.getBoundingClientRect()
    if (!r.width || !r.height) return
    // 高分屏：先把画布像素放大到 dpr 倍，再用 setTransform 把坐标系换回 CSS 像素，
    // 这样绘制代码里不用到处乘 dpr，也不会在 2x/3x 屏上发虚。
    const dpr = Math.min(3, window.devicePixelRatio || 1)
    cw = r.width
    ch = r.height
    c.width = Math.round(cw * dpr)
    c.height = Math.round(ch * dpr)
    ctx = c.getContext('2d')
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  /** 按"当前角速度"决定这一帧撒几颗火星：速度越高越密，且封顶防糊屏。 */
  function spawn(dt, v) {
    if (!ctx || reduceMotion) return
    if (v < FX_SPEED) return
    const R = (Math.min(cw, ch) / 2) * 0.955
    const rate = Math.min(110, 6 + ((v - FX_SPEED) / 900) * 74)
    emitAcc += rate * dt
    const dir = v >= 0 ? 1 : -1
    while (emitAcc >= 1) {
      emitAcc -= 1
      if (particles.length >= 260) break
      const th = Math.random() * Math.PI * 2
      const x = cw / 2 + Math.sin(th) * R
      const y = ch / 2 - Math.cos(th) * R
      // 甩出去的方向 = 径向向外 + 切向（跟转盘同向）的拖拽感
      const out = 70 + Math.random() * 210 * Math.min(1, v / 1100)
      const tang = v * 0.075 * dir
      particles.push({
        x,
        y,
        vx: Math.sin(th) * out + Math.cos(th) * tang,
        vy: -Math.cos(th) * out + Math.sin(th) * tang,
        life: 0.38 + Math.random() * 0.3,
        age: 0,
        size: 0.9 + Math.random() * 1.9,
        c: PALETTE[(Math.random() * PALETTE.length) | 0],
      })
    }
  }

  function stepParticles(dt) {
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i]
      p.age += dt
      if (p.age >= p.life) {
        particles.splice(i, 1)
        continue
      }
      p.vy += GRAVITY * dt
      p.vx *= 0.985
      p.x += p.vx * dt
      p.y += p.vy * dt
    }
  }

  function draw() {
    if (!ctx) return
    ctx.clearRect(0, 0, cw, ch)
    if (reduceMotion) return

    // 高速时的外缘光轨：一条随速度加深的金色细环
    if (speed.value > FX_SPEED) {
      const R = (Math.min(cw, ch) / 2) * 0.94
      ctx.globalAlpha = Math.min(0.3, speed.value / 3200)
      ctx.strokeStyle = '#ffd48a'
      ctx.lineWidth = 2.2
      ctx.beginPath()
      ctx.arc(cw / 2, ch / 2, R, 0, Math.PI * 2)
      ctx.stroke()
    }

    for (const p of particles) {
      const a = 1 - p.age / p.life
      ctx.globalAlpha = a * 0.55
      ctx.fillStyle = p.c
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size * 2.1, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalAlpha = a
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalAlpha = 1
  }

  /* ============================ 主循环 ============================ */

  function ensure() {
    if (rafId) return
    lastT = performance.now()
    rafId = requestAnimationFrame(loop)
  }

  function loop(now) {
    rafId = 0
    // dt 上限 50ms：切后台/切标签回来时 now 会跳几百毫秒，
    // 不限的话那一帧转盘直接飞出去半圈，还撒出一屏火花。
    const dt = clamp((now - lastT) / 1000, 0.001, 0.05)
    lastT = now

    if (mode === 'inertia') {
      vel *= Math.pow(DAMPING, dt * 60)
      rot.value += vel * dt
      speed.value = Math.abs(vel)
      emitCross()
      spawn(dt, vel)
      if (Math.abs(vel) < MIN_SPEED || now - startedAt > MAX_SPIN_MS) beginSnap()
    } else if (mode === 'ease' || mode === 'snap') {
      const t = Math.min(1, (now - easeT0) / easeDur)
      const inv = 1 - t
      rot.value = easeFrom + easeDist * (1 - inv * inv * inv)
      // 导数 = 3·dist·(1-t)²/时长，用来决定还要不要撒火花
      const vNow = (easeDist * 3 * inv * inv) / (easeDur / 1000)
      speed.value = Math.abs(vNow)
      emitCross()
      if (mode === 'ease') spawn(dt, vNow)
      if (t >= 1) finish()
    }

    fast.value = speed.value > FX_SPEED
    stepParticles(dt)
    draw()

    if (mode !== '' || particles.length) {
      rafId = requestAnimationFrame(loop)
    } else {
      speed.value = 0
      fast.value = false
      emitAcc = 0
    }
  }

  /* ============================ 吸附 ============================ */

  /**
   * 从当前角度出发，让"指针所在扇区的中线"转到正上方。
   * 落点由当前位置决定（不重新随机），所以手指停在哪，结果就是哪。
   */
  function beginSnap() {
    const a = mod(-rot.value, 360)
    const i = idxAt(a)
    const sp = spans()
    const span = sp[i] || 60
    const mid = mids()[i] ?? 0

    /* 就近收尾：a 一定落在这个扇区内部，所以 a-mid 天然就在 ±span/2 之内，
       不用再取模。**不要**按转速方向再加一圈 —— 那样会滑进隔壁扇区，
       结果就跟"松手时指针压着的那块"不一致了（实测 6 段盘会偏一格）。
       物理上滚轮收尾本来也会往回轻顿一下，观感反而更真。 */
    let delta = a - mid
    delta = clamp(delta, -span / 2, span / 2)
    if (Math.abs(delta) < 0.4) delta = 0

    easeFrom = rot.value
    easeDist = delta
    // 走得多就多给点时间（300~620ms），但别拖成"慢动作"
    easeDur = 300 + Math.min(1, Math.abs(delta) / span) * 320
    easeT0 = performance.now()
    mode = 'snap'
    spinning.value = true
    ensure()
  }

  function finish() {
    mode = ''
    vel = 0
    speed.value = 0
    rot.value = mod(rot.value, 360)   // 把累积角收进 [0,360)：旋转 360° 视觉完全等价
    spinning.value = false
    onSettle?.(segUnderPointer())
  }

  /**
   * GO 按钮 / 键盘：按权重随机挑一块，然后强推 5 圈落到它正中。
   * 这不是"物理"，是"表演" —— 用户点 GO 期待的是仪式感，不是惯性。
   */
  function launchTo(idx) {
    const sp = spans()
    const span = sp[idx] || 60
    const mid = mids()[idx] ?? 0
    const jitter = (Math.random() - 0.5) * span * 0.5
    const target = -(mid + jitter)
    const delta = mod(target - rot.value, 360) + 360 * 5

    easeFrom = rot.value
    easeDist = delta
    easeDur = 3600
    easeT0 = performance.now()
    mode = 'ease'
    spinning.value = true
    vel = 0
    lastIdx = segUnderPointer()
    ensure()
  }

  /** 切签组/重置时用：停掉一切动画。 */
  function cancel() {
    mode = ''
    vel = 0
    speed.value = 0
    fast.value = false
    spinning.value = false
    particles.length = 0
    if (rafId) cancelAnimationFrame(rafId)
    rafId = 0
    draw()
  }

  /* ============================ 手势 ============================ */

  /** 光标的「相对圆心的角度」：正上方 = 0，顺时针为正。 */
  function angleAt(x, y) {
    return Math.atan2(x - cx, cy - y) / D2R
  }

  function onDown(e) {
    if (spinning.value) return                 // 惯性中还拖 → 直接忽略（防无限连转）
    if (e.pointerType === 'mouse' && e.button !== 0) return
    const el = wheelRef.value
    if (!el) return
    const r = el.getBoundingClientRect()
    cx = r.left + r.width / 2
    cy = r.top + r.height / 2

    dragging.value = true
    lastAngle = angleAt(e.clientX, e.clientY)
    startT = performance.now()
    moved = 0
    samples.length = 0
    samples.push({ t: startT, r: rot.value })
    lastIdx = segUnderPointer()

    // 不依赖 setPointerCapture：部分 WebView 上 capture 后 pointerup 会丢，
    // 改挂 window，手指滑出转盘范围也能正常收尾。
    window.addEventListener('pointermove', onMove, { passive: false })
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointercancel', onUp)
    e.preventDefault()
  }

  function onMove(e) {
    if (!dragging.value) return
    e.preventDefault()
    const a = angleAt(e.clientX, e.clientY)
    // 归一化到 (-180,180]：手指跨过 ±180° 那条线时角度会从 179 跳到 -179，
    // 不归一化的话转盘会在那一瞬间倒转一整圈。
    let d = ((a - lastAngle + 540) % 360) - 180
    lastAngle = a
    if (!d) return

    rot.value += d
    moved += Math.abs(d)

    const t = performance.now()
    samples.push({ t, r: rot.value })
    if (samples.length > 24) samples.shift()

    emitCross()

    const prev = samples[samples.length - 2]
    if (prev) {
      const inst = Math.abs(d) / Math.max(0.008, (t - prev.t) / 1000)
      if (inst > FX_SPEED) spawn(0.016, inst * Math.sign(d))
    }
    ensure()
  }

  function onUp() {
    if (!dragging.value) return
    dragging.value = false
    removeWin()

    const now = performance.now()
    // 防误触：只是点了一下（几乎没转、且很快松手）→ 提示，不转
    if (moved < TAP_DEG && now - startT < TAP_MS) {
      onHint?.()
      return
    }

    let v = estimateVel(now)
    v = clamp(v, -MAX_SPEED, MAX_SPEED)
    if (Math.abs(v) < 40) {
      // 慢慢推了一点就松手：不硬甩，直接吸附到最近的段（像机械旋钮的"咔"）
      vel = 0
      beginSnap()
      return
    }
    vel = v
    mode = 'inertia'
    spinning.value = true
    startedAt = now
    ensure()
  }

  /** 只取最后 110ms 的样本算速度：包含起手的停顿会让松手速度偏低很多。 */
  function estimateVel(now) {
    if (samples.length < 2) return 0
    const last = samples[samples.length - 1]
    let first = samples[0]
    for (let i = samples.length - 1; i >= 0; i--) {
      if (now - samples[i].t <= 110) first = samples[i]
      else break
    }
    const dt = (last.t - first.t) / 1000
    if (dt <= 0.002) return 0
    return (last.r - first.r) / dt
  }

  function removeWin() {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    window.removeEventListener('pointercancel', onUp)
  }

  /* ============================ 生命周期 ============================ */

  let ro = null
  let boundEl = null

  function onResize() {
    resizeCanvas()
  }

  /**
   * 绑定到当前 DOM 元素。
   * ⚠️ 必须可重入：这个页面用 `v-if="mode === 'play'"` 切"转盘 / 编辑"，
   * 切一次转盘元素就被销毁重建一次，只在 onMounted 里绑的话，
   * 从编辑页返回后转盘会**再也拖不动**（监听挂在已销毁的旧节点上）。
   */
  function bindEl() {
    const el = wheelRef.value
    if (boundEl && boundEl !== el) boundEl.removeEventListener('pointerdown', onDown)
    if (el && el !== boundEl) {
      el.addEventListener('pointerdown', onDown, { passive: false })
      applyTransform()
      ro?.disconnect()
      if (typeof ResizeObserver !== 'undefined') {
        ro = new ResizeObserver(onResize)
        ro.observe(el)
      }
    }
    boundEl = el || null
    if (canvasRef.value) resizeCanvas()
  }

  onMounted(() => {
    reduceMotion = typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    bindEl()
    window.addEventListener('resize', onResize)
  })

  // DOM 元素换人（编辑 ↔ 转盘）时重新挂载监听与画布尺寸
  watch([wheelRef, canvasRef], bindEl, { flush: 'post' })

  onBeforeUnmount(() => {
    if (boundEl) boundEl.removeEventListener('pointerdown', onDown)
    removeWin()
    window.removeEventListener('resize', onResize)
    ro?.disconnect()
    cancel()
  })

  return { rot, spinning, dragging, fast, speed, launchTo, cancel, segUnderPointer }
}
