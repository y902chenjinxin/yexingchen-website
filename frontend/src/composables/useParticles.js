/**
 * 3D 粒子引擎（v2.46.354，「光晕」风格）
 *
 * ## 参考物换了
 * 之前照夜星给的三张图做成「速度线」（每条粒子是一小段曝光光轨）。他看到
 * 「魔幻粒子3D」这个 App 后说「尺寸颜色特效挺合我心意的」，于是照它的渲染管线重做。
 *
 * ## 逆向出来的管线（assets/ 下的 .frag 是明文，apk 里直接能读）
 *   1. 粒子画进一张**半分辨率**的 paint 缓冲，加法混合 → 密集处自然过曝成白
 *      （PaintResolveLow.frag 里的 `magn = clamp((maxComp-1.0)*0.25, 0, 1)` 就是这个意思）
 *   2. 这张缓冲再做一次**可分离高斯模糊**（BlurHor/BlurVert.frag，17 抽头，权重 0.05~0.16）
 *   3. 合成时 `color += 1.5 × 模糊图`（glow_active / FluidTrippyGlow 里分别是 1.5 / 2.0）
 *   4. 最后 `smoothstep(0.0, 1.0)`（cmode_additive / FluidRegularDetail 都有这一句）
 *      —— 这是整张图「柔、有体积、不像霓虹管」的真正原因
 *   5. 粒子贴图 textures/glow.png：64×64，**没有硬芯**，亮度按高斯衰减，
 *      实测 r/R=0.5 处还有 0.47 亮度、0.875 处 0.075 → sigma≈0.41R
 *
 * ## 尺寸为什么比以前大一倍
 * 以前 size=10.5 是「一条光轨的横截面」，现在 size 是「一团光斑的直径」。
 * 参考 App 里 blobs 的直径约等于屏幕短边的 1/18，3200 颗叠在一起才成团。
 * 所以默认 18px + 半分辨率缓冲 + 模糊，观感对得上。
 *
 * ## 代价
 * 多 3 张半分辨率纹理 + 4 个全屏 pass。1080×2400 的屏上模糊层只有 540×1200，
 * 手机上实测仍稳 60fps；真机掉帧就调低 `bloom`（0 直接关掉整个后处理）。
 */

const VERT = `
attribute vec2 a_pos;
attribute vec2 a_vel;
attribute vec3 a_color;
attribute float a_size;

uniform vec2 u_res;
uniform float u_scale;   // 画到屏幕用 dpr，画到半分辨率缓冲用 dpr/2

varying vec3 v_color;
varying vec2 v_dir;
varying float v_sp;

void main() {
  // 像素坐标 → NDC；y 轴翻转（屏幕向下为正，GL 向上为正）
  vec2 clip = (a_pos / u_res) * 2.0 - 1.0;
  gl_Position = vec4(clip.x, -clip.y, 0.0, 1.0);
  gl_PointSize = a_size * u_scale;

  v_color = a_color;
  // 方向也要翻 y，否则线段的朝向和运动方向镜像
  vec2 d = vec2(a_vel.x, -a_vel.y);
  float len = length(d);
  v_dir = len > 0.0001 ? d / len : vec2(1.0, 0.0);
  v_sp = len;
}
`

/** 光晕：两瓣高斯（紧芯 + 宽晕），宽晕那瓣的 sigma 对齐参考 App 的 glow.png */
const FRAG_GLOW = `
precision mediump float;

varying vec3 v_color;
varying vec2 v_dir;
varying float v_sp;

uniform float u_width;

void main() {
  vec2 p = gl_PointCoord - 0.5;
  float r2 = dot(p, p) * 4.0;          // 0（中心）~ 1（精灵边缘）
  if (r2 > 1.0) discard;

  float core = exp(-r2 * 14.0);         // 紧芯
  float halo = exp(-r2 * 3.0);          // 宽晕，exp(-0.25*3)=0.47 对上参考贴图
  float a = core * 0.22 + halo * 0.19;  // 峰值 0.41：单颗只是一片光，叠几颗才白

  gl_FragColor = vec4(v_color * a, a);
}
`

/** 光轨：老的胶囊形状（保留，可在设置里切回来） */
const FRAG_STREAK = `
precision mediump float;

varying vec3 v_color;
varying vec2 v_dir;

uniform float u_width;

void main() {
  vec2 p = gl_PointCoord - 0.5;

  float t = dot(p, v_dir);                        // 沿方向的位置
  float d = abs(dot(p, vec2(-v_dir.y, v_dir.x))); // 垂直方向的距离

  float along = smoothstep(0.5, 0.26, abs(t));
  float across = smoothstep(max(u_width, 0.02), max(u_width, 0.02) * 0.15, d);
  float a = along * across;

  if (a <= 0.004) discard;
  gl_FragColor = vec4(v_color * a, a);
}
`

/** 全屏三角/四边形通用顶点着色器（后处理用） */
const QUAD_VERT = `
attribute vec2 a_uv;
varying vec2 v_uv;
void main() {
  v_uv = a_uv * 0.5 + 0.5;
  gl_Position = vec4(a_uv, 0.0, 1.0);
}
`

/** 可分离高斯模糊（9 抽头，两次 = 近似参考里的 17 抽头） */
const BLUR_FRAG = `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D u_tex;
uniform vec2 u_dir;      // 一个方向 × 步长（纹理坐标）

void main() {
  vec3 c = texture2D(u_tex, v_uv).rgb * 0.216;
  c += texture2D(u_tex, v_uv + u_dir * 1.0).rgb * 0.176;
  c += texture2D(u_tex, v_uv - u_dir * 1.0).rgb * 0.176;
  c += texture2D(u_tex, v_uv + u_dir * 2.3).rgb * 0.121;
  c += texture2D(u_tex, v_uv - u_dir * 2.3).rgb * 0.121;
  c += texture2D(u_tex, v_uv + u_dir * 4.0).rgb * 0.060;
  c += texture2D(u_tex, v_uv - u_dir * 4.0).rgb * 0.060;
  c += texture2D(u_tex, v_uv + u_dir * 6.0).rgb * 0.033;
  c += texture2D(u_tex, v_uv - u_dir * 6.0).rgb * 0.033;
  c += texture2D(u_tex, v_uv + u_dir * 8.0).rgb * 0.002;
  c += texture2D(u_tex, v_uv - u_dir * 8.0).rgb * 0.002;
  gl_FragColor = vec4(c, 1.0);
}
`

/** 合成：paint + 1.5×blur，再 smoothstep 压肩膀（参考链条的最后两步） */
const COMPOSITE_FRAG = `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D u_paint;
uniform sampler2D u_blur;
uniform float u_glow;

void main() {
  vec3 base = texture2D(u_paint, v_uv).rgb;
  vec3 glow = texture2D(u_blur, v_uv).rgb;
  // ① 先压肩膀：让堆积处干净地并到白、边缘柔和过渡
  vec3 c = smoothstep(0.0, 1.0, min(base, vec3(1.0)));
  // ② 再叠辉光（这样模糊出来的暗尾巴还留着，才看得到"透出来的光"）
  c += glow * u_glow;
  // ③ 一点点提亮，避免整体发闷
  c = pow(min(c, vec3(1.0)), vec3(0.92));
  gl_FragColor = vec4(c, 1.0);
}
`

/** 每颗粒子占的 float 数：x, y, vx, vy, r, g, b, size */
const STRIDE = 8

function hsl2rgb(h, s, l, out) {
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

/**
 * 配色预设。
 *
 * `steps` = 色相取几个固定档位：夜星最早那三张参考图是「纯红 / 纯黄 / 纯绿」
 * 三个色块，均匀随机取色相会糊成一片黄绿，三种颜色分不出来。
 * 但「魔幻粒子3D」里是七彩连续流动（七彩流动那一档），所以另给了一个 rainbow。
 */
export const PALETTES = {
  // 参考 App 的主色：高饱和、亮度中等，靠加法混合自己叠亮
  magic: { name: '幻彩', hues: [0, 360], sat: [100, 100], light: [50, 52], steps: 0, flow: 1 },
  neon: { name: '霓虹', hues: [176, 300], sat: [100, 100], light: [50, 54], steps: 3 },
  crystal: { name: '水晶', hues: [190, 262], sat: [45, 70], light: [72, 88], steps: 2 },
  nature: { name: '自然', hues: [0, 120], sat: [100, 100], light: [50, 54], steps: 3 },
  fire: { name: '焰', hues: [4, 46], sat: [100, 100], light: [50, 54], steps: 0, flow: 1 },
  ice: { name: '霜', hues: [180, 240], sat: [72, 100], light: [52, 60], steps: 0, flow: 1 },
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
    // 探针会误判成"没画出来"。注意开了后处理之后画面来自合成 pass，这条仍然成立。
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

  function makeProgram(vsSrc, fsSrc) {
    const p = gl.createProgram()
    gl.attachShader(p, compile(gl.VERTEX_SHADER, vsSrc))
    gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fsSrc))
    gl.linkProgram(p)
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      throw new Error('link: ' + gl.getProgramInfoLog(p))
    }
    return p
  }

  const cfg = {
    count: 3200,
    size: 26,           // 光斑直径（CSS px）
    trail: 0.92,        // 拖尾系数：越大越黏，粒子赖在屏幕上叠成团
    width: 0.055,       // 仅光轨风格用
    style: 'glow',      // glow | streak
    palette: 'magic',
    invert: false,
    bloom: 0.85,        // 0 = 关掉后处理（低端机兜底）
    auto: false,
    ...options,
  }

  let prog, loc
  let quadProg = null        // 后处理程序是否已建好（当作布尔用）
  let blurProg = null, blurLoc = null
  let compProg = null, compLoc = null

  try {
    prog = makeProgram(VERT, cfg.style === 'streak' ? FRAG_STREAK : FRAG_GLOW)
  } catch (e) {
    return { ok: false, reason: String(e.message || e) }
  }
  loc = {
    pos: gl.getAttribLocation(prog, 'a_pos'),
    vel: gl.getAttribLocation(prog, 'a_vel'),
    color: gl.getAttribLocation(prog, 'a_color'),
    size: gl.getAttribLocation(prog, 'a_size'),
    res: gl.getUniformLocation(prog, 'u_res'),
    scale: gl.getUniformLocation(prog, 'u_scale'),
    width: gl.getUniformLocation(prog, 'u_width'),
  }

  function buildPost() {
    if (quadProg) return true
    try {
      // 只需要两个后处理程序：模糊 + 合成。别在这里再建一个占位程序 ——
      // 第一版就这么干，那个占位 shader 引用了没声明的 u_tex，编译失败后
      // 整个 try 被吞掉，bloom 永远开着 fbo=null（表现为纯黑屏）。
      quadProg = true
      blurProg = makeProgram(QUAD_VERT, BLUR_FRAG)
      blurLoc = {
        tex: gl.getUniformLocation(blurProg, 'u_tex'),
        dir: gl.getUniformLocation(blurProg, 'u_dir'),
        uv: gl.getAttribLocation(blurProg, 'a_uv'),
      }
      compProg = makeProgram(QUAD_VERT, COMPOSITE_FRAG)
      compLoc = {
        paint: gl.getUniformLocation(compProg, 'u_paint'),
        blur: gl.getUniformLocation(compProg, 'u_blur'),
        glow: gl.getUniformLocation(compProg, 'u_glow'),
        uv: gl.getAttribLocation(compProg, 'a_uv'),
      }
      return true
    } catch (e) {
      quadProg = null
      return false
    }
  }

  // 全屏四边形（两个三角形）的 uv
  const quadBuf = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
    -1, -1, 1, -1, -1, 1,
    -1, 1, 1, -1, 1, 1,
  ]), gl.STATIC_DRAW)

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

  // 加法混合：叠出白热。
  // 🔴 blendFunc 只是"设参数"，真正生效要 enable(BLEND)。v2.46.347 只写了
  // blendFunc 没 enable，于是从来没有混合过：后画的粒子把前面的直接盖掉，
  // 暗边啃掉邻居的光（屏幕上那种月牙缺口），密集处也堆不出白。
  gl.enable(gl.BLEND)
  gl.blendFunc(gl.ONE, gl.ONE)
  gl.disable(gl.DEPTH_TEST)
  gl.clearColor(0, 0, 0, 1)

  // 部分设备的点大小上限很小（有的只到 64），超了会被裁剪、粒子看起来"长不大"
  const sizeRange = gl.getParameter(gl.ALIASED_POINT_SIZE_RANGE) || [1, 64]
  const MAX_POINT = Math.min(sizeRange[1] || 64, 512)

  // ---------- 后处理缓冲（半分辨率）----------
  let fbo = null          // { paint, tmp, blur, fb[], w, h, ok }
  let bloomOn = cfg.bloom > 0

  function makeTex(w, h) {
    const t = gl.createTexture()
    gl.bindTexture(gl.TEXTURE_2D, t)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    return t
  }

  function disposeFbo() {
    if (!fbo) return
    for (const t of fbo.textures) gl.deleteTexture(t)
    for (const f of fbo.fbs) gl.deleteFramebuffer(f)
    fbo = null
  }

  function ensureFbo(w, h) {
    // 模糊层不需要跟屏幕同分辨率：1200 宽的屏上 600 宽足够，再大纯烧填充率
    const bw = Math.max(64, Math.round(w * 0.5))
    const bh = Math.max(64, Math.round(h * 0.5))
    if (fbo && fbo.w === bw && fbo.h === bh) return true
    disposeFbo()
    if (!buildPost()) { bloomOn = false; return false }
    const names = ['paint', 'tmp', 'blur']
    const textures = names.map(() => makeTex(bw, bh))
    const fbs = textures.map((t) => {
      const f = gl.createFramebuffer()
      gl.bindFramebuffer(gl.FRAMEBUFFER, f)
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0)
      if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) {
        gl.bindFramebuffer(gl.FRAMEBUFFER, null)
        return null
      }
      return f
    })
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    if (fbs.some((f) => !f)) { bloomOn = false; return false }
    fbo = { w: bw, h: bh, textures, fbs, paint: textures[0], paintFb: fbs[0] }
    return true
  }

  // ---------- 粒子池 ----------
  let cap = 0
  let data = null      // [x, y, vx, vy, r, g, b, size] * cap
  let life = null      // 剩余寿命（秒）
  let maxLife = null
  // 原始尺寸单独放：每帧的 size 是「原始尺寸 × 速度放大 × 将死缩小」算出来的，
  // 如果直接往 data 里乘，下一帧就会在上一次的结果上再乘，尺寸会雪球式失真。
  let baseSize = null
  let alive = 0
  let cw = 1
  let ch = 1
  let dpr = 1
  let tsec = 0        // 累计时长（flow 配色按时间流动）

  function ensureCap(n) {
    if (n === cap) return
    const old = data, oldLife = life, oldMax = maxLife, oldBase = baseSize
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

  /**
   * 按配色取一个颜色。
   *
   * 🔴 别退回「每颗随机取色相」：第一版就是这样，满屏彩色纸屑，一颗一个颜色，
   * 相邻的也不相干，完全没有参考 App 那种「一整片光在流动」的感觉。
   * flow 类配色按**位置 + 时间**取色相 —— 同一次喷发、挨着的粒子颜色接近，
   * 才会连成彩带（参考里的「七彩流动」就是这么来的）。
   */
  function pickColor(out, x = 0, y = 0) {
    const p = PALETTES[cfg.palette] || PALETTES.magic
    let h
    if (p.flow) {
      // 空间上分成几条彩带（一屏能看到 2~3 个色段），时间上缓慢漂移；
      // 再加 ±20° 的抖动 —— 完全一致的话像塑料片，抖一点才有颗粒感
      const wave = Math.sin(x * 0.0075 + y * 0.0055 + tsec * 2.6)
      h = p.hues[0] + (p.hues[1] - p.hues[0]) * (0.5 + 0.5 * wave)
      h += rand(-20, 20)
    } else if (p.steps && p.steps > 1) {
      const k = Math.floor(Math.random() * p.steps)
      h = p.hues[0] + (k * (p.hues[1] - p.hues[0])) / (p.steps - 1)
      h += rand(-4, 4)      // 一点抖动，免得几色太生硬
    } else {
      h = rand(p.hues[0], p.hues[1])
    }
    if (cfg.invert) h = (h + 180) % 360
    hsl2rgb(h, rand(p.sat[0], p.sat[1]), rand(p.light[0], p.light[1]), out)
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
      let sp = speed * (0.28 + Math.random() * Math.random() * 1.6)
      let lf = l0 + Math.random() * (l1 - l0)
      let szMul = 1
      let isCore = false
      /* 约 15% 是「芯」：几乎不动、更大、短命。
         参考 App 里那团白热就是这种粒子在一处叠出来的 —— 只靠飞出去的，
         中心永远是空的（粒子一发射就离开了）。
         加法混合下几十颗叠在一起就过曝成白。 */
      if (Math.random() < 0.15) {
        sp = rand(2, 26)
        lf = rand(0.18, 0.42)
        szMul = 1.8
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
        pickColor(_col, x, y)
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
    if (cfg.style === 'streak') gl.uniform1f(loc.scale, dpr)
    if (bloomOn) ensureFbo(canvas.width, canvas.height)
  }

  /** 把已经在飞的粒子按当前配色重算颜色 —— 否则改配色后要等旧的死光才看见效果 */
  function recolor() {
    for (let i = 0; i < alive; i++) {
      const off = i * STRIDE
      pickColor(_col, data[off], data[off + 1])
      data[off + 4] = _col[0]
      data[off + 5] = _col[1]
      data[off + 6] = _col[2]
    }
  }

  function rebuildPointProgram() {
    try {
      const p = makeProgram(VERT, cfg.style === 'streak' ? FRAG_STREAK : FRAG_GLOW)
      gl.deleteProgram(prog)
      prog = p
      loc = {
        pos: gl.getAttribLocation(prog, 'a_pos'),
        vel: gl.getAttribLocation(prog, 'a_vel'),
        color: gl.getAttribLocation(prog, 'a_color'),
        size: gl.getAttribLocation(prog, 'a_size'),
        res: gl.getUniformLocation(prog, 'u_res'),
        scale: gl.getUniformLocation(prog, 'u_scale'),
        width: gl.getUniformLocation(prog, 'u_width'),
      }
      gl.useProgram(prog)
      gl.bindBuffer(gl.ARRAY_BUFFER, buf)
      gl.enableVertexAttribArray(loc.pos)
      gl.enableVertexAttribArray(loc.vel)
      gl.enableVertexAttribArray(loc.color)
      gl.enableVertexAttribArray(loc.size)
      gl.vertexAttribPointer(loc.pos, 2, gl.FLOAT, false, B, 0)
      gl.vertexAttribPointer(loc.vel, 2, gl.FLOAT, false, B, 8)
      gl.vertexAttribPointer(loc.color, 3, gl.FLOAT, false, B, 16)
      gl.vertexAttribPointer(loc.size, 1, gl.FLOAT, false, B, 28)
      gl.uniform2f(loc.res, cw, ch)
      gl.uniform1f(loc.width, Math.max(0.02, Math.min(0.5, cfg.width)))
    } catch { /* 保留旧程序 */ }
  }

  function applyOptions(patch) {
    if (!patch) return
    const styleChanged = patch.style != null && patch.style !== cfg.style
    Object.assign(cfg, patch)
    if (patch.width != null) {
      gl.useProgram(prog)
      gl.uniform1f(loc.width, Math.max(0.02, Math.min(0.5, cfg.width)))
    }
    if (patch.count != null) ensureCap(Math.max(64, Math.min(8000, Math.round(cfg.count))))
    if (patch.palette != null || patch.invert != null) recolor()
    if (patch.bloom != null) {
      bloomOn = cfg.bloom > 0 && cfg.style !== 'streak'
      if (bloomOn) ensureFbo(canvas.width, canvas.height)
    }
    if (styleChanged) {
      bloomOn = cfg.bloom > 0 && cfg.style !== 'streak'
      if (bloomOn) ensureFbo(canvas.width, canvas.height)
      rebuildPointProgram()
    }
  }

  /** 物理步进。dt 秒。 */
  function step(dt) {
    // 光晕风格要"黏"：粒子赖在屏幕上叠成团，画面才有体积感；
    // 光轨风格要"射出去"：衰减快，才能拉出长线。
    const drag = cfg.style === 'streak'
      ? Math.pow(0.925, dt * 60)
      : Math.pow(0.90 + 0.075 * cfg.trail, dt * 60)
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
      data[off + 3] += (cfg.style === 'streak' ? 26 : 12) * dt   // 一点重力

      const sp = Math.hypot(data[off + 2], data[off + 3])
      const t = life[i] / maxLife[i]
      const fade = t < 0.28 ? 0.35 + (t / 0.28) * 0.65 : 1
      // 光晕风格：速度只轻微放大尺寸（光斑不该因为跑得快就变长）
      const grow = cfg.style === 'streak'
        ? 1 + Math.min(2.4, (sp / 420) * growK)
        : 1 + Math.min(0.5, sp / 1400)
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

  function uploadPoints() {
    gl.bufferData(gl.ARRAY_BUFFER, data.subarray(0, alive * STRIDE), gl.DYNAMIC_DRAW)
  }

  /** 画一遍全屏四边形 */
  function drawQuad(attribLoc) {
    gl.bindBuffer(gl.ARRAY_BUFFER, quadBuf)
    gl.enableVertexAttribArray(attribLoc)
    gl.vertexAttribPointer(attribLoc, 2, gl.FLOAT, false, 0, 0)
    gl.drawArrays(gl.TRIANGLES, 0, 6)
  }

  function draw() {
    gl.clear(gl.COLOR_BUFFER_BIT)
    const useBloom = bloomOn && cfg.style !== 'streak' && fbo

    if (!useBloom) {
      if (!alive) { gl.drawArrays(gl.POINTS, 0, 0); return }
      gl.enable(gl.BLEND)
      gl.useProgram(prog)
      gl.uniform1f(loc.scale, dpr)
      gl.bindBuffer(gl.ARRAY_BUFFER, buf)
      gl.enableVertexAttribArray(loc.pos)
      gl.enableVertexAttribArray(loc.vel)
      gl.enableVertexAttribArray(loc.color)
      gl.enableVertexAttribArray(loc.size)
      gl.vertexAttribPointer(loc.pos, 2, gl.FLOAT, false, B, 0)
      gl.vertexAttribPointer(loc.vel, 2, gl.FLOAT, false, B, 8)
      gl.vertexAttribPointer(loc.color, 3, gl.FLOAT, false, B, 16)
      gl.vertexAttribPointer(loc.size, 1, gl.FLOAT, false, B, 28)
      uploadPoints()
      gl.drawArrays(gl.POINTS, 0, alive)
      return
    }

    // ---- 1. 粒子 → paint（半分辨率）----
    gl.enable(gl.BLEND)
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo.paintFb)
    gl.viewport(0, 0, fbo.w, fbo.h)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.useProgram(prog)
    gl.uniform1f(loc.scale, dpr * 0.5)      // 缓冲只有一半宽，点尺寸要跟着缩
    gl.bindBuffer(gl.ARRAY_BUFFER, buf)
    gl.enableVertexAttribArray(loc.pos)
    gl.enableVertexAttribArray(loc.vel)
    gl.enableVertexAttribArray(loc.color)
    gl.enableVertexAttribArray(loc.size)
    gl.vertexAttribPointer(loc.pos, 2, gl.FLOAT, false, B, 0)
    gl.vertexAttribPointer(loc.vel, 2, gl.FLOAT, false, B, 8)
    gl.vertexAttribPointer(loc.color, 3, gl.FLOAT, false, B, 16)
    gl.vertexAttribPointer(loc.size, 1, gl.FLOAT, false, B, 28)
    if (alive) {
      uploadPoints()
      gl.drawArrays(gl.POINTS, 0, alive)
    }

    // 画粒子时顶点属性就开在 buf 上，后面画四边形要改用 quadBuf，
    // 两个程序的 attribLocation 不同，所以每次 bind 之后都要重设指针。
    gl.disableVertexAttribArray(loc.pos)
    gl.disableVertexAttribArray(loc.vel)
    gl.disableVertexAttribArray(loc.color)
    gl.disableVertexAttribArray(loc.size)

    // 后面的模糊/合成都是"整张覆盖写"，必须关混合
    // （tmp/blur 两张图不清屏，开着混合会把上一帧的内容叠进来，画面越跑越亮）
    gl.disable(gl.BLEND)

    // ---- 2. 横向模糊 paint → tmp ----
    gl.useProgram(blurProg)
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo.fbs[1])
    gl.viewport(0, 0, fbo.w, fbo.h)
    gl.activeTexture(gl.TEXTURE0)
    gl.bindTexture(gl.TEXTURE_2D, fbo.paint)
    gl.uniform1i(blurLoc.tex, 0)
    gl.uniform2f(blurLoc.dir, 3.0 / fbo.w, 0)
    drawQuad(blurLoc.uv)

    // ---- 3. 纵向模糊 tmp → blur ----
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo.fbs[2])
    gl.bindTexture(gl.TEXTURE_2D, fbo.textures[1])
    gl.uniform2f(blurLoc.dir, 0, 3.0 / fbo.h)
    drawQuad(blurLoc.uv)

    // ---- 4. 合成到屏幕 ----
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    gl.viewport(0, 0, canvas.width, canvas.height)
    gl.useProgram(compProg)
    gl.activeTexture(gl.TEXTURE0)
    gl.bindTexture(gl.TEXTURE_2D, fbo.paint)
    gl.uniform1i(compLoc.paint, 0)
    gl.activeTexture(gl.TEXTURE1)
    gl.bindTexture(gl.TEXTURE_2D, fbo.textures[2])
    gl.uniform1i(compLoc.blur, 1)
    gl.uniform1f(compLoc.glow, Math.max(0, Math.min(2, cfg.bloom)) * 1.0)
    drawQuad(compLoc.uv)
  }

  // 初始分配 + 默认线宽（applyOptions 只在"改设置"时跑，首帧不能靠它）
  ensureCap(Math.max(64, Math.min(8000, Math.round(cfg.count))))
  gl.useProgram(prog)
  gl.uniform1f(loc.width, Math.max(0.02, Math.min(0.5, cfg.width)))
  bloomOn = cfg.bloom > 0 && cfg.style !== 'streak'

  function dispose() {
    try {
      disposeFbo()
      gl.deleteBuffer(buf)
      gl.deleteBuffer(quadBuf)
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
    get bloom() { return bloomOn },
    clear() { alive = 0 },
  }
}
