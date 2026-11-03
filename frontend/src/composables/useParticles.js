/**
 * 3D 粒子引擎（v2.46.347）
 *
 * ## 参考图的关键特征
 * 夜星给的三张图不是"圆点粒子"，而是**速度线**：
 *   · 每条粒子是一小段沿运动方向的线段（像曝光时的光轨）
 *   · 中心靠大量叠加过曝成白，外圈才显出红/绿/黄的色相
 *   · 纯黑底，没有背景图
 *
 * ## 为什么用 WebGL 而不是 Canvas 2D
 * 图里的密度是 12000 条级别。Canvas 2D 画一条线要 moveTo + lineTo + stroke，
 * 每次都要改 state，实测 2000 条就掉到 30fps。WebGL 一次 drawArrays 出全部，
 * 手机上 5000 条稳 60fps。
 *
 * ## 怎么用点精灵画线段
 * `gl.POINTS` 只能画方点，所以线段是在**片元着色器里算出来的**：
 * 把 [0,1] 的点内坐标转成 [-0.5,0.5]，沿粒子方向投影得 t、垂直方向得 d，
 * `|t| ≤ 0.5 且 |d| ≤ 线宽` 的地方着色 —— 等于在一个正方形里"刻"出一条胶囊。
 * 好处是每条粒子只需 1 个顶点（8 个 float），5000 条只有 160KB/帧。
 *
 * ## 加法混合
 * `blendFunc(ONE, ONE)`，密集区域自然叠加到 1.0 以上被裁成白色，
 * 这就是参考图里"中心白热、外圈有色"的成因，不需要额外画辉光层。
 */

const VERT = `
attribute vec2 a_pos;
attribute vec2 a_vel;
attribute vec3 a_color;
attribute float a_size;

uniform vec2 u_res;
uniform float u_dpr;

varying vec3 v_color;
varying vec2 v_dir;
varying float v_alpha;

void main() {
  // 像素坐标 → NDC；y 轴翻转（屏幕向下为正，GL 向上为正）
  vec2 clip = (a_pos / u_res) * 2.0 - 1.0;
  gl_Position = vec4(clip.x, -clip.y, 0.0, 1.0);
  gl_PointSize = a_size * u_dpr;

  v_color = a_color;
  // 方向也要翻 y，否则线段的朝向和运动方向镜像
  vec2 d = vec2(a_vel.x, -a_vel.y);
  float len = length(d);
  v_dir = len > 0.0001 ? d / len : vec2(1.0, 0.0);
  v_alpha = 1.0;
}
`

const FRAG = `
precision mediump float;

varying vec3 v_color;
varying vec2 v_dir;

uniform float u_width;   // 线宽占精灵的比例（0.06 ~ 0.5）

void main() {
  vec2 p = gl_PointCoord - 0.5;

  float t = dot(p, v_dir);                        // 沿方向的位置
  float d = abs(dot(p, vec2(-v_dir.y, v_dir.x))); // 垂直方向的距离

  // 胶囊两端收口 + 横向柔化。硬边会看出方块，柔化之后是"光轨"
  float along = smoothstep(0.5, 0.26, abs(t));
  float across = smoothstep(max(u_width, 0.02), max(u_width, 0.02) * 0.15, d);
  float a = along * across;

  if (a <= 0.004) discard;
  gl_FragColor = vec4(v_color * a, a);
}
`

/** 每颗粒子占的 float 数：x, y, vx, vy, r, g, b, size */
const STRIDE = 8

/** 配色预设。色相区间 + 饱和/亮度，值域按参考图调过 */
export const PALETTES = {
  // steps = 色相取几个固定档位。参考图里是「纯红 / 纯黄 / 纯绿」三个色块，
  // 不是连续渐变 —— 均匀随机取色相会糊成一片黄绿，三种颜色分不出来。
  neon: { name: '霓虹', hues: [176, 300], sat: [92, 100], light: [64, 78], steps: 3 },
  crystal: { name: '水晶', hues: [190, 262], sat: [42, 66], light: [80, 94], steps: 2 },
  // 0=红 60=黄 120=绿，正好对应参考图那三种
  nature: { name: '自然', hues: [0, 120], sat: [90, 100], light: [60, 74], steps: 3 },
}

export function createParticleEngine(canvas, options = {}) {
  const gl = canvas.getContext('webgl', {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    powerPreference: 'high-performance',
    // 默认 false（省一份缓冲区复制）。调试时页面带 ?debug=1 会置 true ——
    // 否则 WebGL 缓冲在 rAF 结束后就失效，`drawImage` / `readPixels` 取到的全是黑的，
    // 探针会误判成"没画出来"。
    preserveDrawingBuffer: !!options.debug,
  })
  if (!gl) return { ok: false, reason: 'no-webgl' }

  // ---------- shader ----------
  function compile(type, src) {
    const sh = gl.createShader(type)
    gl.shaderSource(sh, src)
    gl.compileShader(sh)
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(sh)
      gl.deleteShader(sh)
      throw new Error('shader: ' + log)
    }
    return sh
  }

  let prog
  try {
    prog = gl.createProgram()
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT))
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG))
    gl.linkProgram(prog)
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      throw new Error('link: ' + gl.getProgramInfoLog(prog))
    }
  } catch (e) {
    return { ok: false, reason: String(e.message || e) }
  }
  gl.useProgram(prog)

  const loc = {
    pos: gl.getAttribLocation(prog, 'a_pos'),
    vel: gl.getAttribLocation(prog, 'a_vel'),
    color: gl.getAttribLocation(prog, 'a_color'),
    size: gl.getAttribLocation(prog, 'a_size'),
    res: gl.getUniformLocation(prog, 'u_res'),
    dpr: gl.getUniformLocation(prog, 'u_dpr'),
    width: gl.getUniformLocation(prog, 'u_width'),
  }

  const buf = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buf)
  gl.enableVertexAttribArray(loc.pos)
  gl.enableVertexAttribArray(loc.vel)
  gl.enableVertexAttribArray(loc.color)
  gl.enableVertexAttribArray(loc.size)
  const B = STRIDE * 4
  gl.vertexAttribPointer(loc.pos, 2, gl.FLOAT, false, B, 0)
  gl.vertexAttribPointer(loc.vel, 2, gl.FLOAT, false, B, 8)
  gl.vertexAttribPointer(loc.color, 3, gl.FLOAT, false, B, 16)
  gl.vertexAttribPointer(loc.size, 1, gl.FLOAT, false, B, 28)

  gl.blendFunc(gl.ONE, gl.ONE)   // 加法混合：叠出白热
  gl.disable(gl.DEPTH_TEST)
  gl.clearColor(0, 0, 0, 1)

  // 部分设备的点大小上限很小（有的只到 64），超了会被裁剪、粒子看起来"长不大"
  const sizeRange = gl.getParameter(gl.ALIASED_POINT_SIZE_RANGE) || [1, 64]
  const MAX_POINT = Math.min(sizeRange[1] || 64, 512)

  // ---------- 可调参数 ----------
  const cfg = {
    count: 3200,
    size: 10.5,         // 基础粗细（px，会被速度放大）
    trail: 0.92,        // 拖尾系数：段长 = size * (1 + trail * k)
    // 0.055 才是"细光轨"。0.13 时线宽 2px 多，看起来是彩色小棒而不是光
    width: 0.055,
    palette: 'nature',
    invert: false,
    auto: false,        // 不按也自己喷
    ...options,
  }

  // ---------- 粒子池 ----------
  // 用扁平 Float32Array（struct of arrays 的更省内存，但写起来容易索引错）
  let cap = 0
  let data = null      // [x, y, vx, vy, r, g, b, size] * cap
  let life = null      // 剩余寿命（秒）
  let maxLife = null
  // 原始尺寸单独放：每帧的 size 是「原始尺寸 × 速度放大 × 将死缩小」算出来的，
  // 如果直接往 data 里乘，下一帧就会在上一次的结果上再乘，尺寸会雪球式失真。
  let baseSize = null
  let alive = 0        // 前 alive 个是活的（定期整理，避免空洞）
  let cw = 1
  let ch = 1
  let dpr = 1

  function ensureCap(n) {
    if (n === cap) return
    const old = data
    const oldLife = life
    const oldMax = maxLife
    const oldBase = baseSize
    const keep = Math.min(alive, n)
    data = new Float32Array(n * STRIDE)
    life = new Float32Array(n)
    maxLife = new Float32Array(n)
    baseSize = new Float32Array(n)
    if (old && keep > 0) {
      data.set(old.subarray(0, keep * STRIDE), 0)
      life.set(oldLife.subarray(0, keep))
      maxLife.set(oldMax.subarray(0, keep))
      baseSize.set(oldBase.subarray(0, keep))
    }
    alive = keep
    cap = n
  }

  function rand(a, b) {
    return a + Math.random() * (b - a)
  }

  /** 按配色取一个颜色。invert 时取补色，让黑底上换成另一套观感 */
  function pickColor(out) {
    const p = PALETTES[cfg.palette] || PALETTES.nature
    let h
    if (p.steps && p.steps > 1) {
      const k = Math.floor(Math.random() * p.steps)
      h = p.hues[0] + (k * (p.hues[1] - p.hues[0])) / (p.steps - 1)
      h += rand(-4, 4)      // 一点抖动，免得三色太生硬
    } else {
      h = rand(p.hues[0], p.hues[1])
    }
    if (cfg.invert) h = (h + 180) % 360
    const s = rand(p.sat[0], p.sat[1])
    const l = rand(p.light[0], p.light[1])
    // HSL → RGB（只算这一次，粒子生命周期内颜色不变）
    const c = (1 - Math.abs(2 * (l / 100) - 1)) * (s / 100)
    const hp = (h / 60) % 6
    const x = c * (1 - Math.abs((hp % 2) - 1))
    let r = 0, g = 0, b = 0
    if (hp < 1) [r, g, b] = [c, x, 0]
    else if (hp < 2) [r, g, b] = [x, c, 0]
    else if (hp < 3) [r, g, b] = [0, c, x]
    else if (hp < 4) [r, g, b] = [0, x, c]
    else if (hp < 5) [r, g, b] = [x, 0, c]
    else [r, g, b] = [c, 0, x]
    const m = l / 100 - c / 2
    out[0] = r + m
    out[1] = g + m
    out[2] = b + m
  }

  const _col = [0, 0, 0]

  /**
   * 发射一批粒子。
   * @param {number} x 像素 x
   * @param {number} y 像素 y
   * @param {number} n 数量
   * @param {object} o { speed, spread(弧度), angle(基准弧度), sizeMul, lifeRange }
   */
  function emit(x, y, n, o = {}) {
    const speed = o.speed ?? 260
    const spread = o.spread ?? Math.PI * 2
    const angle = o.angle ?? 0
    const sizeMul = o.sizeMul ?? 1
    const [l0, l1] = o.lifeRange || [0.55, 1.25]
    let left = Math.min(n, cap - alive)
    // 池满了就覆盖最老的（视觉上无感，比"不发射"好）
    if (left <= 0) {
      alive = Math.max(0, cap - n)
      left = Math.min(n, cap - alive)
    }
    for (let k = 0; k < left; k++) {
      const i = alive + k
      const a = angle + (Math.random() - 0.5) * spread
      // 速度用平方分布：慢的多、快的少，这样"芯"更密、外圈更长
      // 大多数是飞出去的光轨（rnd² 让慢速的多、快速的少）
      let sp = speed * (0.28 + Math.random() * Math.random() * 1.6)
      let lf = l0 + Math.random() * (l1 - l0)
      let szMul = 1
      let isCore = false
      /* 约 7% 是「芯」：几乎不动、更大、短命。
         参考图中心那团白热就是这种粒子叠出来的 —— 只靠飞出去的光轨，
         中心永远是空的（粒子一发射就离开了）。加法混合下几十颗叠在一起就过曝成白。 */
      // 18%：参考图那团白热是"成千上万颗叠出来的"，只给 7% 根本叠不白
      // （实测 whitePct 一直是 0）。比例加大 + 速度再压低，让它们在发射点堆住。
      if (Math.random() < 0.18) {
        sp = rand(2, 32)
        lf = rand(0.2, 0.46)
        szMul = 2.0
        isCore = true
      }
      const off = i * STRIDE
      data[off] = x
      data[off + 1] = y
      data[off + 2] = Math.cos(a) * sp
      data[off + 3] = Math.sin(a) * sp
      /* 芯粒子强制近白。
         🔴 这里踩过一个坑：一开始让芯粒子也用配色色相，结果怎么叠都不白 ——
         加法混合下「红(255,0,0) + 绿(0,255,0) = 黄」，蓝通道永远是 0，
         数学上就出不来白色（实测 whitePct 恒为 0，maxV 已经到 625 但还是偏色）。
         参考图中心那团白热，本质是过曝，得让芯粒子自己带满三通道。 */
      if (isCore) {
        _col[0] = 1
        _col[1] = 0.97
        _col[2] = 0.93
      } else {
        pickColor(_col)
      }
      data[off + 4] = _col[0]
      data[off + 5] = _col[1]
      data[off + 6] = _col[2]
      baseSize[i] = cfg.size * sizeMul * szMul * (0.6 + Math.random() * 0.9)
      data[off + 7] = baseSize[i]
      life[i] = lf
      maxLife[i] = lf
    }
    alive += left
  }

  function resize(w, h) {
    cw = Math.max(1, Math.floor(w))
    ch = Math.max(1, Math.floor(h))
    // DPR 封顶 2：3x 屏上画布是 1080×2400，像素填充率直接翻倍，手机上会烫
    dpr = Math.min(2, window.devicePixelRatio || 1)
    canvas.width = Math.floor(cw * dpr)
    canvas.height = Math.floor(ch * dpr)
    canvas.style.width = cw + 'px'
    canvas.style.height = ch + 'px'
    gl.viewport(0, 0, canvas.width, canvas.height)
    gl.uniform2f(loc.res, cw, ch)
    gl.uniform1f(loc.dpr, dpr)
  }

  /** 把已经在飞的粒子按当前配色重算颜色 —— 否则改配色后要等旧的死光才看见效果 */
  function recolor() {
    for (let i = 0; i < alive; i++) {
      const off = i * STRIDE
      pickColor(_col)
      data[off + 4] = _col[0]
      data[off + 5] = _col[1]
      data[off + 6] = _col[2]
    }
  }

  function applyOptions(patch) {
    if (!patch) return
    Object.assign(cfg, patch)
    if (patch.width != null) gl.uniform1f(loc.width, Math.max(0.02, Math.min(0.5, cfg.width)))
    if (patch.count != null) ensureCap(Math.max(64, Math.min(8000, Math.round(cfg.count))))
    // 配色/反转变了立刻重算（参数面板点一下就该看到变化，而不是等两秒）
    if (patch.palette != null || patch.invert != null) recolor()
  }

  /** 物理步进。dt 秒。 */
  function step(dt) {
    // 0.925：粒子能飞满屏。0.86 在一秒内几乎停住，看起来是「原地冒烟」而不是
    // 「光射出去」（第一版就是 0.86，太稀、太短）。
    const drag = Math.pow(0.925, dt * 60)
    const growK = cfg.trail * 3.0
    let w = 0
    for (let i = 0; i < alive; i++) {
      const off = i * STRIDE
      life[i] -= dt
      if (life[i] <= 0 || data[off] < -240 || data[off] > cw + 240 ||
          data[off + 1] < -240 || data[off + 1] > ch + 240) {
        continue   // 死了或飞出屏幕：跳过，下面会把活着的压缩到前面
      }
      data[off] += data[off + 2] * dt
      data[off + 1] += data[off + 3] * dt
      data[off + 2] *= drag
      data[off + 3] *= drag
      data[off + 3] += 26 * dt          // 一点重力，飘散时落下去更自然

      const sp = Math.hypot(data[off + 2], data[off + 3])
      const t = life[i] / maxLife[i]
      // 段长 = 原始尺寸 × 速度放大 × 将死收缩。
      // 速度放大部分就是参考图里"速度线"的来源：飞得快 = 拉得长。
      const grow = 1 + Math.min(2.4, (sp / 420) * growK)
      const fade = t < 0.28 ? 0.35 + (t / 0.28) * 0.65 : 1
      const sz = Math.min(MAX_POINT, baseSize[i] * grow * fade)

      if (w !== i) {
        const to = w * STRIDE
        for (let k = 0; k < STRIDE; k++) data[to + k] = data[off + k]
        life[w] = life[i]
        maxLife[w] = maxLife[i]
        baseSize[w] = baseSize[i]
      }
      data[w * STRIDE + 7] = sz
      w++
    }
    alive = w
  }

  function draw() {
    gl.clear(gl.COLOR_BUFFER_BIT)
    if (!alive) {
      gl.drawArrays(gl.POINTS, 0, 0)
      return
    }
    gl.bufferData(gl.ARRAY_BUFFER, data.subarray(0, alive * STRIDE), gl.DYNAMIC_DRAW)
    gl.drawArrays(gl.POINTS, 0, alive)
  }

  // 初始分配 + 默认线宽（applyOptions 只在"改设置"时跑，首帧不能靠它）
  ensureCap(Math.max(64, Math.min(8000, Math.round(cfg.count))))
  gl.uniform1f(loc.width, Math.max(0.02, Math.min(0.5, cfg.width)))

  function dispose() {
    try {
      gl.deleteBuffer(buf)
      gl.deleteProgram(prog)
      gl.getExtension('WEBGL_lose_context')?.loseContext()
    } catch { /* ignore */ }
  }

  return {
    ok: true,
    cfg,
    emit,
    resize,
    applyOptions,
    step,
    draw,
    dispose,
    get alive() { return alive },
    get maxPoint() { return MAX_POINT },
    clear() { alive = 0 },
  }
}
