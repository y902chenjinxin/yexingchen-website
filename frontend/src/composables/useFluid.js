/**
 * GPU 流体引擎（v2.46.355）—— 按「魔幻粒子3D」APK 逆向出来的真实管线重做
 *
 * ## 为什么推翻粒子系统
 * 夜星：「我现在就要跟逆向的 apk 一模一样的效果」。
 * 那个 App 不是粒子系统，是 **Stable Fluids（半拉格朗日平流）**：
 * assets/AdvectPaint.frag 里一句 `samplePos = varyTexCoord - texture2D(texVel, uv) * uVelScale`
 * 就是铁证 —— 每个像素按速度场往回取上一帧的颜色，所以东西会"流"、会黏、会卷。
 * 粒子再怎么调也出不来这个观感。
 *
 * ## 从 APK 里抄下来的东西（assets/*.frag 全是明文）
 *   · 速度/染料都用**两个字节编码浮点**，因为 8bit 纹理会把浮点插坏
 *     （AdvectPaintLow.frag 里的 EncodeFloatRG / DecodeFloatRG / 手写 sampleTex 双线性）
 *   · 可分离高斯 17 抽头（BlurHor/BlurVert.frag，权重 0.05~0.16）
 *   · 显示：`smoothstep(0,1,color)` **之后**再 `+= 1.5 × 模糊图`（FluidRegularGlow.frag）
 *   · 细节：`color *= (1.9 * detail)`（detail_active）
 *   · RGB→HSV 平移（paint_hsl_active），对应它的「七彩流动」
 *
 * ## 为什么不用浮点纹理
 * APK 明明有 OES_texture_float 也不用，宁可手写双字节编码 + 自己插值 ——
 * 就是为了在低端安卓上也能跑。这里照做：整套只有 RGBA8，一套路径跑遍所有设备。
 *
 * ## 量纲（很容易搞混，写清楚）
 *   · 速度单位是 **uv/秒**（1 = 一屏宽每秒）
 *   · 平流：`coord = uv - v * dt`
 *   · 散度/梯度要除以 texel 才是物理量：`div = 0.5 * ((vR.x - vL.x)/texel.x + …)`
 *     不除的话散度只有 1e-3 量级，8bit 编码直接是噪声
 */

const VERT = `
attribute vec2 a_pos;
varying vec2 v_uv;
void main() {
  v_uv = a_pos * 0.5 + 0.5;
  gl_Position = vec4(a_pos, 0.0, 1.0);
}
`

const COMMON = `
precision highp float;

const float VR = 2048.0;    // 速度量程 ±2048 texel/s（手指最快约 300）
const float PR = 256.0;     // 压力
const float DR = 768.0;     // 散度 / 涡度
const float EPS = 1e-6;

vec2 encRG(float v, float range) {
  float n = clamp(v / (2.0 * range) + 0.5, 0.0, 0.9999);
  vec2 e = vec2(1.0, 255.0) * n;
  e = fract(e);
  e -= e.yy * vec2(1.0 / 255.0, 0.0);
  return e;
}

float decRG(vec2 rg, float range) {
  return (dot(rg, vec2(1.0, 1.0 / 255.0)) - 0.5) * 2.0 * range;
}

vec4 encV(vec2 v) { return vec4(encRG(v.x, VR), encRG(v.y, VR)); }
vec2 decV(vec4 t) { return vec2(decRG(t.rg, VR), decRG(t.ba, VR)); }

// NEAREST 纹理上自己插值 —— 编码值交给硬件 bilerp 会插坏低字节
vec4 texBilerp(sampler2D tex, vec2 uv, vec2 res) {
  vec2 p = uv * res - 0.5;
  vec2 i = floor(p);
  vec2 f = p - i;
  vec4 a = texture2D(tex, (i + vec2(0.5, 0.5)) / res);
  vec4 b = texture2D(tex, (i + vec2(1.5, 0.5)) / res);
  vec4 c = texture2D(tex, (i + vec2(0.5, 1.5)) / res);
  vec4 d = texture2D(tex, (i + vec2(1.5, 1.5)) / res);
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
`

const FILL_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform float uValue;
uniform float uRange;
uniform float uRaw;   // 1 = 直接写 uValue（染料这种非编码纹理）
void main() {
  if (uRaw > 0.5) { gl_FragColor = vec4(uValue, uValue, uValue, 1.0); return; }
  gl_FragColor = vec4(encRG(uValue, uRange), encRG(uValue, uRange));
}
`

const ADVECT_VEL_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uVel;
uniform sampler2D uSrc;
uniform vec2 uRes;
uniform float uDt;
uniform float uDissipation;

void main() {
  vec2 v = decV(texBilerp(uVel, v_uv, uRes));
  vec2 coord = v_uv - v * uDt / uRes;
  vec2 outV = decV(texBilerp(uSrc, coord, uRes));
  outV /= 1.0 + uDissipation * uDt;
  // 8bit 编码在 0 附近有 ±0.012 的死区抖动，太小就归零，否则画面会永远在爬
  if (abs(outV.x) < 0.4 && abs(outV.y) < 0.4) outV = vec2(0.0);
  gl_FragColor = encV(clamp(outV, vec2(-VR), vec2(VR)));
}
`

const ADVECT_DYE_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uVel;
uniform sampler2D uSrc;
uniform vec2 uRes;
uniform float uDt;
uniform float uDissipation;

void main() {
  vec2 v = decV(texBilerp(uVel, v_uv, uRes));
  vec2 coord = v_uv - v * uDt / uRes;
  vec4 c = texture2D(uSrc, coord);
  c.rgb /= 1.0 + uDissipation * uDt;
  gl_FragColor = vec4(c.rgb, 1.0);
}
`

const SPLAT_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uTarget;
uniform vec2 uRes;
uniform float uAspect;
uniform vec2 uPoint;
uniform vec3 uColor;
uniform float uRadius;
uniform float uIsVel;

void main() {
  vec2 p = v_uv - uPoint;
  p.x *= uAspect;
  float f = exp(-dot(p, p) / uRadius);
  if (uIsVel > 0.5) {
    vec2 base = decV(texBilerp(uTarget, v_uv, uRes));
    gl_FragColor = encV(clamp(base + uColor.xy * f, vec2(-VR), vec2(VR)));
  } else {
    // 20.0 对上 APK 的 texInput * 20.0：一次按压就直接把染料顶到饱和，
    // 所以手指划过的轨迹是实心的、边缘才散开
    vec3 base = texture2D(uTarget, v_uv).rgb;
    gl_FragColor = vec4(min(base + uColor * f * 3.0, vec3(1.0)), 1.0);
  }
}
`

const CURL_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uVel;
uniform vec2 uTexel;

void main() {
  vec2 res = 1.0 / uTexel;
  float L = decV(texBilerp(uVel, v_uv - vec2(uTexel.x, 0.0), res)).y;
  float R = decV(texBilerp(uVel, v_uv + vec2(uTexel.x, 0.0), res)).y;
  float B = decV(texBilerp(uVel, v_uv - vec2(0.0, uTexel.y), res)).x;
  float T = decV(texBilerp(uVel, v_uv + vec2(0.0, uTexel.y), res)).x;
  float c = (R - L) - (T - B);
  c = clamp(c, -DR, DR);
  gl_FragColor = vec4(encRG(c, DR), encRG(c, DR));
}
`

const VORTICITY_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uVel;
uniform sampler2D uCurl;
uniform vec2 uTexel;
uniform float uCurlStrength;
uniform float uDt;

void main() {
  vec2 res = 1.0 / uTexel;
  float L = decRG(texBilerp(uCurl, v_uv - vec2(uTexel.x, 0.0), res).rg, DR);
  float R = decRG(texBilerp(uCurl, v_uv + vec2(uTexel.x, 0.0), res).rg, DR);
  float B = decRG(texBilerp(uCurl, v_uv - vec2(0.0, uTexel.y), res).rg, DR);
  float T = decRG(texBilerp(uCurl, v_uv + vec2(0.0, uTexel.y), res).rg, DR);
  float C = decRG(texBilerp(uCurl, v_uv, res).rg, DR);

  vec2 force = vec2(abs(T) - abs(B), abs(R) - abs(L));
  force /= length(force) + EPS;
  force *= uCurlStrength * C;
  force.y *= -1.0;

  vec2 v = decV(texBilerp(uVel, v_uv, res));
  v += force * uDt;
  gl_FragColor = encV(clamp(v, vec2(-VR), vec2(VR)));
}
`

const DIVERGENCE_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uVel;
uniform vec2 uTexel;

void main() {
  vec2 res = 1.0 / uTexel;
  vec2 L = decV(texBilerp(uVel, v_uv - vec2(uTexel.x, 0.0), res));
  vec2 R = decV(texBilerp(uVel, v_uv + vec2(uTexel.x, 0.0), res));
  vec2 B = decV(texBilerp(uVel, v_uv - vec2(0.0, uTexel.y), res));
  vec2 T = decV(texBilerp(uVel, v_uv + vec2(0.0, uTexel.y), res));
  float div = 0.5 * ((R.x - L.x) + (T.y - B.y));
  div = clamp(div, -DR, DR);
  gl_FragColor = vec4(encRG(div, DR), encRG(div, DR));
}
`

const PRESSURE_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uPressure;
uniform sampler2D uDivergence;
uniform vec2 uTexel;

void main() {
  float L = decRG(texture2D(uPressure, v_uv - vec2(uTexel.x, 0.0)).rg, PR);
  float R = decRG(texture2D(uPressure, v_uv + vec2(uTexel.x, 0.0)).rg, PR);
  float B = decRG(texture2D(uPressure, v_uv - vec2(0.0, uTexel.y)).rg, PR);
  float T = decRG(texture2D(uPressure, v_uv + vec2(0.0, uTexel.y)).rg, PR);
  float div = decRG(texture2D(uDivergence, v_uv).rg, DR);
  float p = (L + R + B + T - div) * 0.25;
  gl_FragColor = vec4(encRG(clamp(p, -PR, PR), PR), encRG(clamp(p, -PR, PR), PR));
}
`

const GRADIENT_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uPressure;
uniform sampler2D uVel;
uniform vec2 uTexel;

void main() {
  vec2 res = 1.0 / uTexel;
  float L = decRG(texture2D(uPressure, v_uv - vec2(uTexel.x, 0.0)).rg, PR);
  float R = decRG(texture2D(uPressure, v_uv + vec2(uTexel.x, 0.0)).rg, PR);
  float B = decRG(texture2D(uPressure, v_uv - vec2(0.0, uTexel.y)).rg, PR);
  float T = decRG(texture2D(uPressure, v_uv + vec2(0.0, uTexel.y)).rg, PR);
  vec2 v = decV(texBilerp(uVel, v_uv, res));
  v -= vec2(R - L, T - B) * 0.5;
  gl_FragColor = encV(clamp(v, vec2(-VR), vec2(VR)));
}
`

/** 17 抽头，权重照 BlurHor.frag（0.05/0.09/0.12/0.15/0.16） */
const BLUR_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uTex;
uniform vec2 uDir;

void main() {
  vec3 c = texture2D(uTex, v_uv).rgb * 0.16;
  c += texture2D(uTex, v_uv + uDir * 1.0).rgb * 0.15;
  c += texture2D(uTex, v_uv - uDir * 1.0).rgb * 0.15;
  c += texture2D(uTex, v_uv + uDir * 2.0).rgb * 0.15;
  c += texture2D(uTex, v_uv - uDir * 2.0).rgb * 0.15;
  c += texture2D(uTex, v_uv + uDir * 3.0).rgb * 0.12;
  c += texture2D(uTex, v_uv - uDir * 3.0).rgb * 0.12;
  c += texture2D(uTex, v_uv + uDir * 4.0).rgb * 0.12;
  c += texture2D(uTex, v_uv - uDir * 4.0).rgb * 0.12;
  c += texture2D(uTex, v_uv + uDir * 5.0).rgb * 0.09;
  c += texture2D(uTex, v_uv - uDir * 5.0).rgb * 0.09;
  c += texture2D(uTex, v_uv + uDir * 6.0).rgb * 0.09;
  c += texture2D(uTex, v_uv - uDir * 6.0).rgb * 0.09;
  c += texture2D(uTex, v_uv + uDir * 7.0).rgb * 0.05;
  c += texture2D(uTex, v_uv - uDir * 7.0).rgb * 0.05;
  c += texture2D(uTex, v_uv + uDir * 8.0).rgb * 0.05;
  c += texture2D(uTex, v_uv - uDir * 8.0).rgb * 0.05;
  gl_FragColor = vec4(c * 0.5, 1.0);
}
`

/** 显示：FluidRegularGlow / FluidTrippyGlow / detail_active / paint_hsl 的组合 */
const DISPLAY_FRAG = COMMON + `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D uDye;
uniform sampler2D uGlow;
uniform sampler2D uDetail;
uniform vec2 uDetailScale;
uniform vec2 uDetailShift;
uniform float uGlowAmt;
uniform float uDetailAmt;
uniform float uMode;
uniform float uHue;
uniform float uSat;
uniform float uInvert;
uniform vec2 uDyeTexel;
uniform float uRim;

vec3 rgb2hsv(vec3 c) {
  vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
  vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
  vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10;
  return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
  vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
  vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
  vec3 color = texture2D(uDye, v_uv).rgb;

  // 边缘高光：拿染料亮度的梯度当"表面曲率"，越靠边越亮。
  // WebGL1 没有 dFdx（要扩展），直接三采样差分，代价可控。
  float lum0 = dot(color, vec3(0.299, 0.587, 0.114));
  vec2 off = uDyeTexel * 2.5;
  float lumX = dot(texture2D(uDye, v_uv + vec2(off.x, 0.0)).rgb, vec3(0.299, 0.587, 0.114));
  float lumY = dot(texture2D(uDye, v_uv + vec2(0.0, off.y)).rgb, vec3(0.299, 0.587, 0.114));
  float rim = clamp(length(vec2(lum0 - lumX, lum0 - lumY)) * uRim, 0.0, 1.5);

  if (uDetailAmt > 0.001) {
    // 镜像平铺（abs(fract(x)*2-1)）：fbm 是非周期噪声，直接 REPEAT 在接缝处是硬边，
    // 之前画面上那个"田"字就是它。镜像之后接缝处值连续。
    vec2 duv = v_uv * uDetailScale + uDetailShift;
    duv = abs(fract(duv) * 2.0 - 1.0);
    float det = texture2D(uDetail, duv).a;
    color *= mix(1.0, 1.9 * det, uDetailAmt);
  }

  color = smoothstep(0.0, 1.0, min(color, vec3(1.0)));

  if (uMode > 0.5) {
    vec3 edge = vec3(0.5);
    vec3 c1 = mix(2.0 * edge, vec3(0.0), (edge - color) / edge);
    vec3 c2 = mix(2.0 * edge, vec3(0.0), (color - edge) / (vec3(1.0) - edge));
    color.r = color.r < edge.r ? c1.r : c2.r;
    color.g = color.g < edge.g ? c1.g : c2.g;
    color.b = color.b < edge.b ? c1.b : c2.b;
  }

  color += rim * 0.42;
  color += uGlowAmt * texture2D(uGlow, v_uv).rgb;

  if (uInvert > 0.5) color = vec3(1.0) - clamp(color, 0.0, 1.0);

  if (abs(uHue) > 0.0001 || abs(uSat) > 0.0001) {
    vec3 hsv = rgb2hsv(clamp(color, 0.0, 1.0));
    hsv.x = fract(hsv.x + uHue);
    hsv.y = clamp(hsv.y + uSat, 0.0, 1.0);
    color = hsv2rgb(hsv);
  }

  // 抖动：8bit 染料配 smoothstep 会出一层层的色带，加半个 LSB 噪声打散
  float dither = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
  color += (dither - 0.5) * 0.012;

  gl_FragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
`

/**
 * 8 个档位 —— 照 APK 的 8 个效果名（resources.arsc 里的 string）。
 * APK 每个档位是一套独立的 native 引擎 + display shader；这里用同一套流体
 * 配不同的显示模式/配色/参数来对位，观感上能一一对应。
 */
export const PRESETS = [
  { key: 'liquid', name: '魔幻液体', mode: 0, palette: 'magic', curl: 24, glow: 1.5, detail: 0.55, density: 0.6, hue: 0 },
  { key: 'rainbow', name: '七彩流动', mode: 0, palette: 'rainbow', curl: 20, glow: 1.2, detail: 0.4, density: 0.5, hue: 0.0, hueDrift: 1 },
  { key: 'fire', name: '火魅幻境', mode: 0, palette: 'fire', curl: 34, glow: 2.4, detail: 0.7, density: 0.85, hue: 0 },
  { key: 'trippy', name: '扭曲轨道', mode: 1, palette: 'neon', curl: 44, glow: 1.4, detail: 0.3, density: 0.55, hue: 0 },
  { key: 'beam', name: '奇点与光束', mode: 1, palette: 'ice', curl: 10, glow: 2.6, detail: 0.25, density: 0.9, hue: 0 },
  { key: 'atom', name: '虚幻原子', mode: 0, palette: 'ice', curl: 6, glow: 1.0, detail: 0.3, density: 0.4, hue: 0 },
  { key: 'wave', name: '艺术引力波', mode: 1, palette: 'magic', curl: 52, glow: 1.8, detail: 0.45, density: 0.7, hue: 0 },
  { key: 'pick', name: '推荐', mode: 1, palette: 'fire', curl: 30, glow: 2.0, detail: 0.6, density: 0.75, hue: 0 },
]

function createProgram(gl, vsSrc, fsSrc) {
  const mk = (type, src) => {
    const s = gl.createShader(type)
    gl.shaderSource(s, src)
    gl.compileShader(s)
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(s)
      gl.deleteShader(s)
      throw new Error('shader: ' + log)
    }
    return s
  }
  const program = gl.createProgram()
  gl.attachShader(program, mk(gl.VERTEX_SHADER, vsSrc))
  gl.attachShader(program, mk(gl.FRAGMENT_SHADER, fsSrc))
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    throw new Error('link: ' + gl.getProgramInfoLog(program))
  }
  const loc = {}
  const n = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS)
  for (let i = 0; i < n; i++) {
    const info = gl.getActiveUniform(program, i)
    loc[info.name] = gl.getUniformLocation(program, info.name)
  }
  loc.$attrib = gl.getAttribLocation(program, 'a_pos')
  return { program, loc }
}

export const PALETTES = {
  // hues 是「同色系游走的范围」，不是完整彩虹：一笔划出去整条颜色要一致，
  // 跨越大半屏才有过渡 —— APK 的「选择一个颜色」就是这个意思
  magic: { name: '幻紫', hues: [258, 318], sat: 1 },
  fire: { name: '熔金', hues: [6, 44], sat: 1 },
  ice: { name: '霜蓝', hues: [176, 214], sat: 0.9 },
  neon: { name: '霓虹', hues: [150, 200], sat: 1 },
  rainbow: { name: '七彩', hues: [0, 360], sat: 1 },
}

function hsv2rgb(h, s, v) {
  const c = v * s
  const hp = (h / 60) % 6
  const x = c * (1 - Math.abs((hp % 2) - 1))
  const m = v - c
  let r = 0, g = 0, b = 0
  if (hp < 1) [r, g, b] = [c, x, 0]
  else if (hp < 2) [r, g, b] = [x, c, 0]
  else if (hp < 3) [r, g, b] = [0, c, x]
  else if (hp < 4) [r, g, b] = [0, x, c]
  else if (hp < 5) [r, g, b] = [x, 0, c]
  else [r, g, b] = [c, 0, x]
  return [r + m, g + m, b + m]
}

/**
 * 程序化 detail 纹理（fbm + 脊线）。
 * APK 用的是买来的 marble_stone / veins2 / water 素材，那些不能拷，这里用噪声自己长，
 * 观感上是同一种「石纹 / 水纹」的细碎质感。
 */
function makeDetailTexture(gl, size = 512) {
  const cv = document.createElement('canvas')
  cv.width = cv.height = size
  const ctx = cv.getContext('2d')
  const img = ctx.createImageData(size, size)
  const d = img.data

  // 🔴 别用 sin(n)*43758 那种"伪哈希"：n 一大精度就丢，x 方向会出现规律竖纹
  // （detail 平铺 3 次就变成满屏栅栏）。这里是整数位运算 hash。
  const hash = (x, y) => {
    let h = (x | 0) * 374761393 + (y | 0) * 668265263
    h = (h ^ (h >>> 13)) * 1274126177
    h = h ^ (h >>> 16)
    return (h >>> 0) / 4294967295
  }
  const noise = (x, y) => {
    const xi = Math.floor(x)
    const yi = Math.floor(y)
    const xf = x - xi
    const yf = y - yi
    const u = xf * xf * (3 - 2 * xf)
    const v = yf * yf * (3 - 2 * yf)
    const a = hash(xi, yi)
    const b = hash(xi + 1, yi)
    const c = hash(xi, yi + 1)
    const e = hash(xi + 1, yi + 1)
    return (a + (b - a) * u) * (1 - v) + (c + (e - c) * u) * v
  }

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = (x / size) * 6
      const v = (y / size) * 6
      let f = 0
      let amp = 0.5
      let fr = 1
      for (let o = 0; o < 5; o++) {
        f += noise(u * fr, v * fr) * amp
        amp *= 0.5
        fr *= 2
      }
      // 弱一点的脊线：只留一点"石纹/水纹"的走向，太强会变成明显的重复图案
      const ridge = 1 - Math.abs(f * 2 - 1)
      const val = 0.68 * f + 0.3 * Math.pow(ridge, 2.0)
      const i = (y * size + x) * 4
      d[i] = d[i + 1] = d[i + 2] = 255
      d[i + 3] = Math.max(0, Math.min(255, val * 255))
    }
  }
  ctx.putImageData(img, 0, 0)

  const tex = gl.createTexture()
  gl.bindTexture(gl.TEXTURE_2D, tex)
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cv)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT)
  return tex
}

export function createFluidEngine(canvas, options = {}) {
  const gl = canvas.getContext('webgl', {
    alpha: false,
    depth: false,
    stencil: false,
    antialias: false,
    premultipliedAlpha: false,
    powerPreference: 'high-performance',
    preserveDrawingBuffer: !!options.debug,
  })
  if (!gl) return { ok: false, reason: 'no-webgl' }

  const cfg = {
    simRes: 192,
    dyeRes: 512,
    densityDissipation: 0.6,
    velocityDissipation: 0.9,
    pressureIterations: 20,
    curl: 24,
    splatRadius: 0.0005,
    splatForce: 1.0,   // 1.0 = 手指速度直接当注入速度（内部再乘 sim 宽 ×60）
    glow: 1.5,
    rim: 18,
    detail: 0.55,
    detailScale: 2.2,
    mode: 0,
    palette: 'magic',
    hueShift: 0,
    satShift: 0,
    invert: false,
    ...options,
  }

  const P = {}
  try {
    P.advectVel = createProgram(gl, VERT, ADVECT_VEL_FRAG)
    P.advectDye = createProgram(gl, VERT, ADVECT_DYE_FRAG)
    P.splat = createProgram(gl, VERT, SPLAT_FRAG)
    P.curl = createProgram(gl, VERT, CURL_FRAG)
    P.vort = createProgram(gl, VERT, VORTICITY_FRAG)
    P.div = createProgram(gl, VERT, DIVERGENCE_FRAG)
    P.pressure = createProgram(gl, VERT, PRESSURE_FRAG)
    P.gradient = createProgram(gl, VERT, GRADIENT_FRAG)
    P.blur = createProgram(gl, VERT, BLUR_FRAG)
    P.display = createProgram(gl, VERT, DISPLAY_FRAG)
    P.fill = createProgram(gl, VERT, FILL_FRAG)
  } catch (e) {
    return { ok: false, reason: String(e.message || e).slice(0, 220) }
  }

  const quad = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, quad)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
    -1, -1, 1, -1, -1, 1,
    -1, 1, 1, -1, 1, 1,
  ]), gl.STATIC_DRAW)

  gl.disable(gl.BLEND)
  gl.disable(gl.DEPTH_TEST)
  gl.clearColor(0, 0, 0, 1)

  const detailTex = makeDetailTexture(gl)

  let velocity = null
  let dye = null
  let pressure = null
  let divergence = null
  let curlFbo = null
  let glowA = null
  let glowB = null
  let simW = 1, simH = 1, dyeW = 1, dyeH = 1
  let aspect = 1
  let time = 0
  let texel = [1, 1]

  function createFBO(w, h, filter) {
    const tex = gl.createTexture()
    gl.bindTexture(gl.TEXTURE_2D, tex)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    const fbo = gl.createFramebuffer()
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo)
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0)
    const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    return { tex, fbo, w, h, texel: [1 / w, 1 / h], ok }
  }

  function createDouble(w, h, filter) {
    let a = createFBO(w, h, filter)
    let b = createFBO(w, h, filter)
    return {
      get read() { return a },
      get write() { return b },
      swap() { const t = a; a = b; b = t },
      w, h,
    }
  }

  const VR_CONST = 2048.0
  const PR_CONST = 256.0

  function fillFbo(target, value, range, raw) {
    const loc = use(P.fill)
    gl.uniform1f(loc.uValue, value)
    gl.uniform1f(loc.uRange, range)
    gl.uniform1f(loc.uRaw, raw ? 1 : 0)
    blit(target)
  }

  function blit(target) {
    if (target) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, target.fbo)
      gl.viewport(0, 0, target.w, target.h)
    } else {
      gl.bindFramebuffer(gl.FRAMEBUFFER, null)
      gl.viewport(0, 0, canvas.width, canvas.height)
    }
    gl.drawArrays(gl.TRIANGLES, 0, 6)
  }

  function use(p) {
    gl.useProgram(p.program)
    if (p.loc.$attrib >= 0) {
      gl.bindBuffer(gl.ARRAY_BUFFER, quad)
      gl.enableVertexAttribArray(p.loc.$attrib)
      gl.vertexAttribPointer(p.loc.$attrib, 2, gl.FLOAT, false, 0, 0)
    }
    return p.loc
  }

  function bind(unit, tex, loc, name) {
    gl.activeTexture(gl.TEXTURE0 + unit)
    gl.bindTexture(gl.TEXTURE_2D, tex)
    if (loc[name]) gl.uniform1i(loc[name], unit)
  }

  function calcRes(base) {
    const w = Math.max(1, canvas.width)
    const h = Math.max(1, canvas.height)
    let ar = w / h
    if (ar < 1) ar = 1 / ar
    const lo = Math.round(base)
    const hi = Math.round(base * ar)
    return w > h ? { w: hi, h: lo } : { w: lo, h: hi }
  }

  function initFBOs() {
    const s = calcRes(cfg.simRes)
    simW = s.w
    simH = s.h
    const d = calcRes(cfg.dyeRes)
    dyeW = d.w
    dyeH = d.h
    velocity = createDouble(simW, simH, gl.NEAREST)
    pressure = createDouble(simW, simH, gl.NEAREST)
    divergence = createFBO(simW, simH, gl.NEAREST)
    curlFbo = createFBO(simW, simH, gl.NEAREST)
    dye = createDouble(dyeW, dyeH, gl.LINEAR)
    const gw = Math.max(64, dyeW >> 1)
    const gh = Math.max(64, dyeH >> 1)
    glowA = createFBO(gw, gh, gl.LINEAR)
    glowB = createFBO(gw, gh, gl.LINEAR)
    aspect = canvas.width / canvas.height
    texel = [1 / simW, 1 / simH]
    // 🔴 编码纹理不能 gl.clear(0,0,0,0) —— 解码出来是 -量程（速度初值 -512 → 整锅炸飞）。
    // 必须写"零的编码"：encRG(0) ≈ 0.498/0.5。染料是普通 RGBA，清成 0。
    for (const f of [velocity.read, velocity.write, pressure.read, pressure.write,
      divergence, curlFbo, glowA, glowB]) {
      fillFbo(f, 0, VR_CONST)
    }
    fillFbo(dye.read, 0, 1, true)
    fillFbo(dye.write, 0, 1, true)
  }

  function resize(w, h) {
    const dpr = Math.min(2, window.devicePixelRatio || 1)
    canvas.width = Math.max(2, Math.floor(w * dpr))
    canvas.height = Math.max(2, Math.floor(h * dpr))
    canvas.style.width = Math.floor(w) + 'px'
    canvas.style.height = Math.floor(h) + 'px'
    initFBOs()
  }

  let huePhase = 0

  function pointerColor(x, y) {
    const p = PALETTES[cfg.palette] || PALETTES.magic
    let h
    if (p.hues[1] > p.hues[0]) {
      // 只做「同色系里的缓慢游走」，不铺满 0~360：
      // 一笔划出去时整条颜色是一致的，跨越大半个屏幕才看得出渐变，
      // 这才是「魔幻液体」的观感（APK 是「选择一个颜色」，不是彩虹）。
      const mid = (p.hues[0] + p.hues[1]) / 2
      const span = (p.hues[1] - p.hues[0]) * 0.18
      const wave = Math.sin(x * 0.0024 + y * 0.0019 + huePhase)
      h = (mid + wave * span + 360) % 360
    } else {
      h = p.hues[0]
    }
    return hsv2rgb(h, p.sat, 1)
  }

  function splat(x, y, dx, dy, color) {
    const ux = x / canvas.width
    const uy = 1 - y / canvas.height

    let loc = use(P.splat)
    gl.uniform2f(loc.uRes, simW, simH)
    gl.uniform1f(loc.uAspect, aspect)
    gl.uniform2f(loc.uPoint, ux, uy)
    gl.uniform3f(loc.uColor, (dx / canvas.width) * simW * 60 * cfg.splatForce,
                 -(dy / canvas.height) * simH * 60 * cfg.splatForce, 0)
    gl.uniform1f(loc.uRadius, cfg.splatRadius)
    gl.uniform1f(loc.uIsVel, 1)
    bind(0, velocity.read.tex, loc, 'uTarget')
    blit(velocity.write)
    velocity.swap()

    loc = use(P.splat)
    gl.uniform2f(loc.uRes, simW, simH)
    gl.uniform1f(loc.uAspect, aspect)
    gl.uniform2f(loc.uPoint, ux, uy)
    gl.uniform3f(loc.uColor, color[0], color[1], color[2])
    gl.uniform1f(loc.uRadius, cfg.splatRadius)
    gl.uniform1f(loc.uIsVel, 0)
    bind(0, dye.read.tex, loc, 'uTarget')
    blit(dye.write)
    dye.swap()
  }

  function step(dt) {
    dt = Math.min(dt, 0.032)
    time += dt
    huePhase += dt * 0.9

    let loc = use(P.advectVel)
    bind(0, velocity.read.tex, loc, 'uVel')
    bind(1, velocity.read.tex, loc, 'uSrc')
    gl.uniform2f(loc.uRes, simW, simH)
    gl.uniform1f(loc.uDt, dt)
    gl.uniform1f(loc.uDissipation, cfg.velocityDissipation)
    blit(velocity.write)
    velocity.swap()

    loc = use(P.curl)
    bind(0, velocity.read.tex, loc, 'uVel')
    gl.uniform2f(loc.uTexel, texel[0], texel[1])
    blit(curlFbo)

    loc = use(P.vort)
    bind(0, velocity.read.tex, loc, 'uVel')
    bind(1, curlFbo.tex, loc, 'uCurl')
    gl.uniform2f(loc.uTexel, texel[0], texel[1])
    gl.uniform1f(loc.uCurlStrength, cfg.curl)
    gl.uniform1f(loc.uDt, dt)
    blit(velocity.write)
    velocity.swap()

    loc = use(P.div)
    bind(0, velocity.read.tex, loc, 'uVel')
    gl.uniform2f(loc.uTexel, texel[0], texel[1])
    blit(divergence)

    fillFbo(pressure.read, 0, PR_CONST)

    loc = use(P.pressure)
    gl.uniform2f(loc.uTexel, texel[0], texel[1])
    bind(1, divergence.tex, loc, 'uDivergence')
    for (let i = 0; i < cfg.pressureIterations; i++) {
      bind(0, pressure.read.tex, loc, 'uPressure')
      blit(pressure.write)
      pressure.swap()
    }

    loc = use(P.gradient)
    bind(0, pressure.read.tex, loc, 'uPressure')
    bind(1, velocity.read.tex, loc, 'uVel')
    gl.uniform2f(loc.uTexel, texel[0], texel[1])
    blit(velocity.write)
    velocity.swap()

    loc = use(P.advectDye)
    bind(0, velocity.read.tex, loc, 'uVel')
    bind(1, dye.read.tex, loc, 'uSrc')
    gl.uniform2f(loc.uRes, simW, simH)
    gl.uniform1f(loc.uDt, dt)
    gl.uniform1f(loc.uDissipation, cfg.densityDissipation)
    blit(dye.write)
    dye.swap()
  }

  function draw() {
    let loc = use(P.blur)
    bind(0, dye.read.tex, loc, 'uTex')
    gl.uniform2f(loc.uDir, glowA.texel[0] * 1.5, 0)
    blit(glowA)

    loc = use(P.blur)
    bind(0, glowA.tex, loc, 'uTex')
    gl.uniform2f(loc.uDir, 0, glowB.texel[1] * 1.5)
    blit(glowB)

    loc = use(P.display)
    bind(0, dye.read.tex, loc, 'uDye')
    bind(1, glowB.tex, loc, 'uGlow')
    bind(2, detailTex, loc, 'uDetail')
    gl.uniform2f(loc.uDetailScale, cfg.detailScale, cfg.detailScale)
    gl.uniform2f(loc.uDetailShift, time * 0.01, time * 0.007)
    gl.uniform2f(loc.uDyeTexel, 1 / dyeW, 1 / dyeH)
    gl.uniform1f(loc.uRim, cfg.rim)
    gl.uniform1f(loc.uGlowAmt, cfg.glow)
    gl.uniform1f(loc.uDetailAmt, cfg.detail)
    gl.uniform1f(loc.uMode, cfg.mode)
    gl.uniform1f(loc.uHue, cfg.hueShift)
    gl.uniform1f(loc.uSat, cfg.satShift)
    gl.uniform1f(loc.uInvert, cfg.invert ? 1 : 0)
    blit(null)
  }

  function applyOptions(patch) {
    if (!patch) return
    const needResize = (patch.simRes != null && patch.simRes !== cfg.simRes)
      || (patch.dyeRes != null && patch.dyeRes !== cfg.dyeRes)
    Object.assign(cfg, patch)
    if (needResize) initFBOs()
  }

  function clear() {
    for (const f of [velocity.read, velocity.write, pressure.read, pressure.write,
      divergence, curlFbo]) {
      fillFbo(f, 0, VR_CONST)
    }
    fillFbo(dye.read, 0, 1, true)
    fillFbo(dye.write, 0, 1, true)
  }

  function dispose() {
    try {
      gl.deleteBuffer(quad)
      gl.deleteTexture(detailTex)
      gl.getExtension('WEBGL_lose_context')?.loseContext()
    } catch { /* ignore */ }
  }

  return {
    ok: true,
    cfg,
    resize,
    splat,
    pointerColor,
    step,
    draw,
    applyOptions,
    dispose,
    clear,
    get info() { return { simW, simH, dyeW, dyeH, aspect } },
  }
}
