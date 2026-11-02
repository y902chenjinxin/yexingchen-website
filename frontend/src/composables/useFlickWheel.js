/**
 * 物理惯性转盘（v2.46.330 / v2.46.331 改「变速自行车」手感）
 * —— 手指拖拽 + 飞轮蓄力 + 长惯性 + 精准吸附 + Canvas 火花粒子。
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

/** 角速度硬上限（deg/s）。约 5 圈/秒，再快就看不清扇区、只剩糊影。 */
const MAX_SPEED = 1800
/**
 * 指数衰减系数（1/秒）：`v *= exp(-K·dt)`。
 *
 * 夜星要「变速自行车」：蹬起来松手能溜很久。v2.46.332 把上限收到 15 秒，
 * 所以 K 从 0.135 提到 0.255：满速 1800 掉到 40 要 ln(45)/0.255 ≈ 15 秒。
 * K 越小溜得越久，但太小会变成永动机。
 */
const SLOW_K = 0.255
/**
 * 弱推的衰减更狠一点。
 *
 * 纯指数衰减的时长只随初速**对数**变化：固定一个 K 的话，轻轻一拨也会溜十几秒，
 * 那就不像自行车了。K 随初速线性插值后：
 *   · 满速 1800 → K=0.255 → 约 15 秒
 *   · 中等 900  → K=0.34  → 约 9 秒
 *   · 轻推 300  → K=0.42  → 约 5 秒
 */
const SLOW_K_WEAK = 0.42
/** 低于这个角速度就放弃惯性，进入吸附（deg/s）。 */
const MIN_SPEED = 40
/** 惯性最长持续时间，到点强制收尾（夜星要求的上限：v2.46.332 从 30s 收到 15s）。 */
const MAX_SPIN_MS = 15000

/* ---------- 飞轮「变速」参数 ----------
 * 前期慢、越转越快：齿轮比 gear 从 0.55 起步（比手指慢，像刚起步踩不动），
 * 持续转就往上充能到 2.8（轮子比手指转得快，像挂上高速档）。
 * 一停手就掉档，反向立刻回 1 —— 不然反向那一下会迟钝得像灌了铅。 */
const GEAR_START = 0.55
const GEAR_MAX = 2.8
/** 充能速率：手指 900°/s 时约 2.2 秒挂到最高档。 */
const GEAR_GAIN = 2.2
/** 掉档速率（1/秒）。 */
const GEAR_FALL = 0.9
/** 松手时把手指速度放大一点，接到齿轮比上（飞轮比手快是应该的）。 */
const RELEASE_BOOST = 1.08
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
  let gear = 1           // 飞轮齿轮比（拖拽期）
  let decayK = SLOW_K    // 本次松手用的衰减系数
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
  let lastSampleT = 0
  let lastDir = 0
  let moved = 0
  const samples = []     // [{t, r}]

  /* ---------- 粒子 ---------- */
  const particles = []
  let ctx = null
  let cw = 0
  let ch = 0
  let rimR = 0            // 转盘半径（火花从这里往外飞）
  let emitAcc = 0
  let reduceMotion = false
  const GRAVITY = 320
  /** 发光精灵：预渲染三档色温的小圆图，绘制时用 drawImage 缩放。
   *  比每帧 arc()+shadowBlur 快一个量级，也比纯色圆点"有质感"得多。 */
  let sprites = []

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

  function emitCross(v = 0) {
    const i = segUnderPointer()
    if (i === lastIdx) return
    lastIdx = i
    onCross?.(i, v)   // 带上当前角速度：转得飞快时上层不该每格都「哒」
  }

  /* ============================ 粒子：Canvas ============================ */

  /**
   * 画布尺寸用 JS 按轮径算死，不用 CSS 百分比。
   *
   * 🔴 踩过：`.sp-fx { width: 152%; height: 152% }` 被全局
   * `@media(max-width:768px){ .island-inner-tool canvas { max-width:100% } }` 压住 ——
   * 宽度被砍回 100%、高度仍是 152%，画布变成 300×456 的竖条，
   * 圆心从 (150,150) 跑到 (72,150)，于是"光圈歪了、没对上转盘"。
   * 现在宽高/位置一律写 px，并给 `.sp-fx` 加 max-width:none 兜底。
   */
  function resizeCanvas() {
    const c = canvasRef.value
    const w = wheelRef.value
    if (!c || !w) return
    const r = w.getBoundingClientRect()
    if (!r.width) return

    const box = Math.round(r.width * 1.5)   // 画布 = 轮径 × 1.5，给火花飞出盘外的余量
    cw = ch = box
    rimR = r.width / 2
    c.style.width = box + 'px'
    c.style.height = box + 'px'
    c.style.left = Math.round((r.width - box) / 2) + 'px'
    c.style.top = Math.round((r.height - box) / 2) + 'px'

    // 高分屏：缓冲放大 dpr 倍，再用 setTransform 把坐标系换回 CSS 像素，
    // 绘制代码里不用到处乘 dpr，也不会在 2x/3x 屏上发虚。
    const dpr = Math.min(3, window.devicePixelRatio || 1)
    c.width = Math.round(box * dpr)
    c.height = Math.round(box * dpr)
    ctx = c.getContext('2d')
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    if (!sprites.length) sprites = buildSprites()
  }

  /** 三档色温的发光精灵：白炽芯 / 鎏金 / 琥珀 */
  function buildSprites() {
    const make = (inner, mid) => {
      const S = 64
      const cv = document.createElement('canvas')
      cv.width = S
      cv.height = S
      const g = cv.getContext('2d')
      const rg = g.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2)
      rg.addColorStop(0, inner)
      rg.addColorStop(0.18, mid)
      rg.addColorStop(0.45, mid.replace(/[\d.]+\)$/, '0.25)'))
      rg.addColorStop(1, 'rgba(255,180,80,0)')
      g.fillStyle = rg
      g.fillRect(0, 0, S, S)
      return cv
    }
    return [
      make('rgba(255,255,255,1)', 'rgba(255,246,214,1)'),
      make('rgba(255,247,222,1)', 'rgba(255,206,110,1)'),
      make('rgba(255,214,150,1)', 'rgba(255,150,64,1)'),
    ]
  }

  /** 按"当前角速度"决定这一帧撒几颗火星：速度越高越密，且封顶防糊屏。 */
  function spawn(dt, v) {
    if (!ctx || reduceMotion || !rimR) return
    const sp = Math.abs(v)
    if (sp < FX_SPEED) return
    const rate = Math.min(170, 12 + ((sp - FX_SPEED) / 700) * 128)
    emitAcc += rate * dt
    const dir = v >= 0 ? 1 : -1
    while (emitAcc >= 1) {
      emitAcc -= 1
      if (particles.length >= 260) break
      const th = Math.random() * Math.PI * 2
      const rr = rimR * (0.97 + Math.random() * 0.03)
      const x = cw / 2 + Math.sin(th) * rr
      const y = ch / 2 - Math.cos(th) * rr
      // 甩出去的方向 = 径向向外 + 切向（跟转盘同向）的拖拽感
      const out = 40 + Math.random() * 190 * Math.min(1, sp / 1200)
      const tang = sp * 0.05 * dir
      particles.push({
        x,
        y,
        vx: Math.sin(th) * out + Math.cos(th) * tang,
        vy: -Math.cos(th) * out + Math.sin(th) * tang,
        life: 0.55 + Math.random() * 0.6,   // 长一点才看得到"飞出去"的轨迹
        age: 0,
        size: 7 + Math.random() * 13,       // 精灵绘制边长（px），大一点才"发光"
        sp: sprites[(Math.random() * 3) | 0],
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
      p.vx *= 0.975
      p.vy *= 0.995
      p.x += p.vx * dt
      p.y += p.vy * dt
    }
  }

  function draw() {
    if (!ctx) return
    ctx.clearRect(0, 0, cw, ch)
    if (reduceMotion) return

    const cx0 = cw / 2
    const cy0 = ch / 2

    /* 光轨：一圈随速度加深的细环 + 一段跟着转的亮弧。
       都是"加法混合"，所以叠在深色盘上会自然发光，不会像描边。 */
    const sp = speed.value
    if (sp > 120 && rimR) {
      const k = Math.min(1, (sp - 120) / 1400)
      ctx.globalCompositeOperation = 'lighter'
      ctx.globalAlpha = 0.08 + k * 0.28
      ctx.strokeStyle = '#ffdca0'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(cx0, cy0, rimR + 3, 0, Math.PI * 2)
      ctx.stroke()

      // 亮弧跟着转盘走：读的是 rot，所以视觉上"贴"在盘沿一起扫
      const head = (mod(-rot.value, 360) - 90) * D2R
      ctx.globalAlpha = 0.16 + k * 0.58
      ctx.lineWidth = 5
      ctx.lineCap = 'round'
      const grd = ctx.createLinearGradient(
        cx0 + Math.cos(head - 0.9) * rimR, cy0 + Math.sin(head - 0.9) * rimR,
        cx0 + Math.cos(head) * rimR, cy0 + Math.sin(head) * rimR,
      )
      grd.addColorStop(0, 'rgba(255,214,140,0)')
      grd.addColorStop(1, 'rgba(255,246,214,0.95)')
      ctx.strokeStyle = grd
      ctx.beginPath()
      ctx.arc(cx0, cy0, rimR + 3, head - 1.15, head)
      ctx.stroke()
      ctx.globalCompositeOperation = 'source-over'
    }

    /* 火花：发光精灵 + lighter 混合。每颗画两遍 —— 一遍拖尾、一遍本体，
       拖尾位置取上一帧的位移方向，看起来才是"飞出去"而不是"原地闪"。 */
    if (particles.length) {
      ctx.globalCompositeOperation = 'lighter'
      for (const p of particles) {
        const k = 1 - p.age / p.life
        const sz = p.size * (0.4 + k * 1.0)
        ctx.globalAlpha = k * 0.95
        const tx = p.x - p.vx * 0.014
        const ty = p.y - p.vy * 0.014
        ctx.globalAlpha = k * 0.5
        ctx.drawImage(p.sp, tx - sz * 0.6, ty - sz * 0.6, sz * 1.2, sz * 1.2)
        ctx.globalAlpha = k * 0.95
        ctx.globalAlpha = k * k * 1.0
        ctx.drawImage(p.sp, p.x - sz / 2, p.y - sz / 2, sz, sz)
      }
      ctx.globalCompositeOperation = 'source-over'
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
      // 🔴 按时间衰减（exp(-K·dt)），不是按帧。按帧的话 120Hz 屏衰减快一倍。
      vel *= Math.exp(-decayK * dt)
      rot.value += vel * dt
      speed.value = Math.abs(vel)
      emitCross(Math.abs(vel))
      spawn(dt, vel)
      if (Math.abs(vel) < MIN_SPEED || now - startedAt > MAX_SPIN_MS) beginSnap()
    } else if (mode === 'ease' || mode === 'snap') {
      const t = Math.min(1, (now - easeT0) / easeDur)
      const inv = 1 - t
      rot.value = easeFrom + easeDist * (1 - inv * inv * inv)
      // 导数 = 3·dist·(1-t)²/时长，用来决定还要不要撒火花
      const vNow = (easeDist * 3 * inv * inv) / (easeDur / 1000)
      speed.value = Math.abs(vNow)
      emitCross(Math.abs(vNow))
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
    lastSampleT = startT
    moved = 0
    // 每次按下都从低档起步：像刚踩上踏板，力气还没传过去
    gear = GEAR_START
    lastDir = 0
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
    const t = performance.now()
    const a = angleAt(e.clientX, e.clientY)
    // 归一化到 (-180,180]：手指跨过 ±180° 那条线时角度会从 179 跳到 -179，
    // 不归一化的话转盘会在那一瞬间倒转一整圈。
    let d = ((a - lastAngle + 540) % 360) - 180
    lastAngle = a
    if (!d) return

    const dt = clamp((t - lastSampleT) / 1000, 0.008, 0.06)
    lastSampleT = t
    /** 手指自己的角速度（还没乘齿轮） */
    const finger = Math.abs(d) / dt

    /* ---------- 变速：一直转就挂高档 ----------
       反向时立刻回 1 档，否则往回转的头几十度会被齿轮比吃掉，手感像灌了铅。 */
    const dir = d > 0 ? 1 : -1
    if (lastDir && dir !== lastDir) gear = 1
    lastDir = dir
    if (finger > 80) gear = Math.min(GEAR_MAX, gear + (finger / 900) * GEAR_GAIN * dt)
    else gear = Math.max(GEAR_START, gear - GEAR_FALL * dt)

    // 轮子转过的角度 = 手指 × 齿轮比。gear>1 时轮子比手指快，就是"越来越快"。
    rot.value += d * gear
    moved += Math.abs(d)

    samples.push({ t, r: rot.value })
    if (samples.length > 24) samples.shift()

    const wheelSpeed = finger * gear
    emitCross(wheelSpeed)
    if (wheelSpeed > FX_SPEED) spawn(dt, wheelSpeed * dir)
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

    /* 注意：estimateVel 算的是 (rot 差 / 时间)，而 rot 在拖拽时已经乘过齿轮比了，
       所以这里拿到的是**轮子自己的**角速度，不能再乘一次 gear（会双计）。 */
    let v = clamp(estimateVel(now) * RELEASE_BOOST, -MAX_SPEED, MAX_SPEED)
    if (Math.abs(v) < 40) {
      // 慢慢推了一点就松手：不硬甩，直接吸附到最近的段（像机械旋钮的"咔"）
      vel = 0
      beginSnap()
      return
    }
    vel = v
    // 初速越高溜得越久（见 SLOW_K_WEAK 注释）
    const t = Math.min(1, Math.abs(v) / MAX_SPEED)
    decayK = SLOW_K + (SLOW_K_WEAK - SLOW_K) * (1 - t)
    mode = 'inertia'
    spinning.value = true
    startedAt = now
    ensure()
  }

  /** 只取最后 110ms 的样本算速度：把起手的停顿算进去会让松手速度偏低很多。 */
  function estimateVel(now) {
    if (samples.length < 2) return 0
    const last = samples[samples.length - 1]
    let first = samples[0]
    for (let i = samples.length - 1; i >= 0; i--) {
      if (now - samples[i].t <= 110) first = samples[i]
      else break
    }
    /* 窗口里只剩最后一个样本（手指停了一下才抬起）→ dt≈0 会算出 0，
       甩不出去。真实触摸里 pointerup 比最后一次 move 晚 100~200ms 很常见，
       所以退一步取倒数第二个样本，但**只在间隔 <250ms 时** ——
       真的停手超过 250ms 再松，就该判成"停住"，不许再甩。 */
    if (first === last) {
      const prev = samples[samples.length - 2]
      if (prev && now - last.t < 250) first = prev
      else return 0
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
